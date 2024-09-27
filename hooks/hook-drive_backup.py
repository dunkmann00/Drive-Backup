from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.utils.hooks import collect_data_files

hiddenimports = ['drive_backup.resources', 'cryptography.fernet']

datas = copy_metadata('drive_backup')
datas += collect_data_files('drive_backup.resources', excludes=['**/__pycache__'])
