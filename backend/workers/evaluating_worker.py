import asyncio
import aiosqlite
import json
import os
import time
import uuid
import re
from pydantic import BaseModel, Field
from typing import Optional
from backend.services.llm import call_llm

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

class EvaluationSchema(BaseModel):
    category_name: str
    entity_name: str
    sub_entity_name: Optional[str] = None
    purpose_name: str
    nexus_important: bool


class BrandSchema(BaseModel):
    canonical_name: str
    primary_color_hex: str = Field(default="#808080", description="Strictly a valid 7-character hex code starting with #. If unavailable, use #808080.")

class EvaluatingWorker:
    """
    Analyzes novel artifacts to map them to categories, entities, and purposes dynamically.

    Layer Interactions:
    - Layer 4 (Cognitive AI): Connects to Tier 1 LLM for deep taxonomy grounding.

    State Interactions:
    - Claims: EVALUATING -> Transitions: QUARANTINE or ERROR

    Args/Returns:
    - None
    """
    async def run(self):
        print("EvaluatingWorker started.")
        while True:
            try:
                artifact = await self._claim_artifact()
                if artifact:
                    await self._process_artifact(artifact)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"EvaluatingWorker error: {e}")
                await asyncio.sleep(10)

    async def _claim_artifact(self):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("BEGIN IMMEDIATE")
            current_ts = int(time.time())
            cursor = await db.execute("""
                UPDATE WORKSPACE_ARTIFACTS
                SET locked_at_ts = ?
                WHERE id = (
                    SELECT id FROM WORKSPACE_ARTIFACTS 
                    WHERE state = 'EVALUATING' AND locked_at_ts IS NULL 
                    ORDER BY priority ASC LIMIT 1
                ) RETURNING *
            """, (current_ts,))
            row = await cursor.fetchone()
            await db.commit()
            
            if row:
                cols = [description[0] for description in cursor.description]
                return dict(zip(cols, row))
            return None

    async def _build_taxonomy_context(self):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            cursor = await db.execute("SELECT id, name FROM CATEGORIES")
            categories = await cursor.fetchall()
            cat_map = {row[1]: row[0] for row in categories}
            
            cursor = await db.execute("SELECT id, name FROM PURPOSES")
            purposes = await cursor.fetchall()
            purp_map = {row[1]: row[0] for row in purposes}
            
            return {
                "category_names": list(cat_map.keys()),
                "purpose_names": list(purp_map.keys()),
                "cat_map": cat_map,
                "purp_map": purp_map
            }

    async def _process_artifact(self, artifact):
        artifact_id = artifact["id"]
        source_sender = artifact.get("source_sender") or "Unknown Sender"
        
        extracted_headers = artifact.get("extracted_headers") or ""
        extracted_body = artifact.get("extracted_body") or ""
        body_truncated = extracted_body[:8000] if extracted_body else ""
        
        taxonomy_ctx = await self._build_taxonomy_context()
        
        payload_text = f"Allowed Categories: {json.dumps(taxonomy_ctx['category_names'])}\n"
        payload_text += f"Allowed Purposes: {json.dumps(taxonomy_ctx['purpose_names'])}\n\n"
        
        context_hint = artifact.get("context_hint")
        if context_hint:
            payload_text += f"Context Hint: {context_hint}\n\n"
            
        payload_text += f"Source Sender: {source_sender}\n\n"
        payload_text += f"Headers:\n{extracted_headers}\n\nBody:\n{body_truncated}"
        
        try:
            eval_result = await call_llm(
                artifact_id=artifact_id,
                prompt_name="EVALUATE_NOVEL",
                payload_text=payload_text,
                response_model=EvaluationSchema
            )
        except Exception as e:
            print(f"EVALUATE_NOVEL failed: {e}")
            await self._route_error(artifact_id)
            return

        if not eval_result:
            await self._route_error(artifact_id)
            return

        # Brand Grounding
        brand_hex = "#808080" # Default
        canonical_name = eval_result.entity_name
        
        try:
            brand_result = await call_llm(
                artifact_id=artifact_id,
                prompt_name="BRAND_GROUNDING",
                payload_text=f"Entity Name: {eval_result.entity_name}",
                use_grounding=True,
                response_model=BrandSchema
            )
            if brand_result:
                canonical_name = brand_result.canonical_name
                raw_hex = brand_result.primary_color_hex
                if raw_hex and isinstance(raw_hex, str) and re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", raw_hex):
                    brand_hex = raw_hex
        except Exception as e:
            print(f"BRAND_GROUNDING failed: {e}. Using fallback.")

        await self._inject_taxonomy(artifact, eval_result, canonical_name, brand_hex, taxonomy_ctx)

    async def _inject_taxonomy(self, artifact, eval_result, canonical_name, brand_hex, taxonomy_ctx):
        artifact_id = artifact["id"]
        source_sender = artifact.get("source_sender")
        
        cat_id = taxonomy_ctx["cat_map"].get(eval_result.category_name, 8) # Fallback 8
        purp_id = taxonomy_ctx["purp_map"].get(eval_result.purpose_name, 15) # Fallback 15
        
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("BEGIN IMMEDIATE")
            
            # 1. Primary Entity
            cursor = await db.execute("SELECT id FROM ENTITIES WHERE canonical_name = ? AND category_id = ?", (canonical_name, cat_id))
            primary_entity = await cursor.fetchone()
            
            if not primary_entity:
                await db.execute("INSERT INTO ENTITIES (category_id, canonical_name, primary_color_hex) VALUES (?, ?, ?)", (cat_id, canonical_name, brand_hex))
                cursor = await db.execute("SELECT last_insert_rowid()")
                primary_entity_id = (await cursor.fetchone())[0]
            else:
                primary_entity_id = primary_entity[0]
                
            # 2. Sub-Entity Logic
            active_entity_id = primary_entity_id
            if eval_result.sub_entity_name:
                sub_canonical = f"{canonical_name} - {eval_result.sub_entity_name}"
                cursor = await db.execute("SELECT id FROM ENTITIES WHERE canonical_name = ? AND parent_entity_id = ?", (sub_canonical, primary_entity_id))
                sub_entity = await cursor.fetchone()
                if not sub_entity:
                    await db.execute("INSERT INTO ENTITIES (category_id, parent_entity_id, canonical_name, primary_color_hex) VALUES (?, ?, ?, ?)", (cat_id, primary_entity_id, sub_canonical, brand_hex))
                    cursor = await db.execute("SELECT last_insert_rowid()")
                    active_entity_id = (await cursor.fetchone())[0]
                else:
                    active_entity_id = sub_entity[0]
            
            # 3. Alias
            if source_sender:
                await db.execute("INSERT OR IGNORE INTO ALIASES (entity_id, alias_string) VALUES (?, ?)", (active_entity_id, source_sender))
                
            # 4. Taxonomy Linkage (QUARANTINE)
            linkage_id = str(uuid.uuid4())
            current_ts = int(time.time())
            
            cursor = await db.execute("SELECT linkage_id FROM TAXONOMY_LINKAGES WHERE entity_id = ? AND purpose_id = ?", (active_entity_id, purp_id))
            existing_linkage = await cursor.fetchone()
            
            if existing_linkage:
                linkage_id = existing_linkage[0]
            else:
                await db.execute("""
                    INSERT INTO TAXONOMY_LINKAGES (linkage_id, category_id, entity_id, purpose_id, nexus_state, last_active_ts)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (linkage_id, cat_id, active_entity_id, purp_id, 'QUARANTINE', current_ts))
                
            # 5. Update Artifact
            nexus_important = 1 if eval_result.nexus_important else 0
            
            await db.execute("""
                UPDATE WORKSPACE_ARTIFACTS 
                SET state = 'QUARANTINE', 
                    mapped_linkage_id = ?, 
                    nexus_important = ?, 
                    locked_at_ts = NULL 
                WHERE id = ?
            """, (linkage_id, nexus_important, artifact_id))
            
            await db.commit()

    async def _route_error(self, artifact_id):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET state = 'ERROR', locked_at_ts = NULL WHERE id = ?", (artifact_id,))
            await db.commit()