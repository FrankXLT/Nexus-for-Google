import asyncio
import aiosqlite
import json
import os
import time
from pydantic import BaseModel, Field
from backend.services.llm import call_llm

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

class VendorSchema(BaseModel):
    vendor_name: str = Field(description="The primary vendor, merchant, sender, or entity that authored this document.")

class PurposeSelectionSchema(BaseModel):
    selected_purpose_name: str

class TriageWorker:
    async def run(self):
        print("TriageWorker started.")
        while True:
            try:
                artifact = await self._claim_artifact()
                if artifact:
                    await self._process_artifact(artifact)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"TriageWorker error: {e}")
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
                    WHERE state = 'TRIAGE' AND locked_at_ts IS NULL 
                    ORDER BY priority ASC LIMIT 1
                ) RETURNING *
            """, (current_ts,))
            row = await cursor.fetchone()
            await db.commit()
            
            if row:
                cols = [description[0] for description in cursor.description]
                return dict(zip(cols, row))
            return None

    async def _process_artifact(self, artifact):
        source_sender = artifact.get("source_sender")
        artifact_id = artifact["id"]
        
        extracted_headers = artifact.get("extracted_headers") or ""
        extracted_body = artifact.get("extracted_body") or ""
        body_truncated = extracted_body[:1000] if extracted_body else ""
        payload_text = f"{extracted_headers}\n\n{body_truncated}"
        
        # Drive Two-Stage Triage (Missing Source Sender)
        if not source_sender and artifact.get("source_system") == "drive":
            vendor_prompt = "Identify the single primary vendor, merchant, sender, or entity that authored this document. Return strictly the name."
            try:
                result = await call_llm(
                    artifact_id=artifact_id,
                    prompt_name="DRIVE_VENDOR_FALLBACK",
                    payload_text=payload_text,
                    response_model=VendorSchema,
                    custom_prompt_text=vendor_prompt,
                    custom_model_tier="gemini-2.5-flash-8b"
                )
                source_sender = result.vendor_name if result else None
                if source_sender:
                    async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
                        await db.execute("UPDATE WORKSPACE_ARTIFACTS SET source_sender = ? WHERE id = ?", (source_sender, artifact_id))
                        await db.commit()
            except Exception as e:
                print(f"Vendor extraction failed: {e}")

        if not source_sender:
            await self._route_to_evaluating(artifact_id)
            return

        # Sender Locking
        is_locked = await self._enforce_sender_lock(source_sender, artifact_id)
        if is_locked:
            return

        # Permutations
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            cursor = await db.execute("""
                SELECT e.id, a.id as alias_id
                FROM ALIASES a
                JOIN ENTITIES e ON a.entity_id = e.id
                WHERE a.alias_string = ?
            """, (source_sender,))
            alias_row = await cursor.fetchone()
            
            if not alias_row:
                await self._route_to_evaluating(artifact_id)
                return
            
            entity_id = alias_row[0]
            
            cursor = await db.execute("""
                SELECT t.linkage_id, p.name 
                FROM TAXONOMY_LINKAGES t
                JOIN PURPOSES p ON t.purpose_id = p.id
                WHERE t.entity_id = ?
            """, (entity_id,))
            linkages = await cursor.fetchall()
            
            if len(linkages) == 0:
                await self._route_to_evaluating(artifact_id)
                return
            elif len(linkages) == 1:
                mapped_linkage_id = linkages[0][0]
                await self._route_to_actionable(artifact_id, mapped_linkage_id)
            else:
                purpose_names = [l[1] for l in linkages]
                purpose_map = {l[1]: l[0] for l in linkages}
                
                prompt_text = f"Select the most appropriate intent from the following allowed list: {json.dumps(purpose_names)}"
                try:
                    result = await call_llm(
                        artifact_id=artifact_id,
                        prompt_name="TRIAGE_ROUTER",
                        payload_text=payload_text,
                        response_model=PurposeSelectionSchema,
                        custom_prompt_text=prompt_text,
                        custom_model_tier="gemini-2.5-flash-8b"
                    )
                    chosen_purpose = result.selected_purpose_name if result else None
                    
                    if chosen_purpose and chosen_purpose in purpose_map:
                        mapped_linkage_id = purpose_map[chosen_purpose]
                        await self._route_to_actionable(artifact_id, mapped_linkage_id)
                    else:
                        await self._route_to_evaluating(artifact_id)
                except Exception as e:
                    print(f"Micro-LLM triage failed: {e}")
                    await self._route_to_evaluating(artifact_id)

    async def _enforce_sender_lock(self, source_sender, artifact_id):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            cursor = await db.execute("""
                SELECT 1 FROM WORKSPACE_ARTIFACTS 
                WHERE source_sender = ? AND state IN ('EVALUATING', 'QUARANTINE') 
                LIMIT 1
            """, (source_sender,))
            row = await cursor.fetchone()
            if row:
                # Keep in TRIAGE, just release the lock
                await db.execute("UPDATE WORKSPACE_ARTIFACTS SET locked_at_ts = NULL WHERE id = ?", (artifact_id,))
                await db.commit()
                return True
        return False

    async def _route_to_evaluating(self, artifact_id):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET state = 'EVALUATING', locked_at_ts = NULL WHERE id = ?", (artifact_id,))
            await db.commit()

    async def _route_to_actionable(self, artifact_id, mapped_linkage_id):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET state = 'ACTIONABLE', mapped_linkage_id = ?, locked_at_ts = NULL WHERE id = ?", (mapped_linkage_id, artifact_id))
            await db.commit()
