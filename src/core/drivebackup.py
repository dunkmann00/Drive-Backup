# -*- coding: utf-8 -*-

import os
import io
import sys
import re
import logging
import time
import calendar
import shutil
import json
from pathlib import Path
from .dfsmap import DriveFileSystemMap
from .config import config
from .progress import progress
from rich.console import Console
from rich.prompt import Confirm
from rich.text import Text

from googleapiclient import discovery
from googleapiclient import errors
from googleapiclient.http import MediaIoBaseDownload

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CLIENT_SECRET_FILE = 'credentials.json'
APPLICATION_NAME = 'Drive Backup'
MIME_TYPES = {
    'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.google-apps.drawing': 'application/pdf',
    'application/vnd.google-apps.script': 'application/vnd.google-apps.script+json'
}
FILE_EXTENSIONS = {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'application/pdf': 'pdf',
    'application/vnd.google-apps.script+json': 'json'
}

drive_file_system = None
download_errors = 0

console = Console(highlight=False)

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    credential_dir = Path("~/.credentials").expanduser()
    if not credential_dir.exists():
        credential_dir.mkdir()
    credential_path = credential_dir / 'drive-python-quickstart.json'

    credentials = None
    if credential_path.exists():
        credentials = Credentials.from_authorized_user_file(str(credential_path), SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        logger = logging.getLogger(__name__)
        logger.info(f'Storing credentials to {credential_path}', )
        with credential_path.open("w") as token:
            token.write(credentials.to_json())
    return credentials

def get_source_folder():
    logger = logging.getLogger(__name__)
    if config.source:
        try:
            results = service.files().list(fields="files(id, name, mimeType)", q=f"'root' in parents and name='{config.source}' and trashed=false").execute()
        except:
            logger.critical('Error initiating backup.', exc_info=True)
            stop_backup()
        items = results.get('files', [])
    else:
        try:
            results = service.files().get(fields="id, name, mimeType", fileId=config.source_id).execute()
        except:
            logger.critical('Error initiating backup.', exc_info=True)
            stop_backup()
        items = [results]

    if not items:
        logger.critical('Source folder not found.')
    elif len(items) == 1:
        if items[0]['mimeType'] == 'application/vnd.google-apps.folder':
            return items[0]
        else:
            item = items[0]
            logger.critical(f"Item found is not a folder: {item['name']}  {item['mimeType']} ({item['id']})")
    else:
        msg = ''
        for item in items:
            if msg != '':
                msg += ', '
            msg += f"{item['name']}  {item['mimeType']} ({item['id']})"
        logger.critical(f'Multiple items with the same name: {msg}')

    return '';

def get_save_destination():
    parent_destination = config.destination
    if config.backup_name:
        backup_name = config.backup_name
    else:
        current_time = time.localtime()
        date_string = f'{current_time.tm_mon}-{current_time.tm_mday}-{current_time.tm_year}'
        backup_name = 'Google Drive Backup ' + date_string

    # save_destination = add_path(parent_destination, backup_name)
    save_destination = parent_destination / backup_name
    recent_backup_destination = get_recent_backup(parent_destination, backup_name)

    if not save_destination.exists():
        if config.backup_type == 'complete' or config.backup_type == 'increment':
            save_destination.mkdir(parents=True)
        elif config.backup_type == 'update':
            if recent_backup_destination:
                recent_backup_destination.rename(save_destination)
            else:
                save_destination.mkdir(parents=True)

    if config.backup_type == 'update':
        recent_backup_destination = None

    return (save_destination, recent_backup_destination)


def get_recent_backup(directory, current_backup):
    if config.prev_backup_name:
        prev_destination = directory / config.prev_backup_name
        if prev_destination.is_dir() and config.prev_backup_name != current_backup:
            return prev_destination
        else:
            return None
    else:
        if not directory.exists():
            return None
        directory_entries = directory.iterdir()
        default_name = re.compile('Google Drive Backup ([0-9][0-9]?-[0-9][0-9]?-[0-9][0-9][0-9][0-9])')
        most_recent_entry = None
        most_recent_date = None
        for entry in directory_entries:
            match = default_name.match(entry.name)
            if match:
                date_string = match.group(1)
                date = time.strptime(date_string, u"%m-%d-%Y")
                if entry.name != current_backup and (most_recent_date == None or date > most_recent_date):
                    most_recent_date = date
                    most_recent_entry = entry
        if most_recent_entry is not None:
            return most_recent_entry
        else:
            return None


def build_dfsmap(source_folder):
    logger = logging.getLogger(__name__)
    drive_file_system = DriveFileSystemMap(source_folder)

    next_page_token = None
    while True:
        results = service.files().list(pageSize=1000,
                                       fields="nextPageToken, files(id, name, mimeType, modifiedTime, parents, size)",
                                       q=u"trashed=false",
                                       pageToken=next_page_token,
                                       orderBy='folder desc').execute(num_retries=5)
        if not results:
            logger.error('Could not prepare the backup succesfully. Check the log for more details.')
            results = {}
        for object in results.get('files', []):
            if object['mimeType'] == 'application/vnd.google-apps.folder':
                drive_file_system.add_folder(object)
            else:
                drive_file_system.add_file(object)

        next_page_token = results.get('nextPageToken')
        if next_page_token is None:
            break

    return drive_file_system


def get_folder(parent_dest, prev_parent_dest=None, drive_folder_object=None):
    global download_errors
    logger = logging.getLogger(__name__)
    if not drive_folder_object:
        drive_folder_object = drive_file_system.get_root_folder()

    # folder_location = add_path(parent_dest, drive_folder_object.name)
    folder_location = parent_dest / drive_folder_object.name
    prev_folder_location = None
    if prev_parent_dest:
        # prev_folder_location = add_path(prev_parent_dest, drive_folder_object.name)
        prev_folder_location = prev_parent_dest / drive_folder_object.name

    if not folder_location.exists():
        try:
            folder_location.mkdir(parents=True)
        except:
            logger.critical(f'Could not create folder: {folder_location}', exc_info=True)
            stop_backup()
        logger.info(f'{folder_location} : Folder Created')


    file_names = set()
    for file in drive_folder_object.files.values():
        if file['name'] in file_names:
            file['name'] = change_name(file['name'])
        file_names.add(file['name'])

        file_location = get_file(file, folder_location, prev_folder_location)
        if file_location:
            logger.info(f'{file_location} : created')
            download_errors = 0
        else:
            if file_location == None:
                download_errors += 1
                if download_errors >= 5:
                    logger.critical('Multiple consecutive failed file downloads. Stopping backup, check log for more details.')
                    stop_backup()
        progress.file_cnt += 1

    file_names = None

    progress.folder_cnt += 1

    folder_names = set()
    for folder in drive_folder_object.folders.values():
        if folder['name'] in folder_names:
           folder['name'] = change_name(folder['name'])
           drive_file_system.set_folder_name(folder['id'], folder['name'])
        folder_names.add(folder['name'])

        child_folder_object = drive_file_system.get_folder(folder['id'])
        get_folder(folder_location, prev_parent_dest=prev_folder_location, drive_folder_object=child_folder_object)

def get_file(drive_file, parent_folder, old_parent_folder=None):
    logger = logging.getLogger(__name__)
    if re.match('application/vnd\.google-apps\..+', drive_file['mimeType']):
        mimeType_convert = get_mimeType(drive_file['mimeType'])
        if not mimeType_convert:
            logger.info(f"{parent_folder / drive_file['name']} : File is not a downloadable Google Document")
            return ''
        request = service.files().export_media(fileId=drive_file['id'],mimeType=mimeType_convert)
        drive_file_name = f"{drive_file['name']}.{FILE_EXTENSIONS.get(mimeType_convert)}"
    else:
        request = service.files().get_media(fileId=drive_file['id'])
        drive_file_name = drive_file['name']

    if not parent_folder.exists():
        logger.critical(f'Backup destination folder does not exist: {parent_folder}  Restart backup')
        stop_backup()

    # file_destination = add_path(parent_folder, drive_file_name)
    file_destination = parent_folder / drive_file_name
    old_file_destination = None
    if old_parent_folder and old_parent_folder.exists():
        # old_file_destination = add_path(old_parent_folder, drive_file_name)
        old_file_destination = old_parent_folder / drive_file_name

    if not should_download(drive_file, file_destination) or (old_file_destination and not should_download(drive_file, old_file_destination)):
        if not config.logging_changes:
            logger.info(f'{file_destination} : Already downloaded current version')
        if old_file_destination and old_file_destination.exists(): #need the extra check to ensure no errors in the event of duplicate files with same name
            if config.backup_type == 'complete':
                shutil.copy2(old_file_destination, file_destination)
            elif config.backup_type == 'increment':
                shutil.move(old_file_destination, file_destination)
        return ''


    fh = io.FileIO(file_destination, mode='wb')
    if drive_file.get('size') == '0':
        fh.close()
        logger.info(f'{file_destination} : File has no data')
        return ''

    downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)
    complete = False


    while complete is False:
        try:
            status, complete = downloader.next_chunk(num_retries=5)
            if status.total_size == None:
                complete = True
                logger.warning(f'{file_destination} : File may not have been fully downloaded.')
                break
        except errors.HttpError as e:
            if is_abusive_file_error(e.content):
                progress.state = progress.state.PAUSE
                prompt = (
                    '[bold cyan]Problem downloading:[/]\n' +
                    f"'[yellow]{drive_file_name}[/]' is marked as potential malware or spam.\n"
                    "[bold cyan]Are you sure you want to download it?[/]"
                )
                download_abusive_file = Confirm.ask(prompt, console=console)
                console.print()
                progress.state = progress.state.DOWNLOAD
                if download_abusive_file:
                    request = service.files().get_media(fileId=drive_file['id'], acknowledgeAbuse=True)
                    downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)
                else:
                    break
            else:
                logger.exception('Could not complete request due to error.')
                break


    fh.close()

    if not complete:
        logger.error(f'{file_destination} : Was not downloaded due to an error. Check the log for more details.')
        file_destination.unlink()
    else:
        driveFileTime = time.strptime(drive_file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        driveFileTimeSecs = calendar.timegm(driveFileTime)
        os.utime(file_destination, (driveFileTimeSecs,driveFileTimeSecs))

    return file_destination if complete else None

# def add_path(part1, part2):
#     part2 = re.sub('[<>:"/\\\\|?*]|\.\.\Z', '-', part2, config=re.IGNORECASE).strip()
#     new_path = os.path.join(part1, part2)
#
#     if sys.platform.startswith('win32'):
#         if len(new_path) + new_path.count('\\') > 248 and not new_path.startswith('\\\\?\\'):
#             new_path = '\\\\?\\' + new_path
#
#     return new_path

def change_name(item_name):
    components = re.match('([^.]*)(\..*)?$', item_name)
    if not components:
        return item_name
    name = components.group(1)
    extension = components.group(2) if components.group(2) else ''
    duplicates = re.match('(.*)( \(([0-9])\))$', name)
    if duplicates:
        name = duplicates.group(1)
        duplicate_count = int(duplicates.group(3)) + 1
    else:
        duplicate_count = 1
    return f'{name} ({duplicate_count}){extension}'

def get_mimeType(google_mimeType):
    new_mimeType = MIME_TYPES.get(google_mimeType)
    if new_mimeType and config.google_doc_mimeType == 'pdf' and google_mimeType != 'application/vnd.google-apps.script':
        new_mimeType = 'application/pdf'
    return new_mimeType

def should_download(drive_file, path):
    if not path.exists():
        return True
    drive_file_time = calendar.timegm(time.strptime(drive_file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ'))
    backup_file_time = path.stat().st_mtime
    if drive_file_time > backup_file_time:
        return True
    else:
        return False

def is_abusive_file_error(content):
    try:
        data = json.loads(content.decode('utf-8'))
        return data['error']['errors'][0]['reason'] == 'cannotDownloadAbusiveFile'
    except:
        return False


def clean_backup(save_destination, prev_save_destination=None):
    if config.backup_type == 'increment' and prev_save_destination:
        clean_incremental_backup(save_destination, prev_save_destination)
    elif config.backup_type == 'update':
        clean_updated_backup(save_destination)


def clean_incremental_backup(save_destination, prev_save_destination):
    current_directory_items = prev_save_destination.iterdir()

    keep_directory = False
    for item in current_directory_items:
        # item_destination = add_path(prev_save_destination, item)
        if item.is_file():
            keep_directory = True
        else:
            # new_destination = add_path(save_destination, item)
            new_destination = save_destination / item.name
            keep_directory = clean_incremental_backup(new_destination, item) or keep_directory

    if not keep_directory:
        if save_destination.exists():
            prev_save_destination.rmdir()
        else:
            keep_directory = True

    return keep_directory

def clean_updated_backup(save_destination, drive_folder_object=None):
    logger = logging.getLogger(__name__)
    if not drive_folder_object:
        drive_folder_object = drive_file_system.get_root_folder()

    # folder_location = add_path(save_destination, drive_folder_object.name)
    folder_location = save_destination / drive_folder_object.name

    current_directory = set((item.name for item in folder_location.iterdir()))

    for file in drive_folder_object.files.values():
        if re.match('application/vnd\.google-apps\..+', file['mimeType']):
            mimeType_convert = get_mimeType(file['mimeType'])
            if not mimeType_convert:
                continue
            drive_file_name = f"{file['name']}.{FILE_EXTENSIONS.get(mimeType_convert)}"
        else:
            drive_file_name = file['name']

        # drive_file_name = add_path('',drive_file_name)

        if drive_file_name in current_directory:
            current_directory.remove(drive_file_name)

    for folder in drive_folder_object.folders.values():
        # local_folder = add_path('', folder['name'])
        local_folder = folder['name']
        if local_folder in current_directory:
            current_directory.remove(local_folder)

    for item in current_directory:
        # item_destination = add_path(folder_location, item)
        item_destination = folder_location / item
        if item_destination.is_file():
            item_destination.unlink()
            logger.info(f'{item_destination} : Removed File')
        else:
            shutil.rmtree(item_destination)
            logger.info(f'{item_destination} : Removed Folder')

    current_directory = None

    for folder in drive_folder_object.folders.values():
        child_folder_object = drive_file_system.get_folder(folder['id'])
        clean_updated_backup(folder_location, child_folder_object)


def stop_backup():
    logger = logging.getLogger(__name__)
    logger.critical('Could not complete backup. Check terminal and/or log file for more info.')
    logging.shutdown()
    progress.state = progress.State.STOP
    sys.exit(1)

def get_user():
    try:
        return service.about().get(fields="user").execute()
    except:
        logger = logging.getLogger(__name__)
        logger.critical('Error Getting User Info.', exc_info=True)
        stop_backup()

def setup_logging(log_destination):
    root_logger = logging.getLogger()
    root_logger.setLevel(config.logging_level)

    log_file = log_destination / 'drive-backup.log'
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(config.logging_level)

    name_spacing = '25'
    if config.logging_filter:
        filter = logging.Filter(name=__name__)
        file_handler.addFilter(filter)
        name_spacing = ''

    file_formatter = logging.Formatter('%(asctime)s - %(name)' + name_spacing + 's - %(levelname)8s - %(message)s')

    file_handler.setFormatter(file_formatter)

    root_logger.addHandler(file_handler)

def progress_update(msg):
    logger = logging.getLogger(__name__)
    text = Text.from_markup(msg)
    plain_text = text.plain
    logger.info(plain_text)
    console.print(text)

def run_drive_backup():
    progress.state = progress.State.INITIATE
    save_destination, recent_backup_destination = get_save_destination()

    setup_logging(save_destination)

    progress_update('[bold cyan]Getting Credentials')
    credentials = get_credentials()
    progress_update('[bold cyan]Verified Credentials')
    global service
    service = discovery.build('drive', 'v3', credentials=credentials)

    user_info = get_user()
    progress_update(f"[bold cyan]Drive Account:[/] {user_info['user']['displayName']} {user_info['user']['emailAddress']}")

    source_folder = get_source_folder()
    if not source_folder:
        stop_backup()
    progress_update(f"[bold cyan]Source Folder:[/] {source_folder['name']}")

    progress_update(f'[bold cyan]Backup Type:[/] {config.backup_type.capitalize()}')

    progress_update(f'[bold cyan]Backup files to:[/] {save_destination}')

    progress_update('[bold cyan]Preparing Backup')
    progress.state = progress.State.PREPARE
    global drive_file_system
    drive_file_system = build_dfsmap(source_folder)
    progress.total_files = drive_file_system.get_total_files()
    progress.total_folders = drive_file_system.get_total_folders()
    progress_update('[bold cyan]Starting Backup')
    progress.state = progress.State.DOWNLOAD
    get_folder(save_destination, recent_backup_destination)
    progress.state = progress.State.COMPLETE

    if config.backup_type != 'complete':
        console.print()
        progress_update('[bold cyan]Cleaning Up Backup')
        clean_backup(save_destination, recent_backup_destination)

    console.print()
    progress_update(f'[bold cyan]Backup Complete!')
    logging.shutdown()