from ..core import config, run_drive_backup, progress
from ..core.drivebackup import console
from rich.progress import Progress, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn, TaskProgressColumn
from rich.table import Column
from rich.text import Text
import argparse, logging, sys

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--destination", help="The destination in the file system where the backup should be stored. Default is the current directory.")
    parser.add_argument("-n", "--backup-name", help="The name of the backup. This will be used as the name of the folder the backup source is stored in. Default is 'Google Drive Backup' followed by the date.")
    parser.add_argument("-t", "--backup-type", help="The type of backup. 'complete' will create a new backup, leaving the previous backup untouched. \
                                              'update' will update the previous backup to have the current files and folders from your Google Drive. \
                                              'increment' creates a new backup, moving files that have not changed since the previous backup into the new backup, and leaving only old files remaining in the previous backup. \
                                              Default is 'complete'.",
                                              choices=['complete', 'update', 'increment'])
    parser.add_argument("-c", "--backup-config", nargs="?", const=True, help="The path to the .bkp backup config file to use to set the config options for the backup. Drive \
                                              Backup creates this file when it successfully completes a backup. The file is placed in the backup's destination directory if this flag isn't present. \
                                              If this flag is given without a path the current directory and default name is used to find the file. If this flag is given with a directory, \
                                              the directory is used with the default name to find the file. If this flag is given with a file, that is used to find the file. If other flags are given along with this flag, \
                                              they will override the config set in the .bkp file.")
    parser.add_argument("--prev-backup-name", help="The name of the previous backup. If the previous backup did not have the default name, this can be \
                                                     used to tell drive backup what it is. If left blank, Drive Backup will look for the default name from backup_name with the most recent date.")
    parser.add_argument("-s", "--source", help="The source folder on Google Drive to backup.")
    parser.add_argument("--source-id", help="The source folder id on Google Drive to backup. Default is everything on Google Drive.")
    parser.add_argument("--google-doc-mimeType", help="The desired mimeType conversion on all compatible Google Document types. Default is to convert documents to their 'msoffice' compatible type.", choices=['msoffice', 'pdf'])
    parser.add_argument("--client-credentials", help="The path to a client credential file. This can possibly help download your files from Google Drive if you are having difficulties.")
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set the logging level of detail. Default is 'INFO'")
    parser.add_argument("--log-filter", help="Only log messages generated from Google Drive Backup, ignore messages from other libraries. If neither option is given, all messages are logged.", action=argparse.BooleanOptionalAction)
    parser.add_argument("--log-changes", help="Only log files that need to be downloaded. If neither option is given, all files are logged.", action=argparse.BooleanOptionalAction)
    parser.add_argument("--log-path", nargs="?", const=False, help="The path to the log file. If not set or set with no path, the log file is stored alongside the directory where the backup is stored. If this flag is set with a directory, the log file is stored in the \
                                            directory with the default name. If this flag is set with a file, it is used to store the logs.")
    args = parser.parse_args()
    args = { key:value for key, value in vars(args).items() if value is not None }
    config.set_config(args)

    setup_logging()

    with progress_bar:
        progress.subscribe(update)
        run_drive_backup()
