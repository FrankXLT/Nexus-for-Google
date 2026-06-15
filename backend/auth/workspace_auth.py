import os
from google_auth_oauthlib.flow import InstalledAppFlow

def authenticate_workspace():
    """
    Initiates a local OAuth 2.0 flow to generate the `token.json` for backend workers.

    Layer Interactions:
    - Layer 1 (Foundation): Establishes the core API permissions.
    - Layer 5 (Workspace Sync): Grants offline access to Gmail and Drive scopes.

    State Interactions:
    - None

    Args/Returns:
    - None
    """
    shared_dir = os.environ.get("NEXUS_SHARED_DIR", ".")
    credentials_path = os.path.join(shared_dir, "credentials.json")
    token_path = os.path.join(shared_dir, "token.json")

    # The required scopes for Nexus Workspace system Auth
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.metadata',
        'https://www.googleapis.com/auth/drive.metadata',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    ]

    if not os.path.exists(credentials_path):
        print(f"Error: {credentials_path} not found.")
        print("Please place the OAuth 2.0 Client ID credentials.json file in the shared directory.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    
    # CRITICAL LAW: request access_type='offline' and prompt='consent'
    creds = flow.run_local_server(port=8081, host='127.0.0.1', access_type='offline', prompt='consent', open_browser=False)

    with open(token_path, 'w') as token_file:
        token_file.write(creds.to_json())
    
    print(f"Successfully generated token.json at {token_path}")

if __name__ == "__main__":
    authenticate_workspace()