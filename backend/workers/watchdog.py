import asyncio
import time
import os
import logging
from backend.workers.base import BaseWorker
import aiosqlite

logger = logging.getLogger(__name__)

class WatchdogWorker(BaseWorker):
    """
    Watchdog engine running three independent health loops at different cadences.

    Layer Interactions:
    - Layer 3 (State Machine): Zombie reclamation (every 5m), webhook renewal (every 12h), audit pruning (daily).

    State Interactions:
    - Reads/writes WORKSPACE_ARTIFACTS.locked_at_ts (zombie recovery).
    - Reads/writes WEBHOOK_REGISTRY.expiration_ts (renewal).
    - Deletes AI_AUDIT_LOGS (retention pruning).
    """
    def __init__(self):
        super().__init__("WatchdogWorker")
        self.shared_dir = os.environ.get("NEXUS_SHARED_DIR", ".")
        self.core_db_path = os.path.join(self.shared_dir, "data", "nexus_core.db")
        self._last_renewal_ts = 0
        self._last_prune_ts = 0

    async def process(self):
        """
        Runs three health checks at appropriate intervals:
        - Zombie reclamation: every 5 minutes (every loop iteration with 300s sleep)
        - Webhook renewal: every 12 hours
        - Audit pruning: every 24 hours

        Args/Returns:
        - None
        """
        await asyncio.sleep(300)  # 5-minute cadence for zombie check
        current_ts = int(time.time())

        await self._reclaim_zombies(current_ts)

        if current_ts - self._last_renewal_ts > (12 * 3600):
            await self._renew_webhooks(current_ts)
            self._last_renewal_ts = current_ts

        if current_ts - self._last_prune_ts > (24 * 3600):
            await self._prune_audit_logs(current_ts)
            self._last_prune_ts = current_ts

    async def _reclaim_zombies(self, current_ts: int):
        """
        Unlocks artifacts locked for more than 15 minutes (zombie reclamation).
        Per the Anti-Duplication Law: ONLY drops the lock, never reverts state.

        Args/Returns:
        - current_ts (int): Current epoch timestamp.
        """
        zombie_threshold = current_ts - 900  # 15 minutes
        async with aiosqlite.connect(self.core_db_path) as db:
            result = await db.execute(
                "UPDATE WORKSPACE_ARTIFACTS SET locked_at_ts = NULL WHERE locked_at_ts < ?",
                (zombie_threshold,)
            )
            await db.commit()
            if result.rowcount > 0:
                logger.info(f"WatchdogWorker: Reclaimed {result.rowcount} zombie artifact(s).")

    async def _renew_webhooks(self, current_ts: int):
        """
        Renews webhook channels expiring within the next 48 hours.
        Updates the expiration timestamp; actual GCP API call is a stub pending
        the real GCP Drive Watch API implementation.

        Args/Returns:
        - current_ts (int): Current epoch timestamp.
        """
        renewal_window = current_ts + (48 * 3600)
        async with aiosqlite.connect(self.core_db_path) as db:
            async with db.execute(
                "SELECT channel_id, resource_id FROM WEBHOOK_REGISTRY WHERE expiration_ts < ?",
                (renewal_window,)
            ) as cursor:
                expiring_channels = await cursor.fetchall()

            for channel_id, resource_id in expiring_channels:
                logger.info(f"WatchdogWorker: Renewing webhook channel {channel_id} for resource {resource_id} (stub).")
                new_exp = current_ts + (7 * 24 * 3600)
                await db.execute(
                    "UPDATE WEBHOOK_REGISTRY SET expiration_ts = ? WHERE channel_id = ?",
                    (new_exp, channel_id)
                )
            await db.commit()

    async def _prune_audit_logs(self, current_ts: int):
        """
        Prunes AI_AUDIT_LOGS for COMPLETED/IGNORED artifacts beyond retention threshold.
        Per the Quarantine Law: never deletes logs for QUARANTINE or ERROR artifacts.
        If db_audit_retention_days is 0, deletion is skipped entirely.

        Args/Returns:
        - current_ts (int): Current epoch timestamp.
        """
        async with aiosqlite.connect(self.core_db_path) as db:
            async with db.execute(
                "SELECT value_json FROM CONFIG_SYSTEM WHERE key = 'db_audit_retention_days'"
            ) as cursor:
                row = await cursor.fetchone()
                retention_days = int(row[0]) if row else 90

            if retention_days == 0:
                logger.info("WatchdogWorker: Audit pruning skipped (retention = 0).")
                return

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
            result = await db.execute(prune_query, (retention_threshold,))
            await db.commit()
            if result.rowcount > 0:
                logger.info(f"WatchdogWorker: Pruned {result.rowcount} audit log(s).")
