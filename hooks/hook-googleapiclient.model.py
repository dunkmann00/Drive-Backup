from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.utils.hooks import collect_data_files

# override hook-googleapiclient.model.py
datas = copy_metadata('google_api_python_client')
datas += collect_data_files('googleapiclient.discovery_cache', subdir='documents', includes=['drive.v3.json'])
