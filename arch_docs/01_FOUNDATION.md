# Layer 1: System Foundation & DevOps

## 1.1 Core Architecture Philosophy
Nexus V3 is an **Asynchronous Closed-Loop Fusion Engine**. It securely bridges external data platforms (Google Workspace) into a unified Zero-Trust Semantic Knowledge Graph.
- **Asynchronous Decoupling:** No webhook or ingress point waits for LLM completion. Everything is dropped into a Blackboard Database, and FastAPI `BackgroundTasks` process state transitions asynchronously.
- **Data Sovereignty:** Nexus relies on its databases for high-speed UI operations, but true knowledge is continuously injected natively back into Google Drive file properties. If Nexus is destroyed, the user's files retain their taxonomic identity.

## 1.2 Unified DevOps: The `nexus.sh` Shell
...
   - `--provision`: Installs Python, SQLite, Node.js, Caddy, enables GCP APIs, creates a 2GB swap space, and configures the `ufw` firewall. **Domain & Pub/Sub:** It interactively prompts for the DDNS/Domain, saves it to `.env` as `NEXUS_PUBLIC_DOMAIN`, and provisions the Google Cloud Pub/Sub topic.
   - `--deploy`: Secure Zero-Downtime Deployment. Clones the repo, creates a venv, builds the SPA frontend, manages symlinks, **executes `python backend/db_init.py` (which seeds the database from `nexus_defaults.json` if empty)**, and restarts the daemon.

**The GCP Production Mandate:** For Google to issue a permanent Refresh Token, the Google Cloud OAuth Consent Screen MUST be set to "In production". If left in "Testing", Google will revoke the token every 7 days. The auth script MUST request `access_type='offline'` and `prompt='consent'`.

## 1.3 Zero-Downtime Directory Scaffolding & Secrets
To ensure smooth deployments and prevent database locking, the VM filesystem MUST adhere to a strict structure (e.g., `/opt/nexus/`):
*   `/shared/`: Contains persistent data that must survive deployments.
    *   `/data/nexus_core.db` & `/data/nexus_kb.db`
    *   `/tmp/` (Temporary streaming buffer for large file downloads)
    *   `.env` (Secrets, API keys, `NEXUS_PUBLIC_DOMAIN`, and `AUTHORIZED_EMAILS="youremail@gmail.com"` for strict login gating).

**Interactive Secret Injection (`--deploy`):**
If `/shared/.env` does not exist during deployment, the `nexus.sh` script MUST pause and interactively prompt the user for their `NEXUS_HMAC_SECRET` and `NEXUS_API_KEY` (Gemini), saving them to the `.env` file. It must also verify the presence of `credentials.json`. Secrets are NEVER hardcoded.

## 1.4 Tiered Telemetry & Diagnostics
Because the system runs highly parallel non-deterministic AI processes, debugging must be tiered and accessible.

1. **Tier 1: UI Decision Tracing (Hot Telemetry):** Every LLM invocation MUST be logged to the `AI_AUDIT_LOGS` table in `nexus_core.db`. This allows the UI to render the exact prompt, payload, and response that led to a specific taxonomy decision, eliminating the "black box" effect. To prevent database bloat, the JSON payloads MUST be compressed using `zlib` and stored as SQLite `BLOB`s.
2. **Tier 2: Live System Logs (systemd & Local Disk):** Standard Python `logging` (INFO/WARN/ERROR) is pushed to `stdout` (viewable via `journalctl -u nexus.service -f`) and written to a local file (`/opt/nexus/shared/logs/nexus.log`). 
3. **Tier 3: Cold Storage (Google Drive Batch Sync):** To prevent disk bloat and API rate limits, the `WATCHDOG_ENGINE` loop compresses the local log file daily, uploads it to Google Drive (`Nexus_System/Logs/`), and clears the local file. Synchronous API logging to Drive is strictly forbidden. If a worker encounters an unrecoverable failure, it dumps the raw payload and stack trace as a standalone `.json` file into `Nexus_System/Diagnostics/`.