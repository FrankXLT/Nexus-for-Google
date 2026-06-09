# Layer 1: System Foundation & DevOps

## 1.1 Core Architecture Philosophy
Nexus V3 is an **Asynchronous Closed-Loop Fusion Engine**. It securely bridges external data platforms (Google Workspace) into a unified Zero-Trust Semantic Knowledge Graph.
- **Asynchronous Decoupling:** No webhook or ingress point waits for LLM completion. Everything is dropped into a Blackboard Database, and FastAPI `BackgroundTasks` process state transitions asynchronously.
- **Data Sovereignty:** Nexus relies on its databases for high-speed UI operations, but true knowledge is continuously injected natively back into Google Drive file properties. If Nexus is destroyed, the user's files retain their taxonomic identity.

## 1.2 Unified DevOps: The `nexus.sh` Shell
All deployment, maintenance, diagnostics, and tunneling are controlled via a single Bash script at the project root (`nexus.sh`). The coding agent MUST reference the Dead Repo (`Nexus-for-Google-DeadRepo/scripts/`) for legacy Bash/PowerShell syntax, but refactor it into this unified, idempotent script.

**Modes of Operation:**
1. **Interactive UI:** Running `./nexus.sh` without arguments launches a color-coded terminal GUI menu.
2. **Headless Execution:** Designed for CI/CD or fast developer triggers:
   - `--provision`: Installs Python, SQLite, Node.js, Caddy, enables GCP APIs, creates a 2GB swap space, and configures the `ufw` firewall. 
     - **Pre-Flight Check:** It MUST execute `gcloud auth print-access-token` to verify the VM is authenticated. If not, it warns the user to run `gcloud auth login` and aborts.
     - **Domain & Pub/Sub:** It interactively prompts for the DDNS/Domain, saves it to `.env` as `NEXUS_PUBLIC_DOMAIN`, and explicitly provisions the Google Cloud Pub/Sub topic named `nexus-incoming-topic` and a push subscription named `nexus-incoming-sub` routing to `https://$NEXUS_PUBLIC_DOMAIN/webhook/gmail`.
   - `--deploy`: Secure Zero-Downtime Deployment. Clones the repo into a timestamped `/releases/YYYYMMDD_HHMMSS/` folder, creates a local venv, builds the SPA frontend (or generates an `index.html` stub if the frontend is not yet built), executes `python backend/db_init.py` (which seeds the database from `nexus_defaults.json` if empty), updates the `/current` symlink, and restarts the daemon.
   - `--auth-tunnel`: Opens an IAP-secured SSH tunnel (`8080:127.0.0.1:8080`) to the VM. **The admin MUST use this tunnel to manually execute `python backend/auth/workspace_auth.py`**, which binds to port 8080 to complete the headless OAuth 2.0 flow for Google Workspace access.
   - `--health`: Prints a dashboard showing system status, disk/memory usage, database sizes, and active webhooks.
   - `--backup`: Copies the SQLite `.db` files to a timestamped backup directory.
   - `--clean`: Purges old releases and executes `VACUUM` on SQLite databases.

**The GCP Production Mandate:** For Google to issue a permanent Refresh Token, the Google Cloud OAuth Consent Screen MUST be set to "In production". If left in "Testing", Google will revoke the token every 7 days. The auth script MUST request `access_type='offline'` and `prompt='consent'`.

## 1.3 Zero-Downtime Directory Scaffolding & Secrets
To ensure smooth deployments and prevent database locking, the VM filesystem MUST adhere to a strict structure (e.g., `/opt/nexus/`):
*   `/shared/`: Contains persistent data that must survive deployments.
    *   `/data/nexus_core.db` & `/data/nexus_kb.db`
    *   `/tmp/` (Temporary streaming buffer for large file downloads)
    *   `/logs/` (Local system logs before Drive batch upload)
*   `.env` (Secrets, API keys, `NEXUS_PUBLIC_DOMAIN`, `GOOGLE_CLIENT_ID`, `AUTHORIZED_EMAILS`, and Document AI configs: `DOCAI_PROJECT_ID`, `DOCAI_LOCATION`, `DOCAI_PROCESSOR_ID`).
    *   `credentials.json` & `token.json`
    *   `/backups/`
*   `/releases/YYYYMMDD_HHMMSS/`: Timestamped clones of the codebase containing their own Python `venv` and built `frontend/dist` directory.
*   `/current`: A symlink pointing to the active release directory in `/releases/`. The `systemd` service and `Caddy` web server execute and serve code exclusively from here.

**Interactive Secret Injection (`--deploy`):** If `/shared/.env` does not exist during deployment, the `nexus.sh` script MUST pause and interactively prompt the user for their `NEXUS_HMAC_SECRET`, `NEXUS_API_KEY` (Gemini), `NEXUS_PUBLIC_DOMAIN`, `AUTHORIZED_EMAILS`, and **`GOOGLE_CLIENT_ID`**, saving them to the `.env` file.

## 1.4 Tiered Telemetry & Diagnostics
Because the system runs highly parallel non-deterministic AI processes, debugging must be tiered and accessible.

1. **Tier 1: UI Decision Tracing (Hot Telemetry):** Every LLM invocation MUST be logged to the `AI_AUDIT_LOGS` table in `nexus_core.db`. This allows the UI to render the exact prompt, payload, and response that led to a specific taxonomy decision, eliminating the "black box" effect. To prevent database bloat, the JSON payloads MUST be compressed using `zlib` and stored as SQLite `BLOB`s.
2. **Tier 2: Live System Logs (systemd & Local Disk):** Standard Python `logging` (INFO/WARN/ERROR) is pushed to `stdout` (viewable via `journalctl -u nexus.service -f`) and written to a local file (`/opt/nexus/shared/logs/nexus.log`). 
3. **Tier 3: Cold Storage (Google Drive Batch Sync):** To prevent disk bloat and API rate limits, the `WATCHDOG_ENGINE` loop compresses the local log file daily, uploads it to Google Drive (`Nexus_System/Logs/`), and clears the local file. Synchronous API logging to Drive is strictly forbidden. If a worker encounters an unrecoverable failure, it dumps the raw payload and stack trace as a standalone `.json` file into `Nexus_System/Diagnostics/`.