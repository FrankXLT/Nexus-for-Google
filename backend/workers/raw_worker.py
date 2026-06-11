import asyncio
import aiosqlite
import json
import os
import time
import re
import base64
from bs4 import BeautifulSoup
from backend.services.workspace import get_gmail_client, get_drive_client

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

class RawWorker:
    def __init__(self):
        self.gmail = None
        self.drive = None

    def _get_gmail(self):
        if not self.gmail:
            self.gmail = get_gmail_client()
        return self.gmail

    def _get_drive(self):
        if not self.drive:
            self.drive = get_drive_client()
        return self.drive

    async def run(self):
        print("RawWorker started.")
        while True:
            try:
                artifact = await self._claim_artifact()
                if artifact:
                    await self._process_artifact(artifact)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"RawWorker error: {e}")
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
                    WHERE state = 'SUB' AND locked_at_ts IS NULL 
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
        source_system = artifact.get("source_system")
        if source_system == "gmail":
            await self._process_gmail(artifact)
        elif source_system == "drive":
            await self._process_drive(artifact)
        else:
            # Unknown system, mark error
            await self._mark_error(artifact["id"])

    async def _process_gmail(self, artifact):
        try:
            envelope = json.loads(artifact.get("context_hint", "{}"))
            # The envelope data usually has historyId
            history_id = envelope.get("historyId")
            
            if not history_id:
                # If no historyId, try to see if it has messageId directly (legacy Sweeper)
                message_id = envelope.get("messageId")
                if message_id:
                    gmail = self._get_gmail()
                    await self._fetch_and_store_gmail_message(message_id)
            else:
                gmail = self._get_gmail()
                try:
                    history_response = gmail.users().history().list(userId='me', startHistoryId=history_id).execute()
                    histories = history_response.get('history', [])
                    for record in histories:
                        for message_added in record.get('messagesAdded', []):
                            msg = message_added.get('message', {})
                            msg_id = msg.get('id')
                            if msg_id:
                                await self._fetch_and_store_gmail_message(msg_id)
                except Exception as e:
                    print(f"Error fetching history: {e}")
            
            # Delete the SUB trigger
            async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
                await db.execute("DELETE FROM WORKSPACE_ARTIFACTS WHERE id = ?", (artifact["id"],))
                await db.commit()
        except Exception as e:
            print(f"Error processing Gmail SUB {artifact['id']}: {e}")
            await self._mark_error(artifact["id"])

    async def _fetch_and_store_gmail_message(self, message_id):
        gmail = self._get_gmail()
        try:
            msg = gmail.users().messages().get(userId='me', id=message_id, format='full').execute()
        except Exception as e:
            print(f"Could not fetch message {message_id}: {e}")
            return

        payload = msg.get('payload', {})
        headers_list = payload.get('headers', [])
        
        # Extract headers
        vital_headers = ['From', 'To', 'Cc', 'Subject', 'Date']
        extracted_headers = {}
        source_sender = ""
        for h in headers_list:
            name = h.get('name')
            if name in vital_headers:
                extracted_headers[name] = h.get('value')
                if name == 'From':
                    # extract just email
                    match = re.search(r'<([^>]+)>', h.get('value'))
                    source_sender = match.group(1) if match else h.get('value')
                    
        thread_id = msg.get('threadId')
        
        # Check if ignored category
        label_ids = msg.get('labelIds', [])
        is_ignored = False
        
        # Fetch ignored categories from system config
        ignored_categories = []
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            cursor = await db.execute("SELECT value_json FROM CONFIG_SYSTEM WHERE key = 'ignored_gmail_categories'")
            row = await cursor.fetchone()
            if row:
                try:
                    ignored_categories = json.loads(row[0])
                except:
                    pass
        
        for label in label_ids:
            if label in ignored_categories:
                is_ignored = True
                break

        # Thread Inheritance check FIRST
        # LAYER 3 INLINE: The Thread Inheritance (thread_id) checks and Quoted Reply stripping in raw_worker.py.
        # New emails in an existing thread MUST inherit the linkage classification of the parent 
        # to prevent fragmented ontological assignments and bypass the TRIAGE/EVALUATING queues.
        is_inherited = False
        mapped_linkage_id = None
        state = 'TRIAGE'
        nexus_starred = 0
        current_ts = int(time.time())
        
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            cursor = await db.execute("""
                SELECT mapped_linkage_id FROM WORKSPACE_ARTIFACTS
                WHERE thread_id = ? AND mapped_linkage_id IS NOT NULL AND id != ?
                LIMIT 1
            """, (thread_id, message_id))
            inherited_row = await cursor.fetchone()
            
            if inherited_row:
                is_inherited = True
                state = 'ACTIONABLE'
                nexus_starred = 1
                mapped_linkage_id = inherited_row[0]

        # Extract body
        body_text = self._extract_body(payload)
        
        # Clean HTML / Quoted replies conditionally
        cleaned_body = self._clean_email_body(body_text, is_inherited)
        
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("BEGIN IMMEDIATE")
            
            if is_ignored:
                await db.execute("""
                    INSERT OR IGNORE INTO WORKSPACE_ARTIFACTS
                    (id, source_system, state, priority, thread_id, source_sender, created_at_ts, updated_at_ts, extracted_headers, extracted_body)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (message_id, 'gmail', 'IGNORED', 1, thread_id, source_sender, current_ts, current_ts, None, None))
                await db.commit()
                return

            await db.execute("""
                INSERT OR IGNORE INTO WORKSPACE_ARTIFACTS
                (id, source_system, state, priority, thread_id, source_sender, created_at_ts, updated_at_ts, extracted_headers, extracted_body, mapped_linkage_id, nexus_starred)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (message_id, 'gmail', state, 1, thread_id, source_sender, current_ts, current_ts, json.dumps(extracted_headers), cleaned_body, mapped_linkage_id, nexus_starred))
            
            await db.commit()

    def _extract_body(self, payload):
        body_data = ""
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType')
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        body_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
                elif mime_type == 'text/html':
                    data = part.get('body', {}).get('data')
                    if data:
                        body_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif 'parts' in part:
                    # nested parts
                    body_data = self._extract_body(part)
                    if body_data:
                        break
        else:
            data = payload.get('body', {}).get('data')
            if data:
                body_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        return body_data

    def _clean_email_body(self, html_content, is_inherited: bool):
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if is_inherited:
            # Remove quoted replies ONLY if inherited
            for div in soup.find_all("div", class_="gmail_quote"):
                div.decompose()
                
            for blockquote in soup.find_all("blockquote"):
                blockquote.decompose()
            
        text = soup.get_text(separator='\n')
        
        if is_inherited:
            # Clean lines starting with > ONLY if inherited
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                if not line.lstrip().startswith('>'):
                    cleaned_lines.append(line)
            text = '\n'.join(cleaned_lines)
                
        return text.strip()

    async def _process_drive(self, artifact):
        # A Drive SUB might contain resourceId in context_hint or id is file_id
        try:
            envelope = json.loads(artifact.get("context_hint", "{}"))
            file_id = envelope.get("resourceId") # Adjust based on actual webhooks
            if not file_id:
                file_id = envelope.get("fileId") # fallback
            
            if file_id:
                drive = self._get_drive()
                file_meta = drive.files().get(fileId=file_id, fields='id, name, mimeType, parents').execute()
                
                parent_folder_name = ""
                parents = file_meta.get('parents', [])
                if parents:
                    parent_meta = drive.files().get(fileId=parents[0], fields='name').execute()
                    parent_folder_name = parent_meta.get('name', '')
                
                current_ts = int(time.time())
                async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
                    await db.execute("BEGIN IMMEDIATE")
                    
                    # Insert the new row with id=file_id
                    await db.execute("""
                        INSERT OR IGNORE INTO WORKSPACE_ARTIFACTS
                        (id, source_system, state, priority, context_hint, created_at_ts, updated_at_ts)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (file_id, 'drive', 'OCR_PENDING', 1, parent_folder_name, current_ts, current_ts))
                    
                    # Delete the original SUB trigger
                    await db.execute("DELETE FROM WORKSPACE_ARTIFACTS WHERE id = ?", (artifact["id"],))
                    await db.commit()
            else:
                # no file_id found, delete or error
                await self._mark_error(artifact["id"])
                
        except Exception as e:
            print(f"Error processing Drive SUB {artifact['id']}: {e}")
            await self._mark_error(artifact["id"])

    async def _mark_error(self, artifact_id):
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("UPDATE WORKSPACE_ARTIFACTS SET state = 'ERROR', locked_at_ts = NULL WHERE id = ?", (artifact_id,))
            await db.commit()
            await db.commit()
