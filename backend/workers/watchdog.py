import asyncio
import time
import os
import logging
from backend.workers.base import BaseWorker
import aiosqlite

logger = logging.getLogger(__name__)


class WatchdogWorker(BaseWorker):
    """
    Watchdog engine running four independent health loops at different cadences.

    Layer Interactions:
    - Layer 3 (State Machine): Zombie reclamation (every 5m), Gmail sweeper (every 10m),
      webhook renewal (every 12h), audit pruning (daily).

    State Interactions:
    - Reads/writes WORKSPACE_ARTIFACTS.locked_at_ts (zombie recovery).
    - Reads/writes WEBHOOK_REGISTRY.expiration_ts (renewal).
    - Inserts WORKSPACE_ARTIFACTS with state='SUB' (Gmail sweeper backfill).
    - Deletes AI_AUDIT_LOGS (retention pruning).
    """
    def __init__(self):
        super().__init__("WatchdogWorker")
        self.core_db_path = os.path.join(
            os.environ.get("NEXUS_SHARED_DIR", "."), "data", "nexus_core.db"
        )
        self._last_renewal_ts = 0
        self._last_prune_ts = 0
        self._last_sweep_ts = 0

    async def process(self):
        """
        Runs four health checks at appropriate intervals:
        - Zombie reclamation: every 5 minutes
        - Gmail sweeper backfill: every 10 minutes
        - Webhook renewal: every 12 hours
        - Audit pruning: every 24 hours

        Args/Returns:
        - None
        """
        await asyncio.sleep(300)  # 5-minute cadence for zombie check
        current_ts = int(time.time())

        await self._reclaim_zombies(current_ts)

        if current_ts - self._last_sweep_ts > 600:
            await self._sweep_gmail(current_ts)
            self._last_sweep_ts = current_ts

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

    async def _sweep_gmail(self, current_ts: int):
        """
        Pulls the 50 most recent INBOX messages from Gmail and enqueues any
        not already present in WORKSPACE_ARTIFACTS. This makes the pipeline
        resilient to Pub/Sub webhook gaps (subscription expiry, redeployment, etc.).

        Layer Interactions:
        - Layer 5 (Workspace Ingress): Reads Gmail INBOX via REST.
        - Layer 3 (State Machine): Inserts SUB artifacts for RawWorker to consume.

        Args/Returns:
        - current_ts (int): Current epoch timestamp.
        """
        import json as _json
        try:
            from backend.services.workspace import get_gmail_client

            def _list_inbox():
                gmail = get_gmail_client()
                return gmail.users().messages().list(
                    userId='me',
                    labelIds=['INBOX'],
                    maxResults=50
                ).execute()

            result = await asyncio.to_thread(_list_inbox)
            messages = result.get('messages', [])
            if not messages:
                return

            msg_ids = [m['id'] for m in messages]

            async with aiosqlite.connect(self.core_db_path, timeout=20.0) as db:
                placeholders = ','.join(['?' for _ in msg_ids])
                cursor = await db.execute(
                    f"SELECT id FROM WORKSPACE_ARTIFACTS WHERE id IN ({placeholders})",
                    msg_ids
                )
                existing = {row[0] for row in await cursor.fetchall()}

                new_ids = [mid for mid in msg_ids if mid not in existing]
                if not new_ids:
                    return

                logger.info(f"WatchdogWorker (Sweeper): Enqueuing {len(new_ids)} unseen Gmail message(s).")
                for mid in new_ids:
                    envelope = _json.dumps({"messageId": mid})
                    await db.execute("""
                        INSERT OR IGNORE INTO WORKSPACE_ARTIFACTS
                        (id, source_system, state, priority, context_hint, created_at_ts, updated_at_ts)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (mid, 'gmail', 'SUB', 3, envelope, current_ts, current_ts))
                await db.commit()

        except FileNotFoundError:
            logger.debug("WatchdogWorker (Sweeper): token.json not found — skipping sweep.")
        except Exception as e:
            logger.warning(f"WatchdogWorker (Sweeper): Gmail sweep failed: {e}")

    async def _renew_webhooks(self, current_ts: int):
        """
        Renews Gmail push-notification watch channels expiring within the next 48 hours
        by calling the real Gmail users().watch() API. Updates WEBHOOK_REGISTRY with the
        new expiration timestamp returned by Google.

        Layer Interactions:
        - Layer 5 (Workspace Ingress): Calls Gmail REST API to renew watch subscriptions.
        - Layer 2 (Data Ontology): Updates WEBHOOK_REGISTRY.expiration_ts.

        Args/Returns:
        - current_ts (int): Current epoch timestamp.
        """
        renewal_window = current_ts + (48 * 3600)
        nexus_domain = os.environ.get("NEXUS_PUBLIC_DOMAIN", "")
        project_id = os.environ.get("DOCAI_PROJECT_ID", "")

        if not nexus_domain or not project_id:
            logger.warning("WatchdogWorker: NEXUS_PUBLIC_DOMAIN or DOCAI_PROJECT_ID not set — skipping webhook renewal.")
            return

        topic_name = f"projects/{project_id}/topics/nexus-incoming-topic"

        try:
            from backend.services.workspace import get_gmail_client

            async with aiosqlite.connect(self.core_db_path) as db:
                async with db.execute(
                    "SELECT channel_id, service_type FROM WEBHOOK_REGISTRY WHERE expiration_ts < ?",
                    (renewal_window,)
                ) as cursor:
                    expiring_channels = await cursor.fetchall()

                for channel_id, service_type in expiring_channels:
                    if service_type != "GMAIL":
                        continue
                    try:
                        def _watch():
                            gmail = get_gmail_client()
                            return gmail.users().watch(
                                userId='me',
                                body={
                                    'topicName': topic_name,
                                    'labelIds': ['INBOX'],
                                    'labelFilterBehavior': 'INCLUDE'
                                }
                            ).execute()

                        watch_resp = await asyncio.to_thread(_watch)
                        new_exp_ms = int(watch_resp.get(
                            'expiration',
                            (current_ts + 7 * 86400) * 1000
                        ))
                        new_exp = new_exp_ms // 1000
                        new_history_id = watch_resp.get('historyId')

                        await db.execute(
                            "UPDATE WEBHOOK_REGISTRY SET expiration_ts = ? WHERE channel_id = ?",
                            (new_exp, channel_id)
                        )
                        logger.info(
                            f"WatchdogWorker: Renewed Gmail watch. "
                            f"New expiry: {new_exp}, historyId: {new_history_id}"
                        )
                    except Exception as e:
                        logger.error(f"WatchdogWorker: Failed to renew Gmail watch {channel_id}: {e}")

                await db.commit()

        except FileNotFoundError:
            logger.debug("WatchdogWorker: token.json not found — skipping webhook renewal.")
        except Exception as e:
            logger.error(f"WatchdogWorker: Webhook renewal error: {e}")

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
