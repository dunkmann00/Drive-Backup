from delocate.fuse import fuse_wheels
from delocate.wheeltools import InWheelCtx, rewrite_record
from delocate.pkginfo import read_pkg_info, write_pkg_info
from pathlib import Path
import subprocess, platform
import packaging.tags
from packaging.utils import parse_wheel_filename
from contextlib import contextmanager
from platformdirs import user_cache_path

from cleo.events.console_events import TERMINATE
from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.event_dispatcher import EventDispatcher
from poetry.core.utils.helpers import temporary_directory
from poetry.console.application import Application
from poetry.console.commands.install import InstallCommand
from poetry.plugins.application_plugin import ApplicationPlugin

NAME = "poetry-plugin-universal2-wheel"

class Universal2WheelPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        if platform.system() != "Darwin":
            application._io.write_error_line(
                f"<warning>Warning: '{NAME}' is only meant to be used on "
                "macOS. It will not have any effect on this machine.</>"
            )
            return

        # Only run if the plugin is listed in the pyproject.toml
        if application.poetry.pyproject.data.get("tool", {}).get(NAME) is not None:
            application.event_dispatcher.add_listener(
                TERMINATE, self.post_install
            )

    def post_install(
        self,
        event: ConsoleCommandEvent,
        event_name: str,
        dispatcher: EventDispatcher
    ) -> None:
        command = event.command
        if not isinstance(command, InstallCommand):
            return

        io = event.io
        env = command.env

        lock_data = command.poetry.locker.lock_data

        cache_pip_wheels = self.should_cache_wheels(command.poetry.pyproject)

        stdout = None if io.is_verbose() else subprocess.DEVNULL

        for package_info in lock_data["package"]:
            if self.needs_universal2(package_info):
                io.write_line(
                    f"<info>Reinstalling {package_info['name']} with universal2 wheel.</>"
                )
                package_specifier = f"{package_info['name']}=={self.get_version(package_info)}"
                platform = self.get_universal2_platform(package_info)
                with self.pip_download_dir(cache_pip_wheels) as download_dir:
                    if platform is None: # We need to try to fuse thin wheels
                        if io.is_verbose():
                            io.write_line(
                                f"<debug>'{package_info['name']}' universal2 wheel not available on pypi, "
                                "attempting to download and fuse thin wheels...'</>"
                            )
                        arm64_platform, x86_64_platform = self.get_specific_platforms(package_info)
                        thin_download_dir = Path(download_dir) / "thin"
                        env.run_pip("download", "--only-binary=:all:", "--no-deps", "--platform", arm64_platform, "--no-cache-dir", "-d", str(thin_download_dir), package_specifier, call=True, stdout=stdout)
                        env.run_pip("download", "--only-binary=:all:", "--no-deps", "--platform", x86_64_platform, "--no-cache-dir", "-d", str(thin_download_dir), package_specifier, call=True, stdout=stdout)
                        arm64_whl = next(thin_download_dir.glob("*arm64.whl"))
                        x86_64_whl = next(thin_download_dir.glob("*x86_64.whl"))
                        universal2_whl = Path(download_dir) / (x86_64_whl.name.removesuffix("x86_64.whl") + "universal2.whl")
                        fuse_wheels(x86_64_whl, arm64_whl, universal2_whl)
                        self.fix_wheel_tags(universal2_whl)
                    else: # Universal2 wheel exists on pypi, just download it
                        if io.is_verbose():
                            io.write_line(
                                f"<debug>'{package_info['name']}' universal2 wheel available on pypi, downloading...'</>"
                            )
                        env.run_pip("download", "--only-binary=:all:", "--no-deps", "--platform", platform, "--no-cache-dir", "-d", download_dir, package_specifier, call=True, stdout=stdout)
                    env.run_pip("install", "--force-reinstall", "--only-binary=:all:", "--no-deps", "--no-cache-dir", "--no-index", "--find-links", download_dir, package_specifier, call=True, stdout=stdout)

    def get_update_packages(self, pyproject):
        return pyproject.data.get("tool", {}).get(NAME, {}).get("dependencies")

    def should_cache_wheels(self, pyproject):
        return pyproject.data.get("tool", {}).get(NAME, {}).get("cache-wheels", False)

    def get_package_info(self, package_name, lock_data):
        for package in lock_data["package"]:
            if package["name"] == package_name:
                return package
        raise ValueError(f"Could not find package '{package_name}'")

    def get_version(self, package_info):
        return package_info["version"]

    def get_arm64_sys_tags(self):
        platforms = packaging.tags.mac_platforms(arch="arm64")
        return packaging.tags.cpython_tags(platforms=platforms)

    def get_x86_sys_tags(self):
        platforms = packaging.tags.mac_platforms(arch="x86_64")
        return packaging.tags.cpython_tags(platforms=platforms)

    def get_universal2_sys_tags(self):
        platforms = packaging.tags.mac_platforms(arch="universal2")
        return packaging.tags.cpython_tags(platforms=platforms)

    def get_universal2_platform(self, package_info):
        for tag in self.get_universal2_sys_tags():
            tag_str = str(tag)
            for file in package_info["files"]:
                if tag_str in file["file"]:
                    return tag.platform
        return None

    def get_specific_platforms(self, package_info):
        arm64_platform = None
        for tag in self.get_arm64_sys_tags():
            if arm64_platform is not None:
                break
            tag_str = str(tag)
            for file in package_info["files"]:
                if tag_str in file["file"]:
                    arm64_platform = tag.platform
                    break
        if arm64_platform is None:
            raise ValueError(f"Could not find compatible arm64 wheel for '{package_info['name']}'")

        x86_64_platform = None
        for tag in self.get_x86_sys_tags():
            if x86_64_platform is not None:
                break
            tag_str = str(tag)
            for file in package_info["files"]:
                if tag_str in file["file"]:
                    x86_64_platform = tag.platform
                    break
        if x86_64_platform is None:
            raise ValueError(f"Could not find compatible x86_64 wheel for '{package_info['name']}'")

        return (arm64_platform, x86_64_platform)

    def needs_universal2(self, package_info):
        for tag in packaging.tags.sys_tags():
            tag_str = str(tag)
            for file in package_info["files"]:
                if tag_str in file["file"]:
                    return not (tag.platform == "any" or "universal2" in tag.platform)
        return False # Its an sdist, there is no wheel

    def fix_wheel_tags(self, wheel_path):
        # delocate will leave the wheel tag whatever it was from the original
        # file that gets copied in. This updates it to be universal2
        name, version, _, tags = parse_wheel_filename(wheel_path.name)
        info_path = Path(f"{name}-{version}.dist-info") / "WHEEL"
        with InWheelCtx(wheel_path) as ctx:
            info = read_pkg_info(info_path)
            del info["Tag"]
            info["Tag"] = str(list(tags)[0])
            write_pkg_info(info_path, info)
            ctx.out_wheel = wheel_path

    @contextmanager
    def pip_download_dir(self, cache_wheels=False):
        if cache_wheels:
            yield user_cache_path(NAME, appauthor=False) / "pip-downloads"
        else:
            with temporary_directory() as temp_dir:
                yield temp_dir
