from . import console, config
from google_auth_oauthlib.flow import InstalledAppFlow, _RedirectWSGIApp
from pathlib import Path
from importlib import resources
import json, logging, wsgiref

from googleapiclient import discovery

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
AUTH_SUCCESS_FILE = 'authentication_success.html'

def get_user_credentials_path():
    credential_dir = Path("~/.credentials").expanduser()
    if not credential_dir.exists():
        credential_dir.mkdir()
    credential_path = credential_dir / CREDENTIAL_FILE
    return credential_path

def get_new_user_credentials(credential_bytes):
    success_file_path = resources.files("drive_backup.resources") / AUTH_SUCCESS_FILE
    success_message = success_file_path.read_text()
    if _get_new_user_credentials is not None:
        return _get_new_user_credentials(credential_bytes, success_message)
    flow = InstalledAppFlow.from_client_config(json.loads(credential_bytes), SCOPES)
    credentials = flow.run_local_server(port=0, success_message=success_message)
    return credentials

def get_user_credentials(new_credential_okay=True):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials if
    'new_credential_okay' is True.

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
    if new_credential_okay and (not user_credentials or not user_credentials.valid):
        if user_credentials and user_credentials.expired and user_credentials.refresh_token:
            try:
                user_credentials.refresh(Request())
            except RefreshError:
                logger.info("Credential refresh failed.")
        if not user_credentials or user_credentials and user_credentials.expired:
            client_credentials_path = config.client_credentials or (resources.files("drive_backup.resources") / DEFAULT_CLIENT_CREDENTIAL)
            logger.info(f"Using client credential file at {client_credentials_path}")
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

def get_user_info(user_credentials):
    service = discovery.build('drive', 'v3', credentials=user_credentials)
    user_info = service.about().get(fields="user").execute()
    return user_info

def sign_out_user():
    console.print("[cyan bold]Sign-out of Google Drive")
    console.print("[green]Removing user credentials...", end="")
    credential_path = get_user_credentials_path()
    credential_path.unlink(missing_ok=True)
    console.print("[green]done")

def sign_in_user(client_credentials=None):
    console.print("[cyan bold]Sign-in to Google Drive")
    if client_credentials is not None:
        config.client_credentials = Path(client_credentials).resolve()
    console.print("[green]Attempting to get user credentials...")
    user_credentials = get_user_credentials()
    if not user_credentials:
        console.print("[red]Unable to acquire user credentials")
        return
    user_info = get_user_info(user_credentials)
    console.print("[green]Sign-in successful")
    console.print(f"[bold cyan]Drive Account:[/] {user_info['user']['displayName']} {user_info['user']['emailAddress']}")

def view_user_info():
    console.print("[cyan bold]View User Info")
    user_credentials = get_user_credentials(new_credential_okay=False)
    if not user_credentials:
        console.print("No user signed in.")
        return
    user_info = get_user_info(user_credentials)
    console.print(f"[bold cyan]Drive Account:[/] {user_info['user']['displayName']} {user_info['user']['emailAddress']}")

def wsgiapp_call(self, environ, start_response):
    start_response("200 OK", [("Content-type", "text/html; charset=utf-8")])
    self.last_request_uri = wsgiref.util.request_uri(environ)
    return [self._success_message.encode("utf-8")]

_RedirectWSGIApp.__call__ = wsgiapp_call
