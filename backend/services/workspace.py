import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_credentials() -> Credentials:
    """
    Loads Google OAuth 2.0 credentials from token.json.

    Layer Interactions:
    - Layer 5 (Workspace Sync): Provides authentication for Drive and Gmail APIs.

    State Interactions:
    - None

    Args/Returns:
    - Returns: google.oauth2.credentials.Credentials
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

    Layer Interactions:
    - Layer 5 (Workspace Sync): Interfaces with Gmail to apply labels.

    State Interactions:
    - None

    Args/Returns:
    - Returns: Authorized Gmail API client resource
    """
    creds = get_credentials()
    return build('gmail', 'v1', credentials=creds)

def get_drive_client():
    """
    Returns an authorized Google Drive API v3 client.

    Layer Interactions:
    - Layer 5 (Workspace Sync): Interfaces with Drive to organize folders and metadata.

    State Interactions:
    - None

    Args/Returns:
    - Returns: Authorized Google Drive API client resource
    """
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)