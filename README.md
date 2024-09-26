<div align="center" markdown="1">

[![Drive Backup Logo](src/drive_backup/resources/drive-backup-icon.png)]()

# Drive Backup

### A simple way to backup your Google Drive locally.

[![PyPI - Version](https://img.shields.io/pypi/v/drive-backup)](https://pypi.org/project/drive-backup/)
[![GitHub Release](https://img.shields.io/github/v/release/dunkmann00/drive-backup?logo=github)](https://github.com/dunkmann00/Drive-Backup-Credentials/releases/latest)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/drive-backup)](https://pypi.org/project/drive-backup/)
[![Build - Workflow](https://github.com/dunkmann00/Drive-Backup/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/dunkmann00/Drive-Backup/actions/workflows/build.yml)
[![Github Pages - Workflow](https://github.com/dunkmann00/Drive-Backup/actions/workflows/github_pages.yml/badge.svg?branch=main)](https://github.com/dunkmann00/Drive-Backup/actions/workflows/github_pages.yml)
[![License](https://img.shields.io/badge/License-MIT-maroon)](LICENSE.md)

</div>

## Introduction

If you need to backup your Google Drive this is exactly the tool for you. It
will fetch the files and folders you want to backup from your Google Drive and
store them locally.

<!-- asciinema-start -->
[![Drive Backup Demo](asciinema/demo/drive-backup-demo.gif)](https://asciinema.org/a/656228)
<!-- asciinema-end -->

## Notable Features

- Supports backing up either your entire Google Drive or a specific directory.
- **Efficient**, Drive Backup will first check if a file it wants to download
  was already downloaded in a previous backup.
- Works through Google Drive API which uses OAuth 2.0 and sends all data
  securely over HTTPS.
- Supports both Mac, Windows, & Linux.
- Emits a notification when complete or when there is a problem (Mac & Windows
  only).
- Choose between 3 backup types:
  - **complete**
    - Creates a new backup, leaving previous backup untouched.
  - **increment**
    - Creates a new backup, moving files that have not changed since the
      previous backup into the new backup, and leaving only old files remaining
      in the previous backup.
  - **update**
    - Update the previous backup in-place with the latest changes from your
      Google Drive.
- Convert Google Document files (Docs, Sheets, Slides) into their corresponding
  MS Office type or to PDF.
- Supports shortcuts in your Google Drive. It will treat a shortcut like a
  separate file each time it encounters one.
- Creates a log file with every backup so you can verify all your files were
  downloaded or check for errors to get information why something went wrong or
  didn't download.
- Saves the configuration for each backup in a `bkp` file so you can easily run
  the same backup multiple times.

## Installation

Drive Backup requires Python version 3.11 or higher.

There are a few different ways to install Drive Backup. Depending on your
setup/need a different approach is recommended.

### Via `pipx`

If `pipx` is installed, it is the recommended way of installing Drive Backup.

```bash
pipx install drive-backup
```

### Via Prebuilt Binaries

The prebuilt binaries are the next easiest way to get up and running. A unique
benefit of the prebuilt binaries is the ability to place them wherever you like.
If you are storing your files on an external drive, it may be covenient to also
store the binaries there. That way, you could connect the external drive to any
computer (...that you trust of course) and be able to easily backup from it.

**Download the prebuilt binaries from the
[latest release](https://github.com/dunkmann00/Drive-Backup-Credentials/releases/latest).**

### Via `git clone`

After cloning the repo make sure to install the project with poetry
(`poetry install`). If you don't have poetry installed on your system you can
find info on how to install it on their
[docs](https://python-poetry.org/docs/#installation). From this point it is like
any other poetry project:

```bash
poetry run dbackup ...
```

## Usage

The first time Drive Backup is ran (or whenever there is no valid user signed
in), a browser window will open asking you to sign in to Google and to give
Drive Backup permission to download files from Google Drive.

> [!IMPORTANT]
> When Drive Backup requests your permission to access your Google
  Drive Files, you will see a warning screen informing you "**Google hasn’t
  verified this app**". This doesn't mean the app is actually dangerous, just
  that it is not verified. This is currently unavoidable unfortunately. For more
  info on why this is happening see the [App Verification](#app-verification)
  section below.

Below are some common examples to show how Drive Backup works. To see more info
about all of the options and commands run `dbackup -h` or `dbackup [command] -h`
.

Backup your entire Google Drive into the current directory. Drive Backup will
make a directory in your current directory titled `Google Drive Backup {date}`
where `date` is the current date.
```bash
dbackup backup
```

Backup your entire Google Drive into a specific directory titled `my-backups`:
```bash
dbackup backup -d my-backups
```

Backup only the directory on Google Drive called `Vacation Photos` into
`my-backups` and run an `update` type backup.
```bash
dbackup backup -d my-backups -t update --source "Vacation Photos"
```

If you wanted to rerun a previous backup, you can pass in the backup config file
from that backup and all the same settings will be used. By default the
`drive-backup.bkp` file from a backup is stored in the destination directory.

As an example, lets say more photos were added to our `Vacation Photos`
directory on Google Drive and we want to back them up. We don't need to use the
`-t` or `--source` options again, just `-c`.
```bash
dbackup backup -c my-backups/drive-backup.bkp
```

When downloading many files, the log can get cluttered with both Drive Backup's
logging of file info and the underlying Google library's logging of download
info. For this reason it may be desirable to only log messages from Drive
Backup and filter out the rest.
```bash
dbackup backup --log-filter
```

Similarly, you may only want to record logs of files that need to be downloaded,
not files that are already present (or in other words, not files that were
downloaded on a previous backup).
```bash
dbackup backup --log-changes
```

You can sign out of your account so you can sign into a different Google
account.
```bash
dbackup user sign-out
```

You can also check which user is currently logged in.
```bash
dbackup user info
```

### App Verification

Drive Backup needs your permission to access your Google Drive files and
folders. To do this, Drive Backup identifies itself to Google with an
application client credential. You are then shown a webpage from Google, asking
for your permission to allow Drive Backup the access it is requesting.

Due to how Google has recently decided to handle verifying client apps, it was
not possible for me to have Drive Backup verified. It would cost $500+ each year
to be verified. Unfortunately, I am not willing/in a position to pay them that
amount of money to verify a free app.

The good news here is that Drive Backup will still function as it should even
though it is not verified. However, when you are prompted to give the app
permission to access your Google Drive, you will be met with a scary window that
contains the following:

![Google Verification Warning](pages/images/google-verification-warning.png)

I can tell you that this app is not dangerous and will not do anything nefarious
with your Google Drive data or any data on your computer. It also [doesn't
collect any info from you](Privacy.md). But, since all the source code is open
source and
[availble for you to check out](https://github.com/dunkmann00/Drive-Backup),
you don't have to take my word for that.

To proceed through the permission request process and allow Drive Backup access
to Google Drive, click on **"Advanced"** and then **"Go to Drive Backup
(unsafe)"**. This will bring you to the page where you can allow Drive Backup to
have access.

I do hope none of this deters you from using Drive Backup, as it is a very
useful tool that I use myself. If you don't want to use the built in app
credential that ships with the app, you can look into
[generating your own client credential](#custom-client-credentials) and use that
instead. With this you can be even more certain Drive Backup only has the
permissions it needs (i.e. Google Drive Read access).

### Custom Client Credentials

If you are having problems with Drive Backup and are hitting download limits,
you can supply your own client credentials. To generate your own, check out the
[Authorize credentials for a desktop application](https://developers.google.com/drive/api/quickstart/python#authorize_credentials_for_a_desktop_application)
section on the Google Drive Python API Guide page. Once you have followed the
steps and downloaded the json file, pass it into Drive Backup with the
`--client-credentials` flag when you run a backup. Now Drive Backup will use
your client credentials instead of the default one that ships with the app. Note
that this will get stored in the backup config `bkp` file, so if you are
repeating a backup with `--backup-config` you don't need to explicitly pass the
custom client credential each time.

```bash
dbackup backup --client-credentials path/to/your/personal/credentials.json
```

## Privacy Policy

Check out Drive Backup's [Privacy Policy](Privacy.md).

## Copyright and License

Google Drive is a trademark of Google Inc. Use of this trademark is subject to
Google Permissions.

2024 George Waters under the MIT License. See [LICENSE](LICENSE.md) for details.
