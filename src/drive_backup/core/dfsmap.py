import collections

class DriveFileSystemMap(object):
    Drive_folder_object = collections.namedtuple('Drive_folder_object',['name', 'files', 'folders', 'temp'])

    def __init__(self, root_folder):
        self._file_system_map = {root_folder['id']: self.Drive_folder_object(root_folder['name'], {}, {}, False)}
        self._total_folders = -1
        self._total_files = -1
        self.root_folder_id = root_folder['id']

    def add_file(self, drive_object):
        self._total_folders = -1
        self._total_files = -1
        if 'parents' in drive_object:
            for parentID in drive_object['parents']:
                drive_folder = self._file_system_map.get(parentID)
                if not drive_folder:
                    self._file_system_map[parentID] = self._get_temp_folder_object()
                    drive_folder = self._file_system_map[parentID]
                if drive_object['id'] not in drive_folder.files:
                    drive_folder.files[drive_object['id']] = drive_object

    def add_folder(self, drive_object):
        self._total_folders = -1
        self._total_files = -1
        if 'parents' in drive_object:
            if drive_object['id'] not in self._file_system_map:
                drive_folder = self.Drive_folder_object(drive_object['name'], {}, {}, False)
                self._file_system_map[drive_object['id']] = drive_folder
                self._add_to_parents(drive_object)
            elif self._is_temporary_folder(drive_object['id']):
                permanent_folder = self._get_perm_folder_object(drive_object)
                self._file_system_map[drive_object['id']] = permanent_folder
                self._add_to_parents(drive_object)

    def _add_to_parents(self, drive_object):
        for parentID in drive_object['parents']:
            parent_folder = self._file_system_map.get(parentID)
            if not parent_folder:
                self._file_system_map[parentID] = self._get_temp_folder_object()
                parent_folder = self._file_system_map[parentID]
            if drive_object['id'] not in parent_folder.folders:
                parent_folder.folders[drive_object['id']] = drive_object

    def get_folder(self, folder_id):
        return self._file_system_map.get(folder_id)

    def set_folder_name(self, folder_id, new_name):
        folder = self._file_system_map.get(folder_id)
        new_folder = folder._replace(name=new_name)
        self._file_system_map[folder_id] = new_folder

    def get_root_folder(self):
        return self._file_system_map.get(self.root_folder_id)

    def get_total_folders(self):
        if self._total_folders == -1:
            self._update_totals()
        return self._total_folders

    def get_total_files(self):
        if self._total_files == -1:
            self._update_totals()
        return self._total_files

    def _get_temp_folder_object(self):
        return self.Drive_folder_object('TEMP', {}, {}, True)

    def _get_perm_folder_object(self, folder_object):
        temp_folder = self._file_system_map[folder_object['id']]
        return temp_folder._replace(name=folder_object['name'], temp=False)

    def _is_temporary_folder(self, folder_id):
        return self._file_system_map[folder_id].temp

    def _update_totals(self):
        self._total_folders, self._total_files = self._count_totals(self.get_root_folder())

    def _count_totals(self, drive_folder_object):
        drive_folder_cnt = 1
        drive_file_cnt = len(drive_folder_object.files)
        for folder in drive_folder_object.folders.values():
            folder_cnt, file_cnt = self._count_totals(self.get_folder(folder['id']))
            drive_folder_cnt += folder_cnt
            drive_file_cnt += file_cnt
        return (drive_folder_cnt, drive_file_cnt)
