import click
from shlex import split
from pathlib import Path
import subprocess, platform, shutil, sys

PYINSTALLER_BUILD_COMMAND = """
pyinstaller src/drive_backup/__main__.py
    --name "dbackup"
    --additional-hooks-dir hooks
    --clean
    --noconfirm
"""

PROJECT_NAME = "Drive Backup"
NOTIFICATIONS_PROJECT_NAME = "Drive Backup Notifications"

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS, help=f"Build/Archive {PROJECT_NAME} app binary.")
def cli():
    pass

@cli.command()
@click.option("--macos-codesign-identity", envvar="MACOS_CODESIGN_IDENTITY", help="Sign the app with the provided identity (macOS only).")
@click.option("--macos-target-arch", default="universal2", help="The target architecture to build for (macOS only).")
def build(macos_codesign_identity, macos_target_arch):
    print("Setting up PyInstaller build...", file=sys.stderr)
    build_command = PYINSTALLER_BUILD_COMMAND
    if platform.system() == "Darwin":
        print(f"Adding '--target-arch {macos_target_arch}' for macOS build.", file=sys.stderr)
        build_command += f"--target-arch {macos_target_arch}"
        if macos_codesign_identity is not None:
            print("Adding '--codesign-identity' for macOS build.", file=sys.stderr)
            build_command += f' --codesign-identity "{macos_codesign_identity}"'
    ret_code = subprocess.run(split(build_command)).returncode
    if ret_code != 0:
        return ret_code
    print(f"Rename app directory to '{PROJECT_NAME}'.", file=sys.stderr)
    app_path = Path.cwd() / "dist" / "dbackup"
    app_path.rename(app_path.parent / PROJECT_NAME)

@cli.command()
def add_notifications():
    if platform.system() in ["Darwin", "Windows"]:
        platform_dir = "mac" if platform.system() == "Darwin" else "windows"
        relative_pkg_path = Path("drive_backup") / "core" / "notifications" / platform_dir / "build"
        src_path = Path.cwd() / "src" / relative_pkg_path
        dst_path = Path.cwd() / "dist" / PROJECT_NAME / "_internal" / relative_pkg_path
        if platform.system() == "Darwin":
            print("Copying macOS notifications app into app build.", file=sys.stderr)
            src_path = src_path / f"{NOTIFICATIONS_PROJECT_NAME}.app"
            dst_path = dst_path / f"{NOTIFICATIONS_PROJECT_NAME}.app"
            shutil.copytree(src_path, dst_path)
        elif platform.system() == "Windows":
            print("Copying windows notifications app into app build.", file=sys.stderr)
            src_path = src_path / f"{NOTIFICATIONS_PROJECT_NAME}.exe"
            shutil.copy2(src_path, dst_path)

@cli.command()
@click.option("--name", default=PROJECT_NAME.replace(" ","_"), help="The name of the archive file to create.")
@click.option("--format", help="Force a specific archive format to be used. (Default: zip on Windows, gztar otherwise)")
def archive(name, format):
    app_path = Path.cwd() / "dist" / name
    format = format or ('zip' if platform.system() == 'Windows' else 'gztar')
    print(f"Creating a {format} archive of the app.", file=sys.stderr)
    archive_name = shutil.make_archive(app_path, format, root_dir=app_path.parent, base_dir=app_path.name)
    print(f"Archive created at '{archive_name}'", file=sys.stderr)
    print(archive_name)

@cli.command()
@click.option("--version", help="The version of the app to use for making the name.", default="0.0.0.dev0")
def archive_name(version):
    project_name = PROJECT_NAME.replace(" ", "_")
    project_platform = platform.system().lower()
    project_arch = platform.machine()
    if project_platform == "darwin":
        project_platform = "macos"
        project_arch = "universal2"
    return f"{project_name}-{version}-{project_arch}"

if __name__ == '__main__':
    cli()
