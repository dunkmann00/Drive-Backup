from . import console, config
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
from importlib import resources
import json, logging

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

try:
    from drive_backup_credentials.credentials import _get_new_user_credentials
except ImportError:
    _get_new_user_credentials = None

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DEFAULT_CLIENT_CREDENTIAL = "credentials.json"
CREDENTIAL_FILE = 'drive-backup-user-cred.json'

def get_user_credentials_path():
    credential_dir = Path("~/.credentials").expanduser()
    if not credential_dir.exists():
        credential_dir.mkdir()
    credential_path = credential_dir / CREDENTIAL_FILE
    return credential_path

def get_user_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    logger = logging.getLogger(__name__)
    user_credential_path = get_user_credentials_path()

    user_credentials = None
    if user_credential_path.exists():
        try:
            user_credentials = Credentials.from_authorized_user_file(str(user_credential_path), SCOPES)
        except (json.JSONDecodeError, ValueError):
            logger.info("User credentials are invalid.")
    if not user_credentials or not user_credentials.valid:
        if user_credentials and user_credentials.expired and user_credentials.refresh_token:
            try:
                user_credentials.refresh(Request())
            except RefreshError:
                logger.info("Credential refresh failed.")
        if not user_credentials or user_credentials and user_credentials.expired:
            client_credentials_path = config.client_credentials or (resources.files("src.resources") / DEFAULT_CLIENT_CREDENTIAL)
            try:
                client_credentials = client_credentials_path.read_bytes()
            except FileNotFoundError:
                logger.critical(f"Client credential file '{client_credentials_path}' could not be found.")
                client_credentials = None
            if client_credentials is not None:
                try:
                    user_credentials = get_new_user_credentials(client_credentials)
                except (json.JSONDecodeError, ValueError):
                    logger.critical("Client credential corrupted, unable to parse.")
                except KeyboardInterrupt:
                    logger.info("Keyboard Interrupt detected, cancelling...")
        if user_credentials:
            logger.info(f'Storing user credentials to {user_credential_path}', )
            with user_credential_path.open("w") as token:
                token.write(user_credentials.to_json())
        else:
            logger.critical('Could not get user credentials.')
    return user_credentials

def remove_user_credentials():
    console.print("[cyan]Removing user credentials...", end="")
    credential_path = get_user_credentials_path()
    credential_path.unlink(missing_ok=True)
    console.print("[cyan]done")

def get_new_user_credentials(credential_bytes):
    if _get_new_user_credentials is not None:
        return _get_new_user_credentials(credential_bytes)
    flow = InstalledAppFlow.from_client_config(json.loads(credential_bytes), SCOPES)
    credentials = flow.run_local_server(port=0)
    return credentials
