import base64
import json
import uuid
import time
import os
import aiosqlite
from fastapi import APIRouter, Request, Response, status

router = APIRouter()

@router.post("/webhook/gmail")
async def gmail_webhook(request: Request, response: Response):
    """
    Receives push notifications from Google Cloud Pub/Sub for Gmail events.

    Layer Interactions:
    - Layer 1 (Foundation): Ingress endpoint for Google's webhook payloads.
    - Layer 3 (State Machine): Inserts the initial SUB state trigger.

    State Interactions:
    - Creates SUB state

    Args/Returns:
    - Args: FastAPI Request and Response objects
    - Returns: JSON status HTTP 202
    """
    try:
        request_body = await request.json()
    except Exception:
        response.status_code = status.HTTP_202_ACCEPTED
        return {"status": "accepted"}

    message = request_body.get("message", {})
    data_b64 = message.get("data")
    if not data_b64:
        response.status_code = status.HTTP_202_ACCEPTED
        return {"status": "accepted"}

    try:
        decoded_bytes = base64.b64decode(data_b64)
        envelope_json_str = decoded_bytes.decode('utf-8')
        # We can verify it's valid JSON
        json.loads(envelope_json_str) 
    except Exception:
        # Malformed data, ignore
        response.status_code = status.HTTP_202_ACCEPTED
        return {"status": "accepted"}

    shared_dir = os.environ.get("NEXUS_SHARED_DIR", ".")
    core_db_path = os.path.join(shared_dir, "data", "nexus_core.db")

    try:
        # Timeout 20s as requested
        async with aiosqlite.connect(core_db_path, timeout=20.0) as db:
            artifact_id = str(uuid.uuid4())
            current_ts = int(time.time())
            
            await db.execute(
                """
                INSERT INTO WORKSPACE_ARTIFACTS 
                (id, source_system, state, priority, context_hint, created_at_ts, updated_at_ts) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, "gmail", "SUB", 1, envelope_json_str, current_ts, current_ts)
            )
            await db.commit()
    except Exception as e:
        # Log it, but still return 202 to avoid Pub/Sub retry loops if the DB is truly hosed temporarily
        print(f"Webhook DB Insert Error: {e}")

    response.status_code = status.HTTP_202_ACCEPTED
    return {"status": "accepted"}
