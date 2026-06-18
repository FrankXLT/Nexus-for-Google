import os
from google_auth_oauthlib.flow import InstalledAppFlow

def authenticate_workspace():
    shared_dir = os.environ.get("NEXUS_SHARED_DIR", ".")
    credentials_path = os.path.join(shared_dir, "credentials.json")
    token_path = os.path.join(shared_dir, "token.json")
    
    # We MUST use gmail.modify to allow 'q' queries and full email downloads
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/drive'
    ]
    
    if not os.path.exists(credentials_path):
        print(f"Error: {credentials_path} not found.")
        return
        
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=8081, host='127.0.0.1', access_type='offline', prompt='consent', open_browser=False)
    
    with open(token_path, 'w') as token_file:
        token_file.write(creds.to_json())
        
    print(f"Successfully generated token.json at {token_path}")

if __name__ == "__main__":
    authenticate_workspace()
