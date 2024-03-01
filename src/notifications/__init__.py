from ..core.drivebackup import APPLICATION_NAME
import importlib.resources as resources
import platform, subprocess, os, logging

def show_notification(title=None, body=None, image=None):
    if title is None:
        title = APPLICATION_NAME
    if body is None:
        body = "Drive Backup is complete!"

    notification_dir = resources.files("src.notifications")

    try:
        if platform.system() == "Windows":
            if image is None:
                image = notification_dir.parents[1] / "drive-backup-icon.png"
            win_drive_notification = notification_dir / "windows" / "build" / "Drive Backup Notifications.exe"
            subprocess.Popen([win_drive_notification, "--title", title, "--body", body, "--image", image])
        elif platform.system() == "Darwin":
            mac_drive_notification = notification_dir / "mac" / "build" / "Drive Backup Notifications.app" / "Contents" / "MacOS" / "Drive Backup Notifications"
            subprocess.Popen([mac_drive_notification, "-title", title, "-body", body])
    except (os.error, subprocess.SubprocessError):
        logger = logging.getLogger(__name__)
        logger.warning(f"Unable to successfully show notification.", exc_info=True)
        return False
    return True
