# -*- coding: utf-8 -*-


from __future__ import print_function
import httplib2
import os
import io
import sys
import re
import logging
import time
import random
import calendar
from collections import deque
import dfsmap
import socket

import pdb

from apiclient import discovery
from apiclient import errors
from apiclient.http import MediaIoBaseDownload
import oauth2client
from oauth2client import client
from oauth2client import tools


try:
    import argparse
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument("--destination", help="The destination in the file system where the backup should be stored.", default='')
    parser.add_argument("--backup_name", help="The name of the backup. This will be used as the name of the folder the backup source is stored in. Default is the date.")
    parser.add_argument("--source", help="The source folder on Google Drive to backup.")
    parser.add_argument("--source_id", help="The source folder id on Google Drive to backup.", default='root')
    parser.add_argument("--google_doc_mimeType", help="The desired mimeType conversion on all compatible Google Document types.", choices=['msoffice', 'pdf'], default='msoffice')
    parser.add_argument("--logging_filter", help="When this flag is present only messages generated from Google Drive Backup will be logged, not other libraries.", action='store_true')
    parser.add_argument("--logging_changes", help="When this flag is present only log files that need to be downloaded.", action='store_true')
    flags = parser.parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive Backup'

PROGRESS_BARS = (u' ', u'▏', u'▎', u'▍', u'▌', u'▋', u'▊', u'▉', u'█')

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
    

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        logger = logging.getLogger(__name__)
        logger.info('Storing credentials to %s', credential_path)
    return credentials
    
def get_source_folder():
    logger = logging.getLogger(__name__)
    if flags.source:
        try:
            results = service.files().list(fields="files(id, name, mimeType)", q="'root' in parents and name='{0}' and trashed=false".format(flags.source)).execute()
        except:
            logger.critical(u'Error initiating backup.', exc_info=True)
            stop_backup()
        items = results.get('files', [])
    else:
        try:
            results = service.files().get(fields="id, name, mimeType", fileId=flags.source_id).execute()
        except:
            logger.critical(u'Error initiating backup.', exc_info=True)
            stop_backup()
        items = [results]
        
    if not items:
        logger.critical(u'Source folder not found.')
    elif len(items) == 1:
        if items[0]['mimeType'] == 'application/vnd.google-apps.folder':
            return items[0]
        else:
            item = items[0]
            logger.critical(u'Item found is not a folder: %s', '{0}  {1} ({2})'.format(item['name'], item['mimeType'], item['id']))
    else:
        msg = ''
        for item in items:
            if msg != '':
                msg += ', '
            msg += u'{0}  {1} ({2})'.format(item['name'], item['mimeType'], item['id'])
        logger.critical(u'Multiple items with the same name: {0}'.format(msg))
    
    return '';

def get_save_destination():
    save_destination = flags.destination if os.path.isabs(flags.destination) else os.path.abspath(flags.destination)
    if flags.backup_name:
        save_destination = add_path(save_destination, flags.backup_name)
    else:
        current_time = time.localtime()
        date_string = u'{0}-{1}-{2}'.format(current_time.tm_mon, current_time.tm_mday, current_time.tm_year)
        backup_name = u'Google Drive Backup ' + date_string
        save_destination = os.path.join(save_destination, backup_name)
    
    if not os.path.exists(save_destination):
        os.makedirs(save_destination)
    
    return save_destination


def build_dfsmap(source_folder):
    logger = logging.getLogger(__name__)
    drive_file_system = dfsmap.DriveFileSystemMap(source_folder)
    
    @request_with_backoff
    def get_list():
        return service.files().list(pageSize=1000,
                                       fields="nextPageToken, files(id, name, mimeType, modifiedTime, parents, size)",
                                       q=folder_query,
                                       pageToken=next_page_token,
                                       orderBy='folder desc').execute()
    
    
    folder_query = u"'{0}' in parents".format(source_folder['id'])
        
    next_folder_query_list = deque([[]])
    query_count = 0
    
    
    while folder_query:
        folder_query = u"({0}) and trashed=false".format(folder_query)
        next_page_token = None
        while True:
            results = get_list()
            if not results:
                logger.error(u'Could not prepare the backup succesfully. Check the log for more details.')
                results = {}
            for object in results.get('files', []):
                if object['mimeType'] == 'application/vnd.google-apps.folder':
                    if query_count >= 200:
                        query_count = 0
                        next_folder_query_list.append([])
                    drive_file_system.add_folder(object)
                    next_folder_query_list[len(next_folder_query_list)-1].append(u"'{0}' in parents".format(object['id']))
                    query_count += 1
                else:
                    drive_file_system.add_file(object)
        
            next_page_token = results.get('nextPageToken')
            if next_page_token is None:
                if len(next_folder_query_list) == 1 and len(next_folder_query_list[0]) > 0:
                    query_count = 0
                    next_folder_query_list.append([])
                folder_query = u" or ".join(next_folder_query_list.popleft())
                break
    
    
    
    return drive_file_system


def get_folder(drive_file_system, parent_dest, drive_folder_object=None, depth=0):
    global file_cnt
    global folder_cnt
    global download_errors
    logger = logging.getLogger(__name__)
    if not drive_folder_object:
        drive_folder_object = drive_file_system.get_root_folder()
    
    folder_location = add_path(parent_dest, drive_folder_object.name)
    
    if not os.path.exists(folder_location):
        try:
            os.mkdir(folder_location)
        except:
            logger.critical(u'Could not create folder: {0}'.format(folder_location), exc_info=True)
            stop_backup()
        logger.info(u'{0} : Folder Created'.format(folder_location))
    
    if depth == 0:
        download_progress_update(drive_file_system.get_total_files(), drive_file_system.get_total_folders())
        
    
    for file in drive_folder_object.files.viewvalues():
        file_location = get_file(file, folder_location)
        if file_location != None:
            if file_location != '':
                logger.info(u'{0} : created'.format(file_location))
            download_errors = 0
        else:
            download_errors += 1
            if download_errors >= 5:
                logger.critical('Multiple consecutive failed file downloads. Stopping backup, check log for more details.')
                stop_backup()
        file_cnt += 1
    
    folder_cnt += 1
    download_progress_update(drive_file_system.get_total_files(), drive_file_system.get_total_folders())
    
    for folder in drive_folder_object.folders.viewvalues():
        child_folder_object = drive_file_system.get_folder(folder['id'])
        get_folder(drive_file_system, folder_location, drive_folder_object=child_folder_object, depth=depth+1)

def get_file(drive_file, parent_folder):
    logger = logging.getLogger(__name__)
    if re.match('application/vnd\.google-apps\..+', drive_file['mimeType']):
        mimeType_convert = get_mimeType(drive_file['mimeType'])
        if not mimeType_convert:
            logger.info(u'{0}/{1} : File is not a downloadable Google Document'.format(parent_folder, drive_file['name']))
            return ''
        request = service.files().export_media(fileId=drive_file['id'],mimeType=mimeType_convert)
        drive_file_name = u'{0}.{1}'.format(drive_file['name'], FILE_EXTENSIONS.get(mimeType_convert))
    else:
        request = service.files().get_media(fileId=drive_file['id'])
        drive_file_name = drive_file['name']
    
    if not os.path.exists(parent_folder):
        logger.critical(u'Backup destination folder does not exist: {0}  Restart backup'.format(parent_folder))
        stop_backup()
    
    file_destination = add_path(parent_folder, drive_file_name)
    
    
    if not should_download(drive_file, file_destination):
        if not flags.logging_changes:
            logger.info(u'{0} : Already downloaded current version'.format(file_destination))
        return ''
    
    
    fh = io.FileIO(file_destination, mode='wb')
    if drive_file.get('size') == '0':
        fh.close()
        logger.info(u'{0} : File has no data'.format(file_destination))
        return ''
    downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)    
    
    @request_with_backoff
    def download_chunk():
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status.total_size == None:
                done = True
                logger.warning(u'{0} : File may not have been fully downloaded.'.format(file_destination))
                break
        return (status, done)
    
    complete = False
    result = download_chunk()
    fh.close()
    if result:
        status, complete = result
    else:
        logger.error(u'{0} : Was not downloaded due to an error. Check the log for more details.'.format(file_destination))
    
    if not complete:
        os.remove(file_destination)
    else:
        driveFileTime = time.strptime(drive_file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        driveFileTimeSecs = calendar.timegm(driveFileTime)
        os.utime(file_destination, (driveFileTimeSecs,driveFileTimeSecs))
    
    return file_destination if complete else None
    
def add_path(part1, part2):
    part2 = re.sub(u'[<>:"/\\\\|?*]|\.\.\Z', '-', part2, flags=re.IGNORECASE)
    new_path = os.path.join(part1, part2)
    
    if sys.platform.startswith('win32'):
        if len(new_path) + new_path.count('\\') > 260 and not new_path.startswith('\\\\?\\'):
            new_path = u'\\\\?\\' + new_path
    
    return new_path

def get_mimeType(google_mimeType):
    new_mimeType = MIME_TYPES.get(google_mimeType)
    if new_mimeType and flags.google_doc_mimeType == 'pdf' and google_mimeType != 'application/vnd.google-apps.script':
        new_mimeType = 'application/pdf'
    return new_mimeType
    
def should_download(drive_file, path):
    if not os.path.exists(path):
        return True
    drive_file_time = calendar.timegm(time.strptime(drive_file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ'))
    backup_file_time = os.path.getmtime(path)
    if drive_file_time > backup_file_time:
        return True
    else:
        return False

def stop_backup():
    logger = logging.getLogger(__name__)
    logger.critical(u'Could not complete backup. Check terminal and/or log file for more info.')
    sys.exit(1)   

def request_with_backoff(fn):
    logger = logging.getLogger(__name__)
    def custom_request(*args, **kwargs):
        num_retries = 5
        retry_num = 0
        returned_args = None
        while True:
            if retry_num > 0:
                time.sleep(random.random() + 2**(retry_num - 1))
                logger.warning(u'Retry %d with backoff', retry_num)
            try:
                returned_args = fn(*args, **kwargs)
                return returned_args
            except:
                retry_num += 1
                if retry_num > num_retries:
                    logger.exception(u'Could not complete request due to error.')
                    return None 
                     
    return custom_request
    
def get_user():
    try:
        return service.about().get(fields="user").execute()
    except:
        logger = logging.getLogger(__name__)
        logger.critical(u'Error Getting User Info.', exc_info=True)
        stop_backup()

def setup_logging(log_destination):
    root_logger = logging.getLogger()
    root_logger.setLevel(flags.logging_level)
    
    log_file = os.path.join(log_destination, 'drive-backup.log')
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(flags.logging_level)
    
    name_spacing = u'25'
    if flags.logging_filter:
        filter = logging.Filter(name=__name__)
        file_handler.addFilter(filter)
        name_spacing = ''
    
    class custom_filter():
        def filter(self, record):
            if record.levelname == 'ERROR' and record.exc_info:
                return 0
            return 1
    
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel('ERROR')
    stream_handler.addFilter(custom_filter())
    
    file_formatter = logging.Formatter(u'%(asctime)s - %(name)' + name_spacing + u's - %(levelname)8s - %(message)s')
    stream_formatter = logging.Formatter(u'\r%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    file_handler.setFormatter(file_formatter)
    stream_handler.setFormatter(stream_formatter)
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    
def progress_update(msg):
    logger = logging.getLogger(__name__)
    logger.info(msg)
    print(msg)

def download_progress_update(total_files, total_folders):
    global PROGRESS_BARS
    frac_bars_cnt = len(PROGRESS_BARS)
    total_width = 20
    total_bars = total_width * (1.0 * file_cnt / total_files)
    full_bars = int(total_bars)
    blank_bars = total_width - (full_bars+1)
    frac_bar = int((total_bars - full_bars) * frac_bars_cnt)
    frac_bar_count = 0 if blank_bars < 0 else 1
                    
    progress_bar_str = u'[{0}{1}{2}]'.format(PROGRESS_BARS[-1]*full_bars,PROGRESS_BARS[frac_bar]*frac_bar_count,PROGRESS_BARS[0]*blank_bars)
    
    try:
        sys.stdout.write(u'\rProgress: {0} Files: {1}/{2} Folders: {3}/{4}'.format(progress_bar_str, file_cnt, total_files, folder_cnt, total_folders))
        sys.stdout.flush()
    except:
        PROGRESS_BARS = (u' ', u'#')
        download_progress_update(total_files, total_folders)
    
def main():
    save_destination = get_save_destination()
    
    setup_logging(save_destination)
    
    progress_update(u'Getting Credentials')
    credentials = get_credentials()
    progress_update(u'Verified Credentials')
    http = credentials.authorize(httplib2.Http(timeout=30))
    global service
    service = discovery.build('drive', 'v3', http=http)
    
    user_info = get_user()
    progress_update(u'Drive Account: {0} {1}'.format(user_info['user']['displayName'], user_info['user']['emailAddress']))
    
    source_folder = get_source_folder()
    if not source_folder:
        stop_backup()
    progress_update(u'Source Folder: {0}'.format(source_folder['name']))    
    
    progress_update(u'Backup files to: {0}'.format(save_destination))
    
    start_time = time.time()
    
    progress_update(u'Preparing Backup')
    drive_file_system = build_dfsmap(source_folder)
    
    progress_update(u'Starting Backup')
    global file_cnt
    global folder_cnt
    global download_errors
    file_cnt = 0
    folder_cnt = 0
    download_errors = 0
    get_folder(drive_file_system, save_destination)
    
    end_time = time.time()
    duration = time.gmtime(end_time-start_time)
    if duration.tm_hour > 0:
        duration_str = time.strftime(u'%H:%M:%S', duration)
    else:
        duration_str = time.strftime(u'%M:%S', duration)
    
    print()
    progress_update(u'Backup Complete! - Duration: {0}'.format(duration_str))
    

if __name__ == '__main__':
    main()