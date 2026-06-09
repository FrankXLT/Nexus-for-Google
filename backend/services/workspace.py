import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_credentials() -> Credentials:
    """
    Loads Google OAuth 2.0 credentials from token.json.
    """
    shared_dir = os.environ.get("NEXUS_SHARED_DIR", ".")
    token_path = os.path.join(shared_dir, "token.json")
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"token.json not found at {token_path}. User must authenticate first.")
    
    return Credentials.from_authorized_user_file(token_path, [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/drive"
    ])

def get_gmail_client():
    """
    Returns an authorized Gmail API v1 client.
    """
    creds = get_credentials()
    return build('gmail', 'v1', credentials=creds)

def get_drive_client():
    """
    Returns an authorized Google Drive API v3 client.
    """
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)
