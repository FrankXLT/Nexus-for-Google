# Layer 5: Workspace Synchronization & Mutation

## 5.1 Bi-Directional Registries (The "No String Paths" Law)
Nexus manages external workspaces (Drive, Gmail) using Bi-Directional Registries. Hardcoded string paths (e.g., `Finance/AWS/Receipt`) are **FORBIDDEN**.
- When generating a folder or label, Nexus stores the immutable Google API ID in `LABEL_REGISTRY` or `FOLDER_REGISTRY`.
- If a user natively renames a folder in Drive, Nexus detects the delta on sync, updates `user_modified_name`, but maintains the ID lock. The system is completely immune to user tampering.

## 5.2 Gmail Sidebar Orchestration
To prevent "Over-Labeling Fatigue," the `ACTIONABLE` worker runs asynchronous pruning loops to keep the native Gmail UI pristine.

### Rule A: Category-Level Nav Pruning
An async background loop continuously prunes the Gmail sidebar:
1. It groups all active `TAXONOMY_LINKAGES` by `category_id`.
2. It queries the Top N linkages per category based on `last_active_ts` (using the limit defined in `CATEGORIES.top_entities_limit`).
3. It includes any linkages currently tied to an unresolved `nexus_important` or `nexus_starred` artifact.
4. It sets `labelListVisibility = labelShow` for these selected linkages via the Gmail API. All other linkages are set to `labelHide`.

### Rule B: Ghost Shortcuts (Dedicated Purposes)
If a Purpose has `is_gmail_shortcut = True` (e.g., `Delivery`, `Receipt`, `Tax`), Nexus creates a standalone Global Label.
- **API Payload:** `labelListVisibility = 'labelShow'`, `messageListVisibility = 'hide'`.
- **Result:** The shortcut exists beautifully in the sidebar for 1-click navigation, but doesn't plaster redundant label pills over the actual emails in the message list.

### Rule C: Sync Mode Overrides
The `ACTIONABLE` worker MUST respect the `gmail_sync_mode` string on the `ENTITY` (which overrides the `CATEGORY` default):
- `FULL`: Applies standard full-depth labels (e.g., `Category/Alias/Purpose`) natively in Gmail.
- `OMIT_PURPOSE`: Truncates the label. Applies `Category/Alias` only, grouping all artifacts for that sender natively.
- `HIDDEN`: Processes the artifact entirely in the Nexus database and RAG Knowledge Base, but skips ALL native Gmail API label creation and application (ideal for personal/family communications).

## 5.3 Data Sovereignty (Hybrid Drive Metadata Injection)
When processing Google Drive artifacts, the `ASSIMILATING` worker MUST inject data natively into the Google Drive file to ensure files remain queryable even if Nexus is uninstalled. 

Because the Google Drive API custom `properties` field has a strict hard limit of **124 bytes per value**, attempting to inject a deep JSON fact payload will cause an `HTTP 400` crash. The worker MUST use a hybrid injection strategy:
1. **Invisible Properties (Programmatic Indexing):** Inject the short strings `canonical_name` (Entity), `workspace_alias`, and `purpose` into the custom `properties` metadata object. This allows Nexus to execute lightning-fast programmatic queries (e.g., `q="properties has { key='Purpose' and value='Receipt' }"`).
2. **The Description Field (Deep Semantic Survival):** Inject the 1-3 sentence `ui_summary` and the raw `extracted_facts_json` string into the file's native `description` property. This field safely supports up to 32,000 characters and makes the deep facts natively searchable via the standard Google Drive web UI search bar.

## 5.4 Google Workspace Batch Operations (Quota Armor)
When processing Tier 3 historical data, the `ACTIONABLE` worker MUST NOT execute single API calls for every label application or folder move.

The coding agent MUST utilize Google's Batch execution endpoints (referencing the Dead Repo for syntax):
- **For Gmail:** Use the `users.messages.batchModify` endpoint to apply/remove labels for up to 1,000 messages in a single HTTP request.
- **For Drive:** Utilize the Google API Client's `BatchHttpRequest` object to group folder moves and property updates.
- **Trigger:** If the worker detects multiple artifacts in the `ACTIONABLE` state destined for the same mutations, it must bundle them into a single batch network call. All external API calls MUST be wrapped in robust Exponential Backoff (Jitter) handlers to survive temporary rate limits gracefully.

## 5.5 Initialization Folders & The Exclusion Law
Upon the first successful Workspace sync, Nexus MUST natively provision a root directory named `Nexus_System` in the user's Google Drive for Tier 3 error logging.
- **Default Structure:**
  - `Nexus_System/Logs/` (Batched system log zips)
  - `Nexus_System/Diagnostics/` (JSON dumps of fatal AI/API crashes)
  - `Nexus_System/Dead_Letter/` (Physical files that repeatedly crash the pipeline)
- **The Exclusion Law:** The Drive ID of the `Nexus_System` folder MUST be appended to an internal configuration exclusion blocklist. The `RAW` and `OCR_PENDING` async workers are **STRICTLY FORBIDDEN** from ingesting, reading, OCR'ing, or categorizing any files placed inside this directory to prevent infinite recursion loops where the AI attempts to analyze its own crash logs.

## 5.6 Workspace API Execution Laws
1. **The Async Threading Law:** The official `google-api-python-client` is strictly synchronous. To prevent blocking the FastAPI asynchronous event loop, all physical Workspace API calls (e.g., `execute()`) MUST be wrapped in `asyncio.to_thread(sync_func, ...)`.
2. **The Hierarchical Nesting Law:** Both Gmail Labels and Google Drive Folders require strict sequential parent creation. You cannot create a child node without the parent existing. The `WorkspaceMutator` MUST iteratively split nested paths (e.g., `Finance/Amazon/Receipt`) and ensure each parent level is physically created and stored in the Registry before attempting to create the child.