import click
from shlex import split
from pathlib import Path
import subprocess, platform, shutil, sys

SCRIPT_PATH = Path.cwd() / "src/drive_backup/__main__.py"

PYINSTALLER_BUILD_COMMAND = f"""
pyinstaller "{SCRIPT_PATH}"
    --name "dbackup"
    --distpath "{{distpath}}"
    --additional-hooks-dir hooks
    --clean
    --noconfirm
"""

PROJECT_NAME = "Drive Backup"
NOTIFICATIONS_PROJECT_NAME = "Drive Backup Notifications"

DEFAULT_DISTPATH = Path.cwd() / 'dist'

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS, help=f"Build/Archive {PROJECT_NAME} app binary.")
def cli():
    pass

@cli.command()
@click.option("--distpath", default=str(DEFAULT_DISTPATH), help="The location to put the binary build. (Default: './dist')")
@click.option("--macos-codesign-identity", envvar="MACOS_CODESIGN_IDENTITY", help="Sign the app with the provided identity (macOS only).")
@click.option("--macos-target-arch", default="universal2", help="The target architecture to build for (macOS only).")
def build(distpath, macos_codesign_identity, macos_target_arch):
    print("Setting up PyInstaller build...", file=sys.stderr)
    build_command = PYINSTALLER_BUILD_COMMAND
    if platform.system() == "Darwin":
        print(f"Adding '--target-arch {macos_target_arch}' for macOS build.", file=sys.stderr)
        build_command += f"--target-arch {macos_target_arch}"
        if macos_codesign_identity is not None:
            print("Adding '--codesign-identity' for macOS build.", file=sys.stderr)
            build_command += f' --codesign-identity "{macos_codesign_identity}"'
    ret_code = subprocess.run(split(build_command.format(distpath=distpath))).returncode
    if ret_code != 0:
        return ret_code
    app_path = Path(distpath).resolve() / "dbackup"
    if platform.system() == "Darwin" and macos_codesign_identity is not None:
        python_executable = next(app_path.glob("_internal/Python.framework/Versions/[.1-9]*/Python"))
        ret_code = subprocess.run(["/usr/bin/codesign", "--force", "-s", macos_codesign_identity, "--timestamp", "--options", "runtime", str(python_executable), "-v"]).returncode
        if ret_code != 0:
            return ret_code
    print(f"Rename app directory to '{PROJECT_NAME}'.", file=sys.stderr)
    rename_path = app_path.parent / PROJECT_NAME
    if rename_path.exists():
        shutil.rmtree(str(rename_path))
    app_path = app_path.rename(rename_path)
    print(f"Binary created at '{app_path}'", file=sys.stderr)
    print(str(app_path))

@cli.command()
@click.option("--app-path", default=str(DEFAULT_DISTPATH / PROJECT_NAME),
    help="The location of the binary build directory. (Default: './dist/Drive Backup')"
)
def add_notifications(app_path):
    if platform.system() in ["Darwin", "Windows"]:
        platform_dir = "mac" if platform.system() == "Darwin" else "windows"
        relative_pkg_path = Path("drive_backup") / "core" / "notifications" / platform_dir / "build"
        src_path = Path.cwd() / "src" / relative_pkg_path
        dst_path = Path(app_path) / "_internal" / relative_pkg_path
        if platform.system() == "Darwin":
            print("Copying macOS notifications app into app build.", file=sys.stderr)
            src_path = src_path / f"{NOTIFICATIONS_PROJECT_NAME}.app"
            dst_path = dst_path / f"{NOTIFICATIONS_PROJECT_NAME}.app"
            shutil.copytree(src_path, dst_path)
        elif platform.system() == "Windows":
            print("Copying windows notifications app into app build.", file=sys.stderr)
            src_path = src_path / f"{NOTIFICATIONS_PROJECT_NAME}.exe"
            if not dst_path.exists():
                dst_path.mkdir(parents=True)
            shutil.copy2(src_path, dst_path)

@cli.command()
@click.option("--app-path", default=str(DEFAULT_DISTPATH / PROJECT_NAME),
    help="The location of the binary build directory. (Default: './dist/Drive Backup')"
)
@click.option("--archive-path", default=str(DEFAULT_DISTPATH / PROJECT_NAME.replace(" ","_")),
    help="The location to create the archive file, minus any format-specific extension. (Default: './dist/Drive_Backup')"
)
@click.option("--archive-name",
    help="The name of the archive file. This will replace the final path component of 'archive_path' if given."
)
@click.option("--format", help="Force a specific archive format to be used. (Default: zip on Windows, gztar otherwise)")
def archive(app_path, archive_path, archive_name, format):
    app_path = Path(app_path).resolve()
    archive_path = Path(archive_path).resolve()
    if archive_name is not None:
        archive_path = archive_path.parent / archive_name
    format = format or ('zip' if platform.system() == 'Windows' else 'gztar')
    print(f"Creating a {format} archive of the app.", file=sys.stderr)
    # We need this to preseve symlinks...because shutil won't >:0
    if format == "zip" and platform.system() == "Darwin":
        archive_name = str(archive_path) + ".zip"
        ret_code = subprocess.run(["ditto", "-c", "-k", "--keepParent", str(app_path), archive_name]).returncode
        if ret_code != 0:
            return ret_code
    else:
        archive_name = shutil.make_archive(str(archive_path), format, root_dir=str(app_path.parent), base_dir=app_path.name)
    print(f"Archive created at '{archive_name}'", file=sys.stderr)
    print(archive_name)

@cli.command()
@click.option("--version", help="The version of the app to use for making the name.", default="0.0.0.dev0")
def archive_name(version):
    project_name = PROJECT_NAME.replace(" ", "_")
    project_platform = platform.system().lower()
    project_arch = platform.machine().lower()
    if project_platform == "darwin":
        project_platform = "macos"
        project_arch = "universal2"
    print(f"{project_name}-{version}-{project_platform}-{project_arch}")

if __name__ == '__main__':
    cli()
