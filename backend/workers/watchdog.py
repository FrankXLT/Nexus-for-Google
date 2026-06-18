import asyncio
import time
import os
import logging
from backend.workers.base import BaseWorker
import aiosqlite

logger = logging.getLogger(__name__)

class WatchdogWorker(BaseWorker):
    def __init__(self):
        super().__init__("WatchdogWorker")
        self.shared_dir = os.environ.get("NEXUS_SHARED_DIR", ".")
        self.core_db_path = os.path.join(self.shared_dir, "data", "nexus_core.db")

    async def process(self):
        await asyncio.sleep(60)
        current_ts = int(time.time())
        async with aiosqlite.connect(self.core_db_path) as db:
            threshold = current_ts + (48 * 3600)
            async with db.execute("SELECT channel_id, resource_id FROM WEBHOOK_REGISTRY WHERE expiration_ts < ?", (threshold,)) as cursor:
                expiring_channels = await cursor.fetchall()
                for channel_id, resource_id in expiring_channels:
                    logger.info(f"Renewing webhook channel {channel_id} for {resource_id} (Stub)")
                    new_exp = current_ts + (7 * 24 * 3600)
                    await db.execute("UPDATE WEBHOOK_REGISTRY SET expiration_ts = ? WHERE channel_id = ?", (new_exp, channel_id))
            await db.commit()

            zombie_threshold = current_ts - 900
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET locked_at_ts = NULL WHERE locked_at_ts < ?", (zombie_threshold,))
            await db.commit()

            async with db.execute("SELECT value_json FROM CONFIG_SYSTEM WHERE key = 'db_audit_retention_days'") as cursor:
                row = await cursor.fetchone()
                retention_days = int(row[0]) if row else 30
            
            retention_threshold = current_ts - (retention_days * 24 * 3600)
            prune_query = """
                DELETE FROM AI_AUDIT_LOGS 
                WHERE created_at_ts < ? 
                AND EXISTS (
                    SELECT 1 FROM WORKSPACE_ARTIFACTS 
                    WHERE WORKSPACE_ARTIFACTS.id = AI_AUDIT_LOGS.artifact_id 
                    AND WORKSPACE_ARTIFACTS.state IN ('COMPLETED', 'IGNORED')
                )
            """
            await db.execute(prune_query, (retention_threshold,))
            await db.commit()
