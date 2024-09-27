from pathlib import Path
from datetime import datetime, timezone
import json, logging, sys

DEFAULT_BACKUP_CONFIG = "drive-backup.bkp"
DEFAULT_LOG = "drive-backup.log"


class Config:
    def __init__(self, args=None):
        if args is None:
            args = {}
        self.update_values(args)

    def update_values(self, args):
        if args.get("backup_config") is True:
            self.backup_config = Path().resolve() / DEFAULT_BACKUP_CONFIG
        elif "backup_config" in args:
            self.backup_config = Path(args["backup_config"]).resolve()
            if self.backup_config.is_dir():
                self.backup_config = self.backup_config / DEFAULT_BACKUP_CONFIG
        else:
            self.backup_config = None

        if self.backup_config is not None:
            config_args = self.load_config_json(self.backup_config)
            args = config_args | args

        self.destination = Path(args.get("destination", "")).resolve()
        self.backup_name = args.get("backup_name")
        self.backup_type = args.get("backup_type", "complete")
        self.prev_backup_name = args.get("prev_backup_name")
        self.source = args.get("source")
        self.source_id = args.get("source_id", "root")
        self.google_doc_mimeType = args.get("google_doc_mimeType", "msoffice")
        self.client_credentials = Path(args["client_credentials"]).resolve() if args.get("client_credentials") else None
        self.log_level = args.get("log_level", "INFO")
        self.log_filter = bool(args.get("log_filter", False))
        self.log_changes = bool(args.get("log_changes", False))
        if args.get("log_path"):
            self.log_path = Path(args["log_path"]).resolve()
            if self.log_path.is_dir():
                self.log_path = self.log_path / DEFAULT_LOG
        else:
            self.log_path = None
        self.notifications = bool(args.get("notifications", True))
        self.backup_date = datetime.fromisoformat(args["backup_date"]) if "backup_date" in args else None

    def set_config(self, args):
        self.update_values(args)

    def store_config(self):
        path = self.backup_config or (self.destination / DEFAULT_BACKUP_CONFIG)
        self.store_config_json(self.to_dict(), path)

    def to_dict(self):
        return {
            "destination": str(self.destination),
            "backup_name": self.backup_name,
            "backup_type": self.backup_type,
            "prev_backup_name": self.prev_backup_name,
            "source": self.source,
            "source_id": self.source_id,
            "google_doc_mimeType": self.google_doc_mimeType,
            "client_credentials": str(self.client_credentials) if self.client_credentials is not None else None,
            "log_level": self.log_level,
            "log_filter": int(self.log_filter),
            "log_changes": int(self.log_changes),
            "log_path": str(self.log_path) if self.log_path is not None else None,
            "notifications": int(self.notifications),
            "backup_date": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def load_config_json(path):
        try:
            with path.open() as f:
                return json.load(f)
        except FileNotFoundError:
            logger = logging.getLogger(__name__)
            logger.critical(f"Backup configuration file '{path}' could not be found.")
            sys.exit(1)

    @staticmethod
    def store_config_json(config, path):
        with path.open("w") as f:
            json.dump(config, f)


config = Config()
