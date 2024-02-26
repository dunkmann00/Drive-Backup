from ..core import config, run_drive_backup, progress
from ..core.drivebackup import APPLICATION_NAME, console
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
    parser.add_argument("--destination", help="The destination in the file system where the backup should be stored. Default is the current directory.")
    parser.add_argument("--backup_name", help="The name of the backup. This will be used as the name of the folder the backup source is stored in. Default is 'Google Drive Backup' followed by the date.")
    parser.add_argument("--backup_type", help="The type of backup. 'complete' will create a new backup, leaving the previous backup untouched. \
                                              'update' will update the previous backup to have the current files and folders from your Google Drive. \
                                              'increment' creates a new backup, moving files that have not changed since the previous backup into the new backup, and leaving only old files remaining in the previous backup. \
                                              Default is 'complete'.",
                                              choices=['complete', 'update', 'increment'])
    parser.add_argument("--prev_backup_name", help="The name of the previous backup. If the previous backup did not have the default name, this can be \
                                                     used to tell drive backup what it is. If left blank, Drive Backup will look for the default name from backup_name with the most recent date.")
    parser.add_argument("--source", help="The source folder on Google Drive to backup.")
    parser.add_argument("--source_id", help="The source folder id on Google Drive to backup. Default is everything on Google Drive.")
    parser.add_argument("--google_doc_mimeType", help="The desired mimeType conversion on all compatible Google Document types. Default is to convert documents to their 'msoffice' compatible type.", choices=['msoffice', 'pdf'])
    parser.add_argument(
        '--logging_level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set the logging level of detail. Default is 'INFO'")
    parser.add_argument("--logging_filter", help="When this flag is present, only messages generated from Google Drive Backup will be logged, not other libraries.", action='store_true')
    parser.add_argument("--logging_changes", help="When this flag is present, only log files that need to be downloaded.", action='store_true')
    args = parser.parse_args()
    args = { key:value for key, value in vars(args).items() if value is not None }
    config.set_config(args)

    setup_logging()

    with progress_bar:
        progress.subscribe(update)
        run_drive_backup()

    if sys.platform.startswith('win32'):
        import zroya
        zroya.init(APPLICATION_NAME, "GWaters", "Drive-Backup", "Backup", "1.0")
        template = zroya.Template(zroya.TemplateType.ImageAndText2)
        template.setFirstLine(APPLICATION_NAME)
        template.setSecondLine("Drive Backup is complete!")
        template.setImage('drive-backup-icon.png')
        zroya.show(template)
    elif sys.platform.startswith('darwin'):
        import subprocess
        subprocess.run(["notifications/mac/Drive Backup Notifications.app/Contents/MacOS/Drive Backup Notifications", "-title", APPLICATION_NAME, "-body", "Drive Backup is complete!"])
