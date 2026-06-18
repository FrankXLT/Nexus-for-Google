import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_credentials() -> Credentials:
    shared_dir = os.environ.get("NEXUS_SHARED_DIR", ".")
    token_path = os.path.join(shared_dir, "token.json")
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"token.json not found at {token_path}. User must authenticate first.")
    return Credentials.from_authorized_user_file(token_path)

def get_gmail_client():
    creds = get_credentials()
    return build('gmail', 'v1', credentials=creds)

def get_drive_client():
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)
