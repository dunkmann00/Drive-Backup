from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_new_credentials(credential_bytes):
    flow = InstalledAppFlow.from_client_config(json.loads(credential_bytes), SCOPES)
    credentials = flow.run_local_server(port=0)
    return credentials
