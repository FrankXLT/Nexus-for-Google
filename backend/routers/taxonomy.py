from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
import os
from backend.dependencies import get_current_user

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")


@router.get("/tree")
async def get_taxonomy_tree(user: str = Depends(get_current_user)):
    """
    Returns all Categories with their child Entities and per-entity linkage state counts.
    Used by TaxonomyConsole's Tree panel to browse the default taxonomy structure.

    Layer Interactions:
    - Layer 2 (Data Ontology): Reads CATEGORIES, ENTITIES, TAXONOMY_LINKAGES.
    - Layer 6 (Frontend UI): Feeds TaxonomyConsole Tree panel.

    State Interactions:
    - Reads CATEGORIES, ENTITIES, TAXONOMY_LINKAGES.

    Args/Returns:
    - Returns: { categories: [{ id, name, color_hex, description, gmail_sync_mode,
                                entity_count, entities: [{ id, canonical_name,
                                workspace_alias, primary_color_hex,
                                active_linkage_count, quarantine_linkage_count }] }] }
    """
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Fetch all categories
        cat_cursor = await db.execute("""
            SELECT id, name, color_hex, description, gmail_sync_mode, top_entities_limit
            FROM CATEGORIES ORDER BY id ASC
        """)
        categories = await cat_cursor.fetchall()

        result = []
        for cat in categories:
            cat_id = cat["id"]

            # Fetch entities in this category
            ent_cursor = await db.execute("""
                SELECT e.id, e.canonical_name, e.workspace_alias, e.primary_color_hex,
                       COUNT(CASE WHEN tl.nexus_state = 'ACTIVE' THEN 1 END) as active_linkage_count,
                       COUNT(CASE WHEN tl.nexus_state = 'QUARANTINE' THEN 1 END) as quarantine_linkage_count
                FROM ENTITIES e
                LEFT JOIN TAXONOMY_LINKAGES tl ON tl.entity_id = e.id
                WHERE e.category_id = ?
                GROUP BY e.id
                ORDER BY (active_linkage_count + quarantine_linkage_count) DESC, e.canonical_name ASC
            """, (cat_id,))
            entities = await ent_cursor.fetchall()

            result.append({
                "id": cat["id"],
                "name": cat["name"],
                "color_hex": cat["color_hex"],
                "description": cat["description"],
                "gmail_sync_mode": cat["gmail_sync_mode"],
                "top_entities_limit": cat["top_entities_limit"],
                "entity_count": len(entities),
                "entities": [
                    {
                        "id": e["id"],
                        "canonical_name": e["canonical_name"],
                        "workspace_alias": e["workspace_alias"],
                        "primary_color_hex": e["primary_color_hex"],
                        "active_linkage_count": e["active_linkage_count"],
                        "quarantine_linkage_count": e["quarantine_linkage_count"],
                    }
                    for e in entities
                ]
            })

        return {"categories": result}


@router.get("/linkages")

async def get_linkages(limit: int = 500, offset: int = 0, user: str = Depends(get_current_user)):
    """
    Returns all taxonomy linkages with joined category, entity, and purpose data.

    Layer Interactions:
    - Layer 2 (Data Ontology): Reads nexus_core.db.
    - Layer 6 (Frontend UI): Feeds the TaxonomyConsole Matrix view.

    State Interactions:
    - Reads TAXONOMY_LINKAGES, CATEGORIES, ENTITIES, PURPOSES.

    Args/Returns:
    - limit (int): Page size.
    - offset (int): Page offset.
    - Returns: list of linkage dicts.
    """
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT t.linkage_id, t.nexus_state,
                   c.name as category_name, c.color_hex as category_color_hex,
                   e.canonical_name as entity_name, e.primary_color_hex as entity_color_hex,
                   p.name as purpose_name, p.color_hex as purpose_color_hex,
                   t.last_active_ts
            FROM TAXONOMY_LINKAGES t
            LEFT JOIN CATEGORIES c ON t.category_id = c.id
            LEFT JOIN ENTITIES e ON t.entity_id = e.id
            LEFT JOIN PURPOSES p ON t.purpose_id = p.id
            ORDER BY t.last_active_ts DESC LIMIT ? OFFSET ?
        """
        cursor = await db.execute(query, (limit, offset))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/vqb")
async def get_vqb_sankey(user: str = Depends(get_current_user)):
    """
    Returns Sankey-ready nodes and links built directly from TAXONOMY_LINKAGES.
    This endpoint is used by VQBSankey.jsx to render the taxonomy flow visualization.
    Nodes are colored using CATEGORIES.color_hex and ENTITIES.primary_color_hex.

    Layer Interactions:
    - Layer 2 (Data Ontology): Reads nexus_core.db.
    - Layer 6 (Frontend UI): Feeds VQBSankey.jsx.

    State Interactions:
    - Reads TAXONOMY_LINKAGES, CATEGORIES, ENTITIES, PURPOSES, WORKSPACE_ARTIFACTS.

    Args/Returns:
    - Returns: { nodes: [{name, itemStyle: {color}}], links: [{source, target, value}] }
    """
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get active linkages with artifact counts
        cursor = await db.execute("""
            SELECT
                c.name as category_name, c.color_hex as category_color,
                e.canonical_name as entity_name, e.primary_color_hex as entity_color,
                p.name as purpose_name, p.color_hex as purpose_color,
                COUNT(wa.id) as artifact_count
            FROM TAXONOMY_LINKAGES tl
            JOIN CATEGORIES c ON tl.category_id = c.id
            JOIN ENTITIES e ON tl.entity_id = e.id
            JOIN PURPOSES p ON tl.purpose_id = p.id
            LEFT JOIN WORKSPACE_ARTIFACTS wa ON wa.mapped_linkage_id = tl.linkage_id
                AND wa.state NOT IN ('SUB', 'RAW', 'OCR_PENDING', 'ERROR')
            WHERE tl.nexus_state = 'ACTIVE'
            GROUP BY tl.linkage_id
            ORDER BY artifact_count DESC
            LIMIT 100
        """)
        rows = await cursor.fetchall()

        nodes_map = {}
        links_map = {}

        for row in rows:
            cat = row["category_name"]
            ent = row["entity_name"]
            purp = row["purpose_name"]
            count = max(row["artifact_count"], 1)

            # Register nodes with colors
            if cat not in nodes_map:
                nodes_map[cat] = {"name": cat, "itemStyle": {"color": row["category_color"] or "#6A5AA9"}}
            if ent not in nodes_map:
                nodes_map[ent] = {"name": ent, "itemStyle": {"color": row["entity_color"] or "#888888"}}
            if purp not in nodes_map:
                nodes_map[purp] = {"name": purp, "itemStyle": {"color": row["purpose_color"] or "#507B7A"}}

            # Aggregate link weights
            link1_key = f"{cat}||{ent}"
            links_map[link1_key] = links_map.get(link1_key, 0) + count

            link2_key = f"{ent}||{purp}"
            links_map[link2_key] = links_map.get(link2_key, 0) + count

        nodes = list(nodes_map.values())
        links = [
            {"source": k.split("||")[0], "target": k.split("||")[1], "value": v}
            for k, v in links_map.items()
        ]

        return {"nodes": nodes, "links": links}


@router.patch("/approve/{linkage_id}")
async def approve_linkage(linkage_id: str, user: str = Depends(get_current_user)):
    """
    Atomically transitions a QUARANTINE linkage to ACTIVE and releases all parked artifacts.

    Layer Interactions:
    - Layer 3 (State Machine): QUARANTINE -> ACTIONABLE state transition.

    State Interactions:
    - Updates TAXONOMY_LINKAGES.nexus_state to 'ACTIVE'.
    - Updates WORKSPACE_ARTIFACTS.state from 'QUARANTINE' to 'ACTIONABLE' for matching artifacts.

    Args/Returns:
    - linkage_id (str): The linkage_id to approve.
    - Returns: { status: 'success' }
    """
    async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
        try:
            # LAYER 3 INLINE: Why PATCH /approve uses a BEGIN IMMEDIATE transaction.
            # We must use BEGIN IMMEDIATE to ensure the transition of the linkage state (to ACTIVE)
            # and the release of all parked WORKSPACE_ARTIFACTS (QUARANTINE -> ACTIONABLE) occur atomically.
            # This prevents race conditions where the ActionableWorker might pick up artifacts before the linkage is fully active.
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                "UPDATE TAXONOMY_LINKAGES SET nexus_state = 'ACTIVE' WHERE linkage_id = ?",
                (linkage_id,)
            )
            await db.execute(
                "UPDATE WORKSPACE_ARTIFACTS SET state = 'ACTIONABLE', locked_at_ts = NULL WHERE mapped_linkage_id = ? AND state = 'QUARANTINE'",
                (linkage_id,)
            )
            await db.commit()
            return {"status": "success"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
