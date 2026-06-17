import asyncio
import time
import os
import logging
from backend.workers.base import BaseWorker
import aiosqlite

logger = logging.getLogger(__name__)

class WatchdogWorker(BaseWorker):
    """
    System maintenance loop for webhook renewals, zombie reclamation, and telemetry pruning.

    Layer Interactions:
    - Layer 1 (Foundation): Executes base system cleanups and log rotations.

    State Interactions:
    - Mutates locked_at_ts for stuck items and deletes old AI_AUDIT_LOGS.

    Args/Returns:
    - None
    """
    def __init__(self):
        super().__init__("WatchdogWorker")
        self.shared_dir = os.environ.get("NEXUS_SHARED_DIR", ".")
        self.core_db_path = os.path.join(self.shared_dir, "data", "nexus_core.db")

    async def process(self):
        """One iteration of the watchdog loop."""
        # Sleep for a bit to not thrash the CPU in the loop
        await asyncio.sleep(60)
        
        current_ts = int(time.time())
        
        async with aiosqlite.connect(self.core_db_path) as db:
            # 1. Webhook Renewals (12h logic, stubbed API call)
            # Query WEBHOOK_REGISTRY, renew channels expiring within 48h (current_ts + 48*3600)
            threshold = current_ts + (48 * 3600)
            async with db.execute("SELECT channel_id, resource_id FROM WEBHOOK_REGISTRY WHERE expiration_ts < ?", (threshold,)) as cursor:
                expiring_channels = await cursor.fetchall()
                for channel_id, resource_id in expiring_channels:
                    logger.info(f"Renewing webhook channel {channel_id} for {resource_id} (Stub)")
                    # STUB: Call Google API to renew
                    # Update registry with new expiration (e.g., current_ts + 7 days)
                    new_exp = current_ts + (7 * 24 * 3600)
                    await db.execute("UPDATE WEBHOOK_REGISTRY SET expiration_ts = ? WHERE channel_id = ?", (new_exp, channel_id))
            await db.commit()

            # 2. Zombie Reclamation (5m logic)
            # UPDATE WORKSPACE_ARTIFACTS SET locked_at_ts = NULL WHERE locked_at_ts < (current_ts - 900)
            zombie_threshold = current_ts - 900
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET locked_at_ts = NULL WHERE locked_at_ts < ?", (zombie_threshold,))
            await db.commit()

            # 3. Telemetry Pruning (Daily logic)
            # Delete from AI_AUDIT_LOGS where parent artifact is COMPLETED/IGNORED and log is older than db_audit_retention_days
            async with db.execute("SELECT config_value FROM CONFIG_SYSTEM WHERE config_key = 'db_audit_retention_days'") as cursor:
                row = await cursor.fetchone()
                retention_days = int(row[0]) if row else 30
            
            retention_threshold = current_ts - (retention_days * 24 * 3600)
            
            # Using EXISTS to match the schema
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
