from drive_backup.core import console, config, progress, run_drive_backup, sign_out_user, sign_in_user, view_user_info, get_macos_notification_authorization
from rich.progress import Progress, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn, TaskProgressColumn
from rich.table import Column
from rich.text import Text
import platform
import click
import logging, sys

class GDBMofNCompleteColumn(MofNCompleteColumn):
    def render(self, task):
        if task.total is None:
            return Text()
        return super().render(task)

columns = [
    TextColumn("[progress.description]{task.description}"),
    BarColumn(bar_width=None, complete_style="bar.finished", pulse_style="bar.finished"),
    GDBMofNCompleteColumn(),
    TaskProgressColumn(),
    TimeElapsedColumn(table_column=Column(justify="right", min_width=7))
]
progress_bar = Progress(*columns, console=console)
task = progress_bar.add_task("[green]Ready...", total=None, visible=False)

def update(progress):
    total = None
    completed = progress.file_cnt
    visible = False
    description = "[green]Ready..."

    if progress.state == progress.state.INITIATE:
        description = "[green]Initiated..."
    elif progress.state == progress.state.PREPARE:
        description = "[green]Preparing..."
    elif progress.state == progress.State.DOWNLOAD:
        total = progress.total_files
        description = "[green]Downloading..."
    elif progress.state == progress.state.PAUSE:
        description = "[yellow]Paused..."
    elif progress.state == progress.state.COMPLETE:
        description = "[green]Completed..."
    elif progress.state == progress.state.STOP:
        description = "[red]Stopped..."
        columns[1].finished_style = "bar.complete"
        columns[1].complete_style = "bar.complete"
        if progress.total_files == 0:
            total = 0

    if progress.state in (progress.State.INITIATE, progress.State.PREPARE, progress.State.DOWNLOAD, progress.state.COMPLETE, progress.state.STOP):
        visible = True

    progress_bar.update(task, description=description, completed=completed, total=total, visible=visible)

    if progress_bar.live.is_started and progress.state == progress.state.PAUSE:
        progress_bar.stop()
    elif not progress_bar.live.is_started and progress.state != progress.state.PAUSE:
        progress_bar.start()



def setup_logging():
    root_logger = logging.getLogger()

    class custom_filter():
        def filter(self, record):
            if record.levelname == 'ERROR' and record.exc_info:
                return 0
            return 1

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel('ERROR')
    stream_handler.addFilter(custom_filter())

    stream_formatter = logging.Formatter('\r%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    stream_handler.setFormatter(stream_formatter)

    root_logger.addHandler(stream_handler)


class HelpFormatter(click.HelpFormatter):
    def write_usage(self, prog: str, args: str = "", prefix: str | None = None) -> None:
        super().write_usage(prog, args=args, prefix=click.style("Usage: ", bold=True))

    def write_heading(self, heading: str) -> None:
        super().write_heading(click.style(heading, bold=True))

    def write_dl(
        self,
        rows,
        col_max: int = 30,
        col_spacing: int = 2,
    ) -> None:
        rows = [(click.style(first, fg="cyan"), second) for (first, second) in rows]
        super().write_dl(rows, col_max, col_spacing)

click.Context.formatter_class = HelpFormatter

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS, help="A simple way to backup your Google Drive locally.")
@click.version_option(package_name="drive-backup", message=f"{click.style('Drive Backup', bold=True)} (version {click.style('%(version)s', fg='cyan')})")
def cli():
    pass

@cli.group(help="Manage the user/user credential for Drive Backup.")
def user():
    pass

@user.command("sign-out", help="Remove the user credential to sign out the user.")
def sign_out_drive_crdentials():
    sign_out_user()

@user.command("sign-in", help="Sign in to Google to acquire a user credential.")
@click.option("--client-credentials", help="The path to a client credential file. This can possibly help download your files from Google Drive if you are having difficulties.")
def sign_in_drive_credentials(client_credentials):
    sign_in_user(client_credentials)

@user.command("info", help="Show the current user's info.")
def view_credential_info():
    view_user_info()

@cli.command("backup", help="Run a backup for your Google Drive.")
@click.option("-d", "--destination", help="The destination in the file system where the backup should be stored. Default is the current directory.")
@click.option("-n", "--backup-name", help="The name of the backup. This will be used as the name of the folder the backup source is stored in. Default when not given or empty is 'Google Drive Backup' followed by the date.")
@click.option("-t", "--backup-type", type=click.Choice(['complete', 'update', 'increment'], case_sensitive=False),
    help=("The type of backup. 'complete' will create a new backup, leaving the previous backup untouched. "
    "'update' will update the previous backup to have the current files and folders from your Google Drive. "
    "'increment' creates a new backup, moving files that have not changed since the previous backup into the new backup, and leaving only old files remaining in the previous backup. "
    "Default is 'complete'.")
)
@click.option("-c", "--backup-config", is_flag=False, flag_value=True,
    help=("The path to the .bkp backup config file to use to set the config options for the backup. Drive "
    "Backup creates this file when it successfully completes a backup. The file is placed in the backup's destination directory if this flag isn't present. "
    "If this flag is given without a path the current directory and default name is used to find the file. If this flag points to a directory, "
    "the directory is used with the default name to find the file. If this flag points to a file, that is used to find the file. If other flags are given along with this flag, "
    "they will override the config set in the .bkp file.")
)
@click.option("--prev-backup-name",
    help=("The name of the previous backup. If the previous backup did not have the default name, this can be "
    "used to tell drive backup what it is. If not given or empty, Drive Backup will look for the default name from backup_name with the most recent date.")
)
@click.option("-s", "--source", help="The source folder on Google Drive to backup. If not given or empty, the default is everything on Google Drive.")
@click.option("--source-id", help="The source folder id on Google Drive to backup. Default is 'root', which is everything on Google Drive.")
@click.option("--google-doc-mimeType", type=click.Choice(['msoffice', 'pdf'], case_sensitive=False),
    help="The desired mimeType conversion on all compatible Google Document types. Default is to convert documents to their 'msoffice' compatible type."
)
@click.option("--client-credentials", help="The path to a client credential file. This can possibly help download your files from Google Drive if you are having difficulties.")
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
    help="Set the logging level of detail. Default is 'INFO'"
)
@click.option("--log-filter/--no-log-filter", default=None, help="Only log messages generated from Google Drive Backup, ignore messages from other libraries. If neither option is given, all messages are logged.")
@click.option("--log-changes/--no-log-changes", default=None, help="Only log files that need to be downloaded. If neither option is given, all files are logged.")
@click.option("--log-path",
    help=("The path to the log file. If not set or set with an empty path, the log file is stored alongside the directory where the backup is stored. If this flag points to a directory, the log file is stored in the "
    "directory with the default name. If this flag points to a file, it is used to store the logs.")
)
@click.option("--notifications/--no-notifications", default=None, help="Will (not) trigger notifications on completion or failure. If neither option is given, notifications will be triggered.")
def run_backup(**args):
    args = { key:value for key, value in args.items() if value is not None }
    config.set_config(args)

    setup_logging()

    if platform.system() == "Darwin" and config.notifications:
        get_macos_notification_authorization()

    with progress_bar:
        progress.subscribe(update)
        run_drive_backup()

def main():
    rc = 1
    try:
        cli(auto_envvar_prefix="DRIVE")
        rc = 0
    except Exception as e:
        print('Error:', e, file=sys.stderr)
    return rc
