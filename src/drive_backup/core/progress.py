from enum import Enum

class Progress:
    class State(Enum):
        READY       = 0
        INITIATE    = 1
        PREPARE     = 2
        DOWNLOAD    = 3
        PAUSE       = 4
        COMPLETE    = 5
        STOP        = 6

    def __init__(self):
        self.total_files = 0
        self.total_folders = 0
        self.file_cnt = 0
        self.folder_cnt = 0
        self.state = self.State.READY
        self._subs = []
        self._inited = True

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if not name.startswith("_") and getattr(self, "_inited", False):
            for sub in self._subs:
                sub(self)

    def subscribe(self, callback):
        self._subs.append(callback)

progress = Progress()
