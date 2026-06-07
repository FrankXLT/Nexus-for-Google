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

## 1.4 Telemetry & Diagnostics
Because the system runs highly parallel background processes, debugging must be deterministic.
- **State Tracing:** Any "stuck" artifact is instantly debugged by querying `SELECT id, state FROM WORKSPACE_ARTIFACTS`.
- **System Logs:** All workers write cleanly to standard out, managed by systemd (`journalctl -u nexus.service -f`).
- **Hallucination Dumps:** Every raw Gemini API request payload and exact response is logged to a secure Google Drive `Diagnostics` folder. If the LLM generates a bad categorization, the exact dynamic prompt that caused it is permanently captured for review.