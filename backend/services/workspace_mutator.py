import math
import asyncio
import aiosqlite
import os
from backend.services.workspace import get_gmail_client, get_drive_client

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

GMAIL_COLORS = [
  {"textColor": "#000000", "backgroundColor": "#43d692"},
  {"textColor": "#ffffff", "backgroundColor": "#434343"},
  {"textColor": "#000000", "backgroundColor": "#f691b2"},
  {"textColor": "#ffffff", "backgroundColor": "#fc2a1d"},
  {"textColor": "#000000", "backgroundColor": "#ffad46"},
  {"textColor": "#000000", "backgroundColor": "#ffffff"},
  {"textColor": "#000000", "backgroundColor": "#b3efd3"},
  {"textColor": "#ffffff", "backgroundColor": "#a479e2"},
  {"textColor": "#000000", "backgroundColor": "#fbd3e0"},
  {"textColor": "#ffffff", "backgroundColor": "#16a765"},
  {"textColor": "#000000", "backgroundColor": "#cccccc"},
  {"textColor": "#000000", "backgroundColor": "#a4c2f4"},
  {"textColor": "#000000", "backgroundColor": "#fc9775"},
  {"textColor": "#000000", "backgroundColor": "#ffbc6b"},
  {"textColor": "#ffffff", "backgroundColor": "#4cb04f"},
  {"textColor": "#ffffff", "backgroundColor": "#999999"},
  {"textColor": "#ffffff", "backgroundColor": "#000000"},
  {"textColor": "#ffffff", "backgroundColor": "#1a1a1a"},
  {"textColor": "#ffffff", "backgroundColor": "#cc3a21"},
  {"textColor": "#ffffff", "backgroundColor": "#ea9999"},
  {"textColor": "#ffffff", "backgroundColor": "#990000"},
  {"textColor": "#000000", "backgroundColor": "#fce8b2"},
  {"textColor": "#000000", "backgroundColor": "#f1c232"},
  {"textColor": "#ffffff", "backgroundColor": "#e69138"},
  {"textColor": "#ffffff", "backgroundColor": "#b45f06"},
  {"textColor": "#000000", "backgroundColor": "#d9d2e9"},
  {"textColor": "#000000", "backgroundColor": "#b4a7d6"},
  {"textColor": "#ffffff", "backgroundColor": "#8e7cc3"},
  {"textColor": "#ffffff", "backgroundColor": "#674ea7"},
  {"textColor": "#ffffff", "backgroundColor": "#351c75"},
  {"textColor": "#000000", "backgroundColor": "#c9daf8"},
  {"textColor": "#ffffff", "backgroundColor": "#6d9eeb"},
  {"textColor": "#ffffff", "backgroundColor": "#3c78d8"},
  {"textColor": "#ffffff", "backgroundColor": "#1155cc"},
  {"textColor": "#ffffff", "backgroundColor": "#0b5394"},
  {"textColor": "#000000", "backgroundColor": "#d0e0e3"},
  {"textColor": "#000000", "backgroundColor": "#a2c4c9"},
  {"textColor": "#ffffff", "backgroundColor": "#76a5af"},
  {"textColor": "#ffffff", "backgroundColor": "#45818e"},
  {"textColor": "#ffffff", "backgroundColor": "#134f5c"}
]

def hex_to_rgb(hex_str):
    """
    Converts a hex color string to an RGB tuple.

    Layer Interactions:
    - Layer 7 (Chromatic Engine): Processes theme colors for external sync.

    State Interactions:
    - None

    Args/Returns:
    - Args: hex_str (str)
    - Returns: Tuple (R, G, B)
    """
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (0, 0, 0)

def _get_nearest_gmail_color(hex_color):
    """
    Maps an arbitrary hex color to the nearest strictly allowed Gmail API color palette.

    Layer Interactions:
    - Layer 5 (Workspace Sync): Prepares valid metadata for Gmail labels.

    State Interactions:
    - None

    Args/Returns:
    - Args: hex_color (str)
    - Returns: Dictionary with textColor and backgroundColor
    """
    if not hex_color:
        return GMAIL_COLORS[5]
    
    target_rgb = hex_to_rgb(hex_color)
    best_match = GMAIL_COLORS[5]
    min_dist = float('inf')
    
    # LAYER 5 INLINE: The zero-dependency 3D Euclidean distance math (math.sqrt) to prevent Google API HTTP 400 color palette errors.
    # Gmail's API strictly rejects any label color that isn't exactly one of its predefined 40 palette pairs (HTTP 400).
    # To map our dynamic Chromatic Engine colors to Gmail safely, we calculate the shortest 3D distance between
    # the target RGB vector and the allowed palette's background RGB vector.
    for color_pair in GMAIL_COLORS:
        bg_rgb = hex_to_rgb(color_pair["backgroundColor"])
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target_rgb, bg_rgb)))
        if dist < min_dist:
            min_dist = dist
            best_match = color_pair
            
    return best_match

def _sync_create_gmail_label(gmail, name, color_hex):
    """
    Synchronously creates a single Gmail label node.

    Layer Interactions:
    - Layer 5 (Workspace Sync): Direct Google API mutation.

    State Interactions:
    - None

    Args/Returns:
    - Args: gmail client, name, color_hex
    - Returns: Created Label ID
    """
    # Fetch existing
    results = gmail.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    for label in labels:
        if label['name'] == name:
            return label['id']
            
    # Create new
    body = {
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }
    
    if color_hex:
        color_pair = _get_nearest_gmail_color(color_hex)
        body["color"] = color_pair
        
    try:
        created = gmail.users().labels().create(userId='me', body=body).execute()
        return created['id']
    except Exception as e:
        print(f"Failed to create Gmail label {name}: {e}")
        # It might have been created concurrently
        results = gmail.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        for label in labels:
            if label['name'] == name:
                return label['id']
        return None

async def get_or_create_gmail_label(sync_mode, cat_name, alias_name, purp_name, color_hex, linkage_id):
    """
    Orchestrates the iterative creation of nested Gmail labels based on taxonomy rules.

    Layer Interactions:
    - Layer 5 (Workspace Sync): Modifies Gmail folder structures.

    State Interactions:
    - None

    Args/Returns:
    - Args: Taxonomy metadata strings
    - Returns: The final leaf Label ID
    """
    if sync_mode == 'HIDDEN':
        return None
        
    parts = []
    if sync_mode == 'OMIT_PURPOSE':
        parts = [cat_name, alias_name]
    else: # FULL
        parts = [cat_name, alias_name, purp_name]
        
    # LAYER 5 INLINE: The iterative/recursive path splitting logic required because Google APIs do not auto-create parent folders.
    # Gmail label APIs do not automatically create parent nodes (e.g., creating "Category/Entity" fails if "Category" does not exist).
    # We must iteratively split the taxonomy path and create each node sequentially to guarantee the nested structure is built.
    gmail = get_gmail_client()
    current_path = ""
    last_label_id = None
    
    for i, part in enumerate(parts):
        if i == 0:
            current_path = part
        else:
            current_path = f"{current_path}/{part}"
            
        # Only the final node gets the color (for simplicity) or maybe all. We'll use None for parents.
        use_color = color_hex if i == len(parts) - 1 else None
        
        last_label_id = await asyncio.to_thread(_sync_create_gmail_label, gmail, current_path, use_color)

    if last_label_id:
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("""
                INSERT OR REPLACE INTO LABEL_REGISTRY (label_id, linkage_id, nexus_applied_name)
                VALUES (?, ?, ?)
            """, (last_label_id, linkage_id, current_path))
            await db.commit()
            
    return last_label_id

def _sync_create_drive_folder(drive, name, parent_id=None):
    """
    Synchronously creates a single Google Drive folder.

    Layer Interactions:
    - Layer 5 (Workspace Sync): Direct Google API mutation.

    State Interactions:
    - None

    Args/Returns:
    - Args: drive client, folder name, parent ID
    - Returns: Created Folder ID
    """
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = drive.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
        
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
        
    try:
        created = drive.files().create(body=file_metadata, fields='id').execute()
        return created['id']
    except Exception as e:
        print(f"Failed to create Drive folder {name}: {e}")
        return None

async def get_or_create_drive_folder(sync_mode, cat_name, alias_name, purp_name, color_hex, linkage_id):
    """
    Orchestrates the iterative creation of nested Drive folders based on taxonomy rules.

    Layer Interactions:
    - Layer 5 (Workspace Sync): Modifies Google Drive directory structures.

    State Interactions:
    - None

    Args/Returns:
    - Args: Taxonomy metadata strings
    - Returns: The final leaf Folder ID
    """
    if sync_mode == 'HIDDEN':
        return None
        
    parts = []
    if sync_mode == 'OMIT_PURPOSE':
        parts = [cat_name, alias_name]
    else: # FULL
        parts = [cat_name, alias_name, purp_name]
        
    drive = get_drive_client()
    last_folder_id = None
    current_path = ""
    
    for i, part in enumerate(parts):
        if i == 0:
            current_path = part
        else:
            current_path = f"{current_path}/{part}"
            
        last_folder_id = await asyncio.to_thread(_sync_create_drive_folder, drive, part, last_folder_id)

    if last_folder_id:
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("""
                INSERT OR REPLACE INTO FOLDER_REGISTRY (folder_id, linkage_id, nexus_applied_name)
                VALUES (?, ?, ?)
            """, (last_folder_id, linkage_id, current_path))
            await db.commit()
            
    return last_folder_id