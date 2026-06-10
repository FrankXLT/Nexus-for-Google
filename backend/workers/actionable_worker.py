import asyncio
import aiosqlite
import time
import os
from backend.services.workspace_mutator import get_or_create_gmail_label, get_or_create_drive_folder
from backend.services.workspace import get_gmail_client, get_drive_client

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

class ActionableWorker:
    async def run(self):
        print("ActionableWorker started.")
        while True:
            try:
                # Prioritize gmail batches
                batch = await self._claim_artifacts_batch()
                if batch:
                    await self._process_batch_gmail(batch)
                    continue
                
                # Fallback to single drive processing
                artifact = await self._claim_artifact_drive()
                if artifact:
                    await self._process_artifact_drive(artifact)
                    continue

                await asyncio.sleep(1)
            except Exception as e:
                print(f"ActionableWorker error: {e}")
                await asyncio.sleep(10)

    async def _claim_artifacts_batch(self):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            current_ts = int(time.time())
            
            # Find target linkage
            cursor = await db.execute("""
                SELECT mapped_linkage_id FROM WORKSPACE_ARTIFACTS 
                WHERE state = 'ACTIONABLE' AND source_system = 'gmail' AND locked_at_ts IS NULL 
                ORDER BY priority ASC LIMIT 1
            """)
            target = await cursor.fetchone()
            
            if not target or not target['mapped_linkage_id']:
                await db.rollback()
                return []
                
            mapped_linkage_id = target['mapped_linkage_id']
            
            # Lock up to 100 rows matching that linkage
            cursor = await db.execute("""
                UPDATE WORKSPACE_ARTIFACTS
                SET locked_at_ts = ?
                WHERE id IN (
                    SELECT id FROM WORKSPACE_ARTIFACTS 
                    WHERE state = 'ACTIONABLE' AND source_system = 'gmail' AND locked_at_ts IS NULL 
                    AND mapped_linkage_id = ?
                    ORDER BY priority ASC
                    LIMIT 100
                ) RETURNING *
            """, (current_ts, mapped_linkage_id))
            
            rows = await cursor.fetchall()
            await db.commit()
            
            return [dict(row) for row in rows]

    async def _claim_artifact_drive(self):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            current_ts = int(time.time())
            cursor = await db.execute("""
                UPDATE WORKSPACE_ARTIFACTS
                SET locked_at_ts = ?
                WHERE id = (
                    SELECT id FROM WORKSPACE_ARTIFACTS 
                    WHERE state = 'ACTIONABLE' AND source_system = 'drive' AND locked_at_ts IS NULL 
                    ORDER BY priority ASC LIMIT 1
                ) RETURNING *
            """, (current_ts,))
            row = await cursor.fetchone()
            await db.commit()
            
            if row:
                return dict(row)
            return None

    def _sync_batch_modify_gmail(self, artifact_ids, label_id, important_ids, not_important_ids):
        gmail = get_gmail_client()
        
        # Batch 1: Important emails (don't remove IMPORTANT)
        if important_ids:
            body = {
                "ids": important_ids,
                "addLabelIds": [label_id] if label_id else [],
                "removeLabelIds": ["INBOX"]
            }
            gmail.users().messages().batchModify(userId='me', body=body).execute()
            
        # Batch 2: Not important emails (remove IMPORTANT)
        if not_important_ids:
            body = {
                "ids": not_important_ids,
                "addLabelIds": [label_id] if label_id else [],
                "removeLabelIds": ["INBOX", "IMPORTANT"]
            }
            gmail.users().messages().batchModify(userId='me', body=body).execute()

    def _sync_modify_drive(self, artifact_id, folder_id):
        if not folder_id:
            return
            
        drive = get_drive_client()
        # Retrieve existing parents to remove
        file_meta = drive.files().get(fileId=artifact_id, fields='parents').execute()
        previous_parents = ",".join(file_meta.get('parents', []))
        
        drive.files().update(
            fileId=artifact_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()

    async def _process_batch_gmail(self, batch):
        if not batch: return
        
        mapped_linkage_id = batch[0].get("mapped_linkage_id")
        if not mapped_linkage_id:
            for a in batch: await self._mark_error(a["id"], "Missing mapped_linkage_id")
            return

        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT t.category_id, t.entity_id, t.purpose_id, 
                       c.name as cat_name, c.gmail_sync_mode as cat_sync,
                       e.canonical_name as alias_name, e.primary_color_hex as color_hex, e.gmail_sync_mode as ent_sync,
                       p.name as purp_name
                FROM TAXONOMY_LINKAGES t
                JOIN CATEGORIES c ON t.category_id = c.id
                JOIN ENTITIES e ON t.entity_id = e.id
                JOIN PURPOSES p ON t.purpose_id = p.id
                WHERE t.linkage_id = ?
            """, (mapped_linkage_id,))
            linkage = await cursor.fetchone()

        if not linkage:
            for a in batch: await self._mark_error(a["id"], "Linkage not found")
            return

        cat_name = linkage["cat_name"]
        cat_sync = linkage["cat_sync"]
        alias_name = linkage["alias_name"]
        color_hex = linkage["color_hex"]
        ent_sync = linkage["ent_sync"]
        purp_name = linkage["purp_name"]

        sync_mode = ent_sync if ent_sync else cat_sync
        
        artifact_ids = [a["id"] for a in batch]
        important_ids = [a["id"] for a in batch if a.get("nexus_important", 0) == 1]
        not_important_ids = [a["id"] for a in batch if a.get("nexus_important", 0) == 0]

        if sync_mode != 'HIDDEN':
            try:
                label_id = await get_or_create_gmail_label(sync_mode, cat_name, alias_name, purp_name, color_hex, mapped_linkage_id)
                await asyncio.to_thread(self._sync_batch_modify_gmail, artifact_ids, label_id, important_ids, not_important_ids)
            except Exception as e:
                print(f"Actionable batch mutation failed: {e}")
                for aid in artifact_ids: await self._mark_error(aid, str(e))
                return

        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.executemany("UPDATE WORKSPACE_ARTIFACTS SET state = 'ASSIMILATING', locked_at_ts = NULL WHERE id = ?", [(aid,) for aid in artifact_ids])
            await db.commit()

    async def _process_artifact_drive(self, artifact):
        artifact_id = artifact["id"]
        mapped_linkage_id = artifact.get("mapped_linkage_id")

        if not mapped_linkage_id:
            await self._mark_error(artifact_id, "Missing mapped_linkage_id")
            return

        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT t.category_id, t.entity_id, t.purpose_id, 
                       c.name as cat_name, c.gmail_sync_mode as cat_sync,
                       e.canonical_name as alias_name, e.primary_color_hex as color_hex, e.gmail_sync_mode as ent_sync,
                       p.name as purp_name
                FROM TAXONOMY_LINKAGES t
                JOIN CATEGORIES c ON t.category_id = c.id
                JOIN ENTITIES e ON t.entity_id = e.id
                JOIN PURPOSES p ON t.purpose_id = p.id
                WHERE t.linkage_id = ?
            """, (mapped_linkage_id,))
            linkage = await cursor.fetchone()

        if not linkage:
            await self._mark_error(artifact_id, "Linkage not found")
            return

        cat_name = linkage["cat_name"]
        cat_sync = linkage["cat_sync"]
        alias_name = linkage["alias_name"]
        color_hex = linkage["color_hex"]
        ent_sync = linkage["ent_sync"]
        purp_name = linkage["purp_name"]

        sync_mode = ent_sync if ent_sync else cat_sync

        if sync_mode != 'HIDDEN':
            try:
                folder_id = await get_or_create_drive_folder(sync_mode, cat_name, alias_name, purp_name, color_hex, mapped_linkage_id)
                await asyncio.to_thread(self._sync_modify_drive, artifact_id, folder_id)
            except Exception as e:
                print(f"Actionable mutation failed for {artifact_id}: {e}")
                await self._mark_error(artifact_id, str(e))
                return

        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET state = 'ASSIMILATING', locked_at_ts = NULL WHERE id = ?", (artifact_id,))
            await db.commit()

    async def _mark_error(self, artifact_id, msg):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET state = 'ERROR', locked_at_ts = NULL WHERE id = ?", (artifact_id,))
            await db.commit()
