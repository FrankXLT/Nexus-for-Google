from fastapi import APIRouter, Depends, Query
import aiosqlite
import os
import re
from backend.dependencies import get_current_user

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")
KB_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_kb.db")

@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: str = Depends(get_current_user)
):
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(f"ATTACH DATABASE '{KB_DB_PATH}' AS kb")
        
        # Replace any non-alphanumeric character with a space to prevent FTS5 syntax crashes
        clean_q = re.sub(r'[^\w\s]', ' ', q).strip()
        safe_q = " ".join([f'"{word}"' for word in clean_q.split()]) if clean_q else ""
        
        if not safe_q:
            return []
            
        query = """
            SELECT wa.id, wa.ui_summary, wa.source_sender, wa.nexus_important, wa.state, kb_ak.extracted_facts_json 
            FROM kb.ARTIFACT_KNOWLEDGE kb_ak 
            JOIN WORKSPACE_ARTIFACTS wa ON wa.id = kb_ak.artifact_id 
            WHERE kb_ak.ARTIFACT_KNOWLEDGE MATCH ? 
            ORDER BY kb_ak.rank LIMIT ? OFFSET ?
        """
        
        try:
            cursor = await db.execute(query, (safe_q, limit, offset))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"FTS5 Search Error: {e}")
            return []