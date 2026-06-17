from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
import os
from backend.dependencies import get_current_user

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

@router.get("/linkages")
async def get_linkages(limit: int = 500, offset: int = 0, user: str = Depends(get_current_user)):
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT t.linkage_id, t.nexus_state, c.name as category_name, 
                   e.canonical_name as entity_name, p.name as purpose_name
            FROM TAXONOMY_LINKAGES t
            LEFT JOIN CATEGORIES c ON t.category_id = c.id
            LEFT JOIN ENTITIES e ON t.entity_id = e.id
            LEFT JOIN PURPOSES p ON t.purpose_id = p.id
            ORDER BY t.created_at_ts DESC LIMIT ? OFFSET ?
        """
        cursor = await db.execute(query, (limit, offset))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

@router.patch("/approve/{linkage_id}")
async def approve_linkage(linkage_id: str, user: str = Depends(get_current_user)):
    async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
        try:
            # LAYER 3 INLINE: Why PATCH /approve uses a BEGIN IMMEDIATE transaction.
            # We must use BEGIN IMMEDIATE to ensure the transition of the linkage state (to ACTIVE)
            # and the release of all parked WORKSPACE_ARTIFACTS (QUARANTINE -> ACTIONABLE) occur atomically.
            # This prevents race conditions where the ActionableWorker might pick up artifacts before the linkage is fully active.
            await db.execute("BEGIN IMMEDIATE")
            
            # 1. Update linkage to active
            await db.execute(
                "UPDATE TAXONOMY_LINKAGES SET nexus_state = 'ACTIVE' WHERE linkage_id = ?", 
                (linkage_id,)
            )
            
            # 2. Release parked artifacts for the worker
            await db.execute(
                "UPDATE WORKSPACE_ARTIFACTS SET state = 'ACTIONABLE', locked_at_ts = NULL WHERE mapped_linkage_id = ? AND state = 'QUARANTINE'", 
                (linkage_id,)
            )
            
            await db.commit()
            return {"status": "success"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

