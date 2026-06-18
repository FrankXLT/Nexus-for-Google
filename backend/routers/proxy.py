from fastapi import APIRouter, Depends, Query, Body
import aiosqlite
import os
import json
import asyncio
import time
import uuid
from typing import List
from pydantic import BaseModel
from backend.dependencies import get_current_user
from backend.services.workspace import get_gmail_client

router = APIRouter(prefix="/api/proxy", tags=["proxy"])
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

def _sync_gmail_search(query: str, max_results: int = 25):
    gmail = get_gmail_client()
    try:
        response = gmail.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = response.get("messages", [])
        results = []
        for msg in messages:
            try:
                msg_data = gmail.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
                headers = msg_data.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
                results.append({
                    "id": msg['id'],
                    "source_system": "gmail",
                    "source_sender": sender,
                    "ui_summary": subject,
                    "snippet": msg_data.get('snippet', ''),
                    "state": "PROXY_STAGING"
                })
            except Exception:
                continue
        return results
    except Exception as e:
        print(f"Proxy search error: {e}")
        return []

@router.get("/search")
async def search_proxy(
    q: str = Query(...), 
    source: str = Query("gmail"),
    user: str = Depends(get_current_user)
):
    if source == "gmail":
        return await asyncio.to_thread(_sync_gmail_search, q)
    return []

class EnqueueRequest(BaseModel):
    source_system: str
    ids: List[str]

@router.post("/enqueue")
async def enqueue_items(req: EnqueueRequest, user: str = Depends(get_current_user)):
    current_ts = int(time.time())
    async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
        await db.execute("BEGIN IMMEDIATE")
        for item_id in req.ids:
            env_json = json.dumps({"messageId": item_id}) if req.source_system == "gmail" else json.dumps({"fileId": item_id})
            artifact_id = str(uuid.uuid4())
            await db.execute("""
                INSERT OR IGNORE INTO WORKSPACE_ARTIFACTS 
                (id, source_system, state, priority, context_hint, created_at_ts, updated_at_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (artifact_id, req.source_system, "SUB", 2, env_json, current_ts, current_ts))
        await db.commit()
    return {"status": "success", "queued": len(req.ids)}
