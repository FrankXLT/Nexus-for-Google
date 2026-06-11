import asyncio
import aiosqlite
import json
import os
import time
import uuid
from backend.services.workspace import get_gmail_client

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

class SweeperWorker:
    def __init__(self):
        self.next_page_token = None
        self.is_running = True

    def _sync_list_gmail(self, page_token):
        gmail = get_gmail_client()
        kwargs = {"userId": "me", "maxResults": 100}
        if page_token:
            kwargs["pageToken"] = page_token
            
        response = gmail.users().messages().list(**kwargs).execute()
        return response.get("messages", []), response.get("nextPageToken")

    async def run(self):
        print("SweeperWorker started.")
        while self.is_running:
            try:
                # Check backpressure
                # LAYER 3 INLINE: The Active Backlog Backpressure checks in sweeper_worker.py.
                # Priority constraints mandate that we halt historical ingestion if the active core 
                # processing queue exceeds 250 items. This ensures Live webhooks (Priority 1) are not 
                # drowned out by legacy sweeps (Priority 3) and prevents DB memory exhaustion.
                async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
                    cursor = await db.execute("SELECT COUNT(*) FROM WORKSPACE_ARTIFACTS WHERE state IN ('RAW', 'TRIAGE', 'EVALUATING')")
                    row = await cursor.fetchone()
                    count = row[0] if row else 0
                
                if count > 250:
                    print(f"Sweeper backpressure threshold reached ({count} > 250). Yielding...")
                    await asyncio.sleep(60)
                    continue

                # Fetch next page
                try:
                    messages, next_token = await asyncio.to_thread(self._sync_list_gmail, self.next_page_token)
                except Exception as e:
                    print(f"Sweeper Gmail List Error: {e}. Sleeping 5m.")
                    await asyncio.sleep(300) # 5 minutes sleep on quota/network error
                    continue
                
                if not messages:
                    print("Sweeper finished ingestion. No more messages.")
                    await asyncio.sleep(3600) # Sleep an hour if done
                    continue

                # Insert STUBs
                current_ts = int(time.time())
                async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
                    await db.execute("BEGIN IMMEDIATE")
                    for msg in messages:
                        artifact_id = str(uuid.uuid4()) # trigger id
                        env_json = json.dumps({"messageId": msg['id']})
                        
                        await db.execute("""
                            INSERT INTO WORKSPACE_ARTIFACTS 
                            (id, source_system, state, priority, context_hint, created_at_ts, updated_at_ts)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (artifact_id, "gmail", "SUB", 3, env_json, current_ts, current_ts))
                    await db.commit()
                
                self.next_page_token = next_token
                if not self.next_page_token:
                    print("Sweeper reached end of mailbox.")
                    await asyncio.sleep(3600)
                else:
                    await asyncio.sleep(5) # Pace ingestion

            except Exception as e:
                print(f"SweeperWorker error: {e}")
                await asyncio.sleep(60)