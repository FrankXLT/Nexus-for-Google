from fastapi import APIRouter, Depends, Query
import aiosqlite
import os
import json
from typing import Optional
from backend.dependencies import get_current_user

router = APIRouter(prefix="/api/data", tags=["data"])
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

@router.get("/theme")
async def get_theme(user: str = Depends(get_current_user)):
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        cursor = await db.execute("SELECT config_value FROM CONFIG_SYSTEM WHERE config_key = 'ui_theme_support'")
        row = await cursor.fetchone()
        if row and row[0]:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                pass
        
        # Fallback theme if not configured
        return {
            "--bg-base": "#121212",
            "--bg-surface": "#1e1e1e",
            "--text-primary": "#ffffff",
            "--text-secondary": "#b3b3b3",
            "--accent-primary": "#bb86fc"
        }

@router.get("/artifacts")
async def get_artifacts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    state: Optional[str] = None,
    user: str = Depends(get_current_user)
):
    """
    Retrieves paginated workspace artifacts with joined taxonomy linkages.

    Layer Interactions:
    - Layer 6 (Frontend UI): Powers the Staging Grid with server-side pagination.

    State Interactions:
    - None

    Args/Returns:
    - Args: limit, offset, optional state filter
    - Returns: List of artifact dictionary records
    """
    query = """
        SELECT wa.id, wa.state, wa.source_system, wa.source_sender, wa.priority, 
               wa.nexus_important, wa.ui_summary, wa.created_at_ts,
               c.name as category_name, e.canonical_name as entity_name, e.primary_color_hex,
               p.name as purpose_name
        FROM WORKSPACE_ARTIFACTS wa
        LEFT JOIN TAXONOMY_LINKAGES t ON wa.mapped_linkage_id = t.linkage_id
        LEFT JOIN CATEGORIES c ON t.category_id = c.id
        LEFT JOIN ENTITIES e ON t.entity_id = e.id
        LEFT JOIN PURPOSES p ON t.purpose_id = p.id
    """
    params = []
    if state:
        query += " WHERE wa.state = ?"
        params.append(state)
    
    query += " ORDER BY wa.priority ASC, wa.created_at_ts DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, tuple(params))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
