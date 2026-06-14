import asyncio
import aiosqlite
import json
import os
import time
from backend.services.llm import call_llm
from backend.services.workspace import get_drive_client

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")
KB_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_kb.db")

class AssimilatingWorker:
    async def run(self):
        print("AssimilatingWorker started.")
        while True:
            try:
                artifact = await self._claim_artifact()
                if artifact:
                    await self._process_artifact(artifact)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"AssimilatingWorker error: {e}")
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
                    WHERE state = 'ASSIMILATING' AND locked_at_ts IS NULL 
                    ORDER BY priority ASC LIMIT 1
                ) RETURNING *
            """, (current_ts,))
            row = await cursor.fetchone()
            await db.commit()
            
            if row:
                cols = [description[0] for description in cursor.description]
                return dict(zip(cols, row))
            return None

    def _sync_patch_drive(self, artifact_id, properties, description):
        drive = get_drive_client()
        body = {
            "properties": properties,
            "description": description
        }
        drive.files().update(fileId=artifact_id, body=body).execute()

    async def _process_artifact(self, artifact):
        artifact_id = artifact["id"]
        source_system = artifact.get("source_system")
        mapped_linkage_id = artifact.get("mapped_linkage_id")

        if not mapped_linkage_id:
            await self._mark_error(artifact_id, "Missing mapped_linkage_id")
            return

        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            cursor = await db.execute("""
                SELECT p.extraction_prompt_name, e.canonical_name, a.alias_string, p.name as purp_name
                FROM TAXONOMY_LINKAGES t
                JOIN PURPOSES p ON t.purpose_id = p.id
                JOIN ENTITIES e ON t.entity_id = e.id
                LEFT JOIN ALIASES a ON a.entity_id = e.id
                WHERE t.linkage_id = ?
            """, (mapped_linkage_id,))
            linkage_row = await cursor.fetchone()

        if not linkage_row:
            await self._mark_error(artifact_id, "Linkage data missing")
            return

        prompt_name = linkage_row[0]
        canonical_name = linkage_row[1] or ""
        alias_string = linkage_row[2] or ""
        purp_name = linkage_row[3] or ""

        ui_summary = ""
        extracted_facts_json = "{}"

        # If there is a prompt, run extraction
        if prompt_name:
            extracted_headers = artifact.get("extracted_headers") or ""
            extracted_body = artifact.get("extracted_body") or ""
            
            # Using 8000 char truncation for heavy processing
            payload_text = f"Headers:\n{extracted_headers}\n\nBody:\n{extracted_body[:8000]}"
            
            try:
                # We request raw JSON from LLM (response_model=None, but config overrides in llm.py if we set response_mime_type)
                # But call_llm wrapper expects response_model for structured outputs. 
                # To do raw JSON, we can just pass prompt, and parse the raw string response.
                raw_response = await call_llm(
                    artifact_id=artifact_id,
                    prompt_name=prompt_name,
                    payload_text=payload_text
                )
                
                clean_json = raw_response.strip()
                if clean_json.startswith('```json'):
                    clean_json = clean_json[7:]
                if clean_json.startswith('```'):
                    clean_json = clean_json[3:]
                if clean_json.endswith('```'):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()
                
                try:
                    parsed_json = json.loads(clean_json)
                    ui_summary = parsed_json.get("ui_summary", "")
                    
                    # Remove ui_summary to keep only facts
                    if "ui_summary" in parsed_json:
                        del parsed_json["ui_summary"]
                        
                    # Extracted facts could be nested or the rest of the object
                    if "extracted_facts" in parsed_json:
                        extracted_facts_json = json.dumps(parsed_json["extracted_facts"])
                    else:
                        extracted_facts_json = json.dumps(parsed_json)
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON from Assimilating LLM: {clean_json}")
            except Exception as e:
                print(f"Extraction LLM failed: {e}")

        # Fallback summary if not extracted
        if not ui_summary:
            ui_summary = f"{purp_name} from {canonical_name}"

        # 3. Insert Knowledge base
        async with aiosqlite.connect(KB_DB_PATH, timeout=20.0) as kb_db:
            await kb_db.execute("""
                INSERT INTO ARTIFACT_KNOWLEDGE (artifact_id, extracted_facts_json)
                VALUES (?, ?)
            """, (artifact_id, extracted_facts_json))
            await kb_db.commit()

        # 4. Drive Metadata Sovereignty
        if source_system == 'drive':
            # LAYER 5 INLINE: The 124-byte properties vs 32,000-byte description injection in assimilating_worker.py.
            # Layer 5 dictates that strict structured taxonomy variables (canonical_name, etc.) 
            # map to Drive's 124-byte limit custom properties. Large unstructured extractions 
            # (facts, summary) map to the 32,000-byte description field.
            props = {
                "canonical_name": canonical_name[:124],
                "workspace_alias": alias_string[:124],
                "purpose": purp_name[:124]
            }
            desc = f"UI Summary: {ui_summary}\n\nFacts: {extracted_facts_json}"
            try:
                await asyncio.to_thread(self._sync_patch_drive, artifact_id, props, desc)
            except Exception as e:
                print(f"Failed to patch Drive metadata for {artifact_id}: {e}")

        # 5. Text Purge Law
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("""
                UPDATE WORKSPACE_ARTIFACTS 
                SET state = 'COMPLETED', 
                    ui_summary = ?, 
                    extracted_headers = NULL, 
                    extracted_body = NULL,
                    locked_at_ts = NULL
                WHERE id = ?
            """, (ui_summary, artifact_id))
            await db.commit()

    async def _mark_error(self, artifact_id, msg):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET state = 'ERROR', locked_at_ts = NULL WHERE id = ?", (artifact_id,))
            await db.commit()