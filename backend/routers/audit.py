from fastapi import APIRouter, Depends
import aiosqlite
import os
import json
import zlib
from backend.dependencies import get_current_user

router = APIRouter(prefix="/api/data/audit", tags=["audit"])
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

@router.get("/{artifact_id}")
async def get_audit_logs(artifact_id: str, user: str = Depends(get_current_user)):
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM AI_AUDIT_LOGS WHERE artifact_id = ? ORDER BY created_at_ts ASC",
            (artifact_id,)
        )
        rows = await cursor.fetchall()
        
        logs = []
        for row in rows:
            log_entry = dict(row)
            
            # Decompress request
            try:
                req_blob = log_entry.get('request_payload_compressed')
                if req_blob:
                    log_entry['request_payload'] = json.loads(zlib.decompress(req_blob).decode('utf-8'))
            except Exception as e:
                log_entry['request_payload'] = {"error": f"Failed to decompress request: {str(e)}"}
            finally:
                log_entry.pop('request_payload_compressed', None)
                
            # Decompress response
            try:
                res_blob = log_entry.get('response_payload_compressed')
                if res_blob:
                    log_entry['response_payload'] = json.loads(zlib.decompress(res_blob).decode('utf-8'))
            except Exception as e:
                log_entry['response_payload'] = {"error": f"Failed to decompress response: {str(e)}"}
            finally:
                log_entry.pop('response_payload_compressed', None)

            logs.append(log_entry)
        
        return logs
