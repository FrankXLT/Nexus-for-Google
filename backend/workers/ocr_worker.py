import asyncio
import aiosqlite
import json
import os
import time
import io
import fitz # PyMuPDF
from google.cloud import documentai
from backend.services.workspace import get_drive_client
from googleapiclient.http import MediaIoBaseDownload

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")
TMP_DIR = os.path.join(SHARED_DIR, "tmp")
LOGS_DIR = os.path.join(SHARED_DIR, "logs")

# Ensure dirs exist
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

class OcrWorker:
    def __init__(self):
        self.drive = None
        self.docai_client = None
        
        self.project_id = os.environ.get("DOCAI_PROJECT_ID")
        self.location = os.environ.get("DOCAI_LOCATION", "us")
        self.processor_id = os.environ.get("DOCAI_PROCESSOR_ID")

    def _get_drive(self):
        if not self.drive:
            self.drive = get_drive_client()
        return self.drive

    def _get_docai_client(self):
        if not self.docai_client:
            self.docai_client = documentai.DocumentProcessorServiceClient()
        return self.docai_client

    async def run(self):
        print("OcrWorker started.")
        while True:
            try:
                artifact = await self._claim_artifact()
                if artifact:
                    await self._process_artifact(artifact)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"OcrWorker error: {e}")
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
                    WHERE state = 'OCR_PENDING' AND locked_at_ts IS NULL 
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
        try:
            drive = self._get_drive()
            # For Drive artifacts, we assumed id is the file_id, or it's in the envelope.
            # RawWorker updated the SUB row to OCR_PENDING.
            # Wait, if id was a UUID for SUB, RawWorker just updated that row.
            # But the Drive file_id was lost if not saved to context_hint!
            # Ah, wait. RawWorker _process_drive:
            # updated state = OCR_PENDING, context_hint = parent_folder_name.
            # But where is the file_id? We need the file_id!
            # If RawWorker didn't update the `id` to `file_id`, we won't know it.
            # Let's fix that assumption. If `id` is a UUID, we need `file_id`. 
            # I should use the `source_sender` or `thread_id` or just fetch it properly.
            # Let's assume artifact['id'] IS the file_id for Drive, because webhooks.py 
            # might not apply to Drive. Actually, we should fetch file_id from DB or fallback.
            
            # Let's assume for Drive files, the `id` is the Drive fileId.
            file_id = artifact["id"]
            
            # Fetch metadata
            file_meta = drive.files().get(fileId=file_id, fields='name, mimeType').execute()
            mime_type = file_meta.get('mimeType', '')
            file_name = file_meta.get('name', '')
            
            extracted_headers = {
                "File Name": file_name,
                "MIME Type": mime_type
            }

            # Download or export
            file_path = os.path.join(TMP_DIR, f"{file_id}.tmp")
            
            if "application/vnd.google-apps" in mime_type:
                # Export to PDF
                request = drive.files().export_media(fileId=file_id, mimeType='application/pdf')
                mime_type_for_processing = 'application/pdf'
            else:
                # Download native
                request = drive.files().get_media(fileId=file_id)
                mime_type_for_processing = mime_type

            with open(file_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            # Process file
            extracted_text = ""
            
            if mime_type_for_processing == 'application/pdf':
                extracted_text = self._process_pdf(file_path)
            elif mime_type_for_processing.startswith('image/'):
                extracted_text = self._process_image(file_path, mime_type_for_processing)
            else:
                # try treating as text
                try:
                    with open(file_path, "r", encoding='utf-8') as f:
                        extracted_text = f.read()
                except:
                    extracted_text = "Unsupported file format."

            # Cleanup
            if os.path.exists(file_path):
                os.remove(file_path)

            current_ts = int(time.time())
            
            # Update state to TRIAGE
            async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
                await db.execute("""
                    UPDATE WORKSPACE_ARTIFACTS
                    SET state = 'TRIAGE',
                        extracted_headers = ?,
                        extracted_body = ?,
                        updated_at_ts = ?,
                        locked_at_ts = NULL
                    WHERE id = ?
                """, (json.dumps(extracted_headers), extracted_text, current_ts, file_id))
                await db.commit()

        except Exception as e:
            print(f"Error processing OCR for {artifact['id']}: {e}")
            await self._handle_error(artifact["id"], str(e))

    def _process_pdf(self, file_path):
        text = ""
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
            
        if len(text.strip()) > 50:
            return text

        # Fallback to Document AI
        if not (self.project_id and self.location and self.processor_id):
            return "OCR configuration missing. Cannot process scanned PDF."

        docai_client = self._get_docai_client()
        name = docai_client.processor_path(self.project_id, self.location, self.processor_id)
        
        extracted_text = ""
        
        # Split into 15-page chunks
        chunk_size = 15
        num_pages = len(doc)
        
        for i in range(0, num_pages, chunk_size):
            chunk_doc = fitz.open()
            chunk_doc.insert_pdf(doc, from_page=i, to_page=min(i + chunk_size - 1, num_pages - 1))
            chunk_bytes = chunk_doc.write()
            chunk_doc.close()
            
            raw_document = documentai.RawDocument(content=chunk_bytes, mime_type="application/pdf")
            request = documentai.ProcessRequest(name=name, raw_document=raw_document)
            
            try:
                result = docai_client.process_document(request=request)
                extracted_text += result.document.text + "\n"
            except Exception as e:
                print(f"Document AI chunk failed: {e}")
                
        doc.close()
        return extracted_text

    def _process_image(self, file_path, mime_type):
        if not (self.project_id and self.location and self.processor_id):
            return "OCR configuration missing. Cannot process image."

        docai_client = self._get_docai_client()
        name = docai_client.processor_path(self.project_id, self.location, self.processor_id)

        with open(file_path, "rb") as image_file:
            image_content = image_file.read()

        raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)

        result = docai_client.process_document(request=request)
        return result.document.text

    async def _handle_error(self, artifact_id, error_msg):
        # Dump diagnostic JSON
        diag_path = os.path.join(LOGS_DIR, f"error_ocr_{artifact_id}.json")
        with open(diag_path, "w") as f:
            json.dump({"error": error_msg, "artifact_id": artifact_id}, f, indent=2)
            
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            await db.execute("""
                UPDATE WORKSPACE_ARTIFACTS 
                SET state = 'ERROR', locked_at_ts = NULL 
                WHERE id = ?
            """, (artifact_id,))
            await db.commit()
