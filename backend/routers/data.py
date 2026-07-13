from fastapi import APIRouter, Depends, Query
import aiosqlite
import os
import json
import time
from typing import Optional
from backend.dependencies import get_current_user

router = APIRouter(prefix="/api/data", tags=["data"])
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")


@router.get("/theme")
async def get_theme(user: str = Depends(get_current_user)):
    """
    Returns the active UI theme CSS variable map from CONFIG_SYSTEM.

    Layer Interactions:
    - Layer 7 (Chromatic Engine): Reads generated theme from database.

    State Interactions:
    - Reads CONFIG_SYSTEM key 'ui_theme_support'.

    Args/Returns:
    - Returns: dict mapping CSS variable names to hex values.
    """
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        cursor = await db.execute("SELECT value_json FROM CONFIG_SYSTEM WHERE key = 'ui_theme_support'")
        row = await cursor.fetchone()
        if row and row[0]:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                pass
        return {
            "--bg-base": "#121215",
            "--bg-surface": "#1E1E24",
            "--text-primary": "#ffffff",
            "--text-secondary": "#b3b3b3",
            "--accent-primary": "#6A5AA9"
        }


@router.get("/artifacts")
async def get_artifacts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    state: Optional[str] = None,
    user: str = Depends(get_current_user)
):
    """
    Returns paginated WORKSPACE_ARTIFACTS joined with taxonomy data.

    Layer Interactions:
    - Layer 2 (Data Ontology): Reads nexus_core.db.
    - Layer 6 (Frontend UI): Feeds the Staging Grid and Knowledge Graph views.

    State Interactions:
    - Reads WORKSPACE_ARTIFACTS, TAXONOMY_LINKAGES, CATEGORIES, ENTITIES, PURPOSES.

    Args/Returns:
    - limit (int): Page size (max 100).
    - offset (int): Page offset.
    - state (str, optional): Filter by artifact state.
    - Returns: list of artifact dicts with joined taxonomy fields.
    """
    query = """
        SELECT wa.id, wa.state, wa.source_system, wa.source_sender, wa.priority,
               wa.nexus_important, wa.nexus_starred, wa.ui_summary, wa.created_at_ts,
               c.name as category_name, c.color_hex as category_color_hex,
               e.canonical_name as entity_name, e.primary_color_hex,
               p.name as purpose_name, p.color_hex as purpose_color_hex,
               wa.mapped_linkage_id
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
    else:
        # Default: exclude ephemeral processing states from the UI list
        query += " WHERE wa.state NOT IN ('SUB', 'RAW', 'OCR_PENDING')"

    query += " ORDER BY wa.priority ASC, wa.created_at_ts DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, tuple(params))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/heatmap")
async def get_heatmap(
    days: int = Query(90, ge=7, le=365),
    limit: int = Query(25, ge=5, le=50),
    user: str = Depends(get_current_user)
):
    """
    Returns sender x time-bucket data for the Activity Heatmap VQB panel.

    Layer Interactions:
    - Layer 6 (Frontend UI): Drives the ECharts heatmap in VQBHeatmap.jsx.

    State Interactions:
    - Reads WORKSPACE_ARTIFACTS, ENTITIES (for brand hex), TAXONOMY_LINKAGES.

    Args/Returns:
    - days (int): Number of days back for the X-axis (default: 90).
    - limit (int): Max number of senders on the Y-axis (default: 25).
    - Returns: { senders: [...], buckets: [...], data: [[x, y, value]], has_quarantine: {sender: bool} }
    """
    cutoff_ts = int(time.time()) - (days * 24 * 3600)

    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get top senders by volume within the window
        top_senders_cursor = await db.execute("""
            SELECT
                COALESCE(e.canonical_name, wa.source_sender, 'Unknown') as display_name,
                wa.source_sender,
                e.primary_color_hex as color_hex,
                COUNT(*) as total_count
            FROM WORKSPACE_ARTIFACTS wa
            LEFT JOIN TAXONOMY_LINKAGES tl ON wa.mapped_linkage_id = tl.linkage_id
            LEFT JOIN ENTITIES e ON tl.entity_id = e.id
            WHERE wa.created_at_ts > ?
              AND wa.state NOT IN ('SUB', 'RAW', 'OCR_PENDING', 'ERROR')
              AND wa.source_sender IS NOT NULL
            GROUP BY wa.source_sender
            ORDER BY total_count DESC
            LIMIT ?
        """, (cutoff_ts, limit))
        top_senders = await top_senders_cursor.fetchall()

        if not top_senders:
            return {"senders": [], "buckets": [], "data": [], "has_quarantine": {}}

        sender_list = [dict(r) for r in top_senders]
        sender_keys = [r["source_sender"] for r in sender_list]

        # Build weekly buckets over the date range
        now_ts = int(time.time())
        # Create weekly buckets
        bucket_count = min(days // 7, 52)
        bucket_seconds = (days * 24 * 3600) // bucket_count
        buckets = []
        for i in range(bucket_count):
            bucket_start = cutoff_ts + i * bucket_seconds
            buckets.append(bucket_start)

        # Fetch all artifact timestamps for top senders within the window
        placeholders = ",".join("?" * len(sender_keys))
        raw_cursor = await db.execute(f"""
            SELECT source_sender, created_at_ts
            FROM WORKSPACE_ARTIFACTS
            WHERE created_at_ts > ?
              AND source_sender IN ({placeholders})
              AND state NOT IN ('SUB', 'RAW', 'OCR_PENDING', 'ERROR')
        """, [cutoff_ts] + sender_keys)
        raw_rows = await raw_cursor.fetchall()

        # Check for quarantine items per sender
        quarantine_cursor = await db.execute(f"""
            SELECT DISTINCT source_sender
            FROM WORKSPACE_ARTIFACTS
            WHERE state = 'QUARANTINE'
              AND source_sender IN ({placeholders})
        """, sender_keys)
        quarantine_senders = {r[0] for r in await quarantine_cursor.fetchall()}

        # Build a count matrix: sender_idx × bucket_idx
        sender_idx_map = {s: i for i, s in enumerate(sender_keys)}
        matrix = [[0] * bucket_count for _ in range(len(sender_keys))]

        for row in raw_rows:
            sender = row[0]
            ts = row[1]
            s_idx = sender_idx_map.get(sender)
            if s_idx is None:
                continue
            # Find bucket index
            b_idx = min(int((ts - cutoff_ts) / bucket_seconds), bucket_count - 1)
            if 0 <= b_idx < bucket_count:
                matrix[s_idx][b_idx] += 1

        # Format for ECharts: [[x_bucket_idx, y_sender_idx, value]]
        data_points = []
        for s_idx, s_row in enumerate(matrix):
            for b_idx, val in enumerate(s_row):
                if val > 0:
                    data_points.append([b_idx, s_idx, val])

        # Format bucket labels (week strings)
        bucket_labels = []
        for b_ts in buckets:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(b_ts, tz=timezone.utc)
            bucket_labels.append(dt.strftime("%b %d"))

        return {
            "senders": [
                {
                    "display_name": s["display_name"],
                    "source_sender": s["source_sender"],
                    "color_hex": s["color_hex"] or "#6A5AA9",
                    "total_count": s["total_count"],
                    "has_quarantine": s["source_sender"] in quarantine_senders
                }
                for s in sender_list
            ],
            "buckets": bucket_labels,
            "data": data_points
        }


@router.get("/taxonomy/summary")
async def get_taxonomy_summary(user: str = Depends(get_current_user)):
    """
    Returns a hierarchical taxonomy summary for the ECharts Treemap view.

    Layer Interactions:
    - Layer 2 (Data Ontology): Reads nexus_core.db.
    - Layer 6 (Frontend UI): Feeds Treemap.jsx.

    State Interactions:
    - Reads CATEGORIES, ENTITIES, TAXONOMY_LINKAGES, WORKSPACE_ARTIFACTS.

    Args/Returns:
    - Returns: { name, children: [{ name, color_hex, value, children: [...] }] }
    """
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get categories with counts
        cat_cursor = await db.execute("""
            SELECT c.id, c.name, c.color_hex,
                   COUNT(wa.id) as artifact_count
            FROM CATEGORIES c
            LEFT JOIN TAXONOMY_LINKAGES tl ON tl.category_id = c.id
            LEFT JOIN WORKSPACE_ARTIFACTS wa ON wa.mapped_linkage_id = tl.linkage_id
                AND wa.state NOT IN ('SUB', 'RAW', 'OCR_PENDING', 'ERROR')
            GROUP BY c.id
            HAVING artifact_count > 0
            ORDER BY artifact_count DESC
        """)
        categories = await cat_cursor.fetchall()

        children = []
        for cat in categories:
            cat_id = cat["id"]
            cat_color = cat["color_hex"] or "#6A5AA9"

            # Get top entities within category
            ent_cursor = await db.execute("""
                SELECT e.canonical_name, e.primary_color_hex,
                       COUNT(wa.id) as artifact_count
                FROM ENTITIES e
                JOIN TAXONOMY_LINKAGES tl ON tl.entity_id = e.id AND tl.category_id = ?
                LEFT JOIN WORKSPACE_ARTIFACTS wa ON wa.mapped_linkage_id = tl.linkage_id
                    AND wa.state NOT IN ('SUB', 'RAW', 'OCR_PENDING', 'ERROR')
                GROUP BY e.id
                HAVING artifact_count > 0
                ORDER BY artifact_count DESC
                LIMIT 20
            """, (cat_id,))
            entities = await ent_cursor.fetchall()

            entity_children = [
                {
                    "name": e["canonical_name"],
                    "value": e["artifact_count"],
                    "color_hex": e["primary_color_hex"] or cat_color
                }
                for e in entities
            ]

            children.append({
                "name": cat["name"],
                "color_hex": cat_color,
                "value": cat["artifact_count"],
                "children": entity_children
            })

        return {"name": "Nexus", "children": children}