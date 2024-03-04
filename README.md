# Drive Backup

If you need to backup your Google Drive this is exactly the tool for you. This script will fetch the files and folders in your drive that you want to backup and store them anywhere you'd like.

## Features

- Supports backing up either your entire Google Drive or a single folder.
- **FAST**, Drive Backup will first check if a file it wants to download was already downloaded in a previous backup.
- Works through Google Drive API which uses OAuth 2.0 and sends all data securely over HTTPS.
- Supports both Mac & Windows.
- Choose between 3 backup types:
  - complete
    - Creates a new backup, leaving previous backup untouched.
  - increment
    - Creates a new backup, moving files that have not changed since the previous backup into the new backup, and leaving only old files remaining in the previous backup.
  - update
    - Update the previous backup to have the current files and folders from your Google Drive.
- Convert Google Document files (Docs, Sheets, Slides) into their corresponding MS Office type or to PDF.
- Creates a log file with every backup so you can verify all your files were downloaded or check for errors to get information why something went wrong or didn't download.

## Before you get started

In order to use Drive Backup you'll need to install the Google Drive Python Client library and add a `client_secret.json` file to the same directory as Drive Backup. But fear not! This is very simple and only takes a minute. Check out the [Python Quickstart](https://developers.google.com/drive/v3/web/quickstart/python) page on Google and follow steps #1 and #2. Once that's complete you're ready to rock-n-roll.

## Example Backup

1. Open the terminal (command prompt on Windows) and navigate to the directory where `drivebackup.py` and `dfsmap.py` are located.
1. We'll assume this is the first backup we are doing so we'll do a complete backup on our entire Google Drive.
```
$ python drivebackup.py --logging_level INFO --logging_filter --destination "My Google Drive Backup" --backup_type complete
```
 - If this is the first time you are running Drive Backup it will open a browser window and ask you to give Drive Backup permission to access your Google Drive.
 - It is also worth noting that even though this was the first time running a backup we didn't have to do `--backup_type complete`. We could have done an incremental backup or updated backup and Drive Backup would run as expected.


 In our example, we also set `--logging_filter`. This blocks other libraries from logging messages to the log file. This can be useful when you want to see all the files that Drive Backup processed, but don't want to see all of the requests the Google Drive API made when downloading the files. There are a few other preferences you can set when running your backup. Type `python drivebackup.py -h` to view all the available options!

## Copyright and License

Google Drive is a trademark of Google Inc. Use of this trademark is subject to Google Permissions.

2024 George Waters under the MIT License
