from drive_backup.core.console import console
from importlib import resources
from pathlib import Path
import platform, subprocess, os, logging

def show_notification(title, body, image=None):
    notification_dir = resources.files("drive_backup.core.notifications")

    try:
        if platform.system() == "Windows":
            if image is None:
                image = resources.files("drive_backup.resources") / "drive-backup-icon.png"
            win_drive_notification = notification_dir / "windows" / "build" / "Drive Backup Notifications.exe"
            subprocess.Popen([win_drive_notification, "--title", title, "--body", body, "--image", image])
        elif platform.system() == "Darwin":
            mac_drive_notification = notification_dir / "mac" / "build" / "Drive Backup Notifications.app" / "Contents" / "MacOS" / "Drive Backup Notifications"
            subprocess.Popen([mac_drive_notification, "--title", title, "--body", body])
    except FileNotFoundError:
        logger = logging.getLogger(__name__)
        logger.info("Notification executable not found, unable to show notification.")
    except (os.error, subprocess.SubprocessError):
        logger = logging.getLogger(__name__)
        logger.warning(f"Unable to successfully show notification.", exc_info=True)
        return False
    return True

def get_macos_notification_authorization():
    if platform.system() != "Darwin":
        return
    prompted_path = Path.home() / "Library" / "Application Support" / "drive-backup" / "notification-authorization"
    already_prompted = prompted_path.is_file()
    if already_prompted:
        return
    prompted_path.parent.mkdir(exist_ok=True)
    prompted_path.touch()
    console.print(
        "[bold]Drive Backup[/] will trigger a notification to let you know when a backup has completed or failed. "
        "In order to allow these notifications you must give [bold]Drive Backup[/] permission to show them by "
        "selecting [green]Allow[/] in the prompt from the [cyan]Notification Center[/] now. You can always change the permission "
        "in the future by going to [cyan]Settings[/] -> [cyan]Notifications[/]."
    )
    try:
        mac_drive_notification = resources.files("drive_backup.core.notifications") / "mac" / "build" / "Drive Backup Notifications.app" / "Contents" / "MacOS" / "Drive Backup Notifications"
        subprocess.run([mac_drive_notification, "--authorization"])
    except FileNotFoundError:
        logger = logging.getLogger(__name__)
        logger.info("Notification executable not found, unable to get notification authorization.")
    except (os.error, subprocess.SubprocessError):
        logger = logging.getLogger(__name__)
        logger.warning(f"Unable to get notification authorization.", exc_info=True)
