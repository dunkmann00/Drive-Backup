from pathlib import Path

class Config:
    def __init__(self, args=None):
        if args is None:
            args = {}
        self.update_values(args)

    def update_values(self, args):
        self.destination = Path(args.get("destination", "")).absolute()
        self.backup_name = args.get("backup_name")
        self.backup_type = args.get("backup_type", "complete")
        self.prev_backup_name = args.get("prev_backup_name")
        self.source = args.get("source")
        self.source_id = args.get("source_id", "root")
        self.google_doc_mimeType = args.get("google_doc_mimeType", "msoffice")
        self.logging_level = args.get("logging_level", "INFO")
        self.logging_filter = bool(args.get("logging_filter", False))
        self.logging_changes = bool(args.get("logging_changes", False))

    def set_config(self, args):
        self.update_values(args)

config = Config()
