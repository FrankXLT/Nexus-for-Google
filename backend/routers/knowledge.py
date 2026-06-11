from fastapi import APIRouter, Depends, Query
import aiosqlite
import os
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
    """
    Executes a Full-Text Search across the structured Knowledge Graph.

    Layer Interactions:
    - Layer 2 (Data Ontology): Joins `nexus_core.db` routing data with `nexus_kb.db` FTS5 indices.

    State Interactions:
    - None

    Args/Returns:
    - Args: Search query `q`, pagination `limit` and `offset`
    - Returns: Ranked list of matching artifacts
    """
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # LAYER 2 INLINE: Use of ATTACH DATABASE for cross-database JOINs and ORDER BY kb_ak.rank.
        # We physically separate the routing DB (core) from the heavy RAG DB (kb) to prevent SQLite WAL contention.
        # By using ATTACH DATABASE, we can perform cross-db JOINs natively in SQLite's C engine, preserving Python 
        # event-loop performance. We ORDER BY kb_ak.rank to ensure FTS5 tf-idf relevance scoring dictates the UI order.
        await db.execute(f"ATTACH DATABASE '{KB_DB_PATH}' AS kb")
        
        query = """
            SELECT wa.id, wa.ui_summary, wa.source_sender, wa.nexus_important, wa.state, kb_ak.extracted_facts_json 
            FROM kb.ARTIFACT_KNOWLEDGE kb_ak 
            JOIN WORKSPACE_ARTIFACTS wa ON wa.id = kb_ak.artifact_id 
            WHERE kb_ak.ARTIFACT_KNOWLEDGE MATCH ? 
            ORDER BY kb_ak.rank LIMIT ? OFFSET ?
        """
        
        cursor = await db.execute(query, (q, limit, offset))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
