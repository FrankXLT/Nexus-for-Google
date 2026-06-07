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
   - `--provision`: Installs Python, SQLite, Caddy, enables GCP APIs, creates a 2GB swap space, configures the `ufw` firewall (allowing only ports 22 and 443), and sets up the `nexus.service` systemd daemon. Prompts for Hostname/DDNS for SSL routing.
   - `--deploy`: Secure Zero-Downtime Deployment. Clones the repo, creates a Python venv, handles interactive secret injection, manages symlinks, and restarts the daemon.
   - `--push-ui`: Executes `clasp push` to sync the frontend Single Page Application to Google Apps Script.
   - `--auth-tunnel`: Opens an IAP-secured SSH tunnel (`8080:127.0.0.1:8080`) to the VM to complete the headless OAuth 2.0 browser flow locally.
   - `--health`: Prints a dashboard showing `nexus.service` status, disk/memory usage, database sizes, and orphaned deployment folders.
   - `--backup`: Copies the SQLite `.db` files to a timestamped backup directory.
   - `--clean`: Purges old release folders (keeping the 3 most recent) and executes `VACUUM` on both SQLite databases.

## 1.3 Zero-Downtime Directory Scaffolding & Secrets
To ensure smooth deployments and prevent database locking, the VM filesystem MUST adhere to a strict structure (e.g., `/opt/nexus/`):

*   `/shared/`: Contains persistent data that must survive deployments.
    *   `/data/nexus_core.db` & `/data/nexus_kb.db`
    *   `.env` (Secrets and API keys)
    *   `credentials.json` & `token.json`
    *   `/backups/`
*   `/releases/YYYYMMDD_HHMMSS/`: Timestamped clones of the codebase containing their own Python `venv`.
*   `/current`: A symlink pointing to the active release directory in `/releases/`. The `systemd` service executes code from here.

**Interactive Secret Injection (`--deploy`):**
If `/shared/.env` does not exist during deployment, the `nexus.sh` script MUST pause and interactively prompt the user for their `NEXUS_HMAC_SECRET` and `NEXUS_API_KEY` (Gemini), saving them to the `.env` file. It must also verify the presence of `credentials.json`. Secrets are NEVER hardcoded.

## 1.4 Telemetry & Diagnostics
Because the system runs highly parallel background processes, debugging must be deterministic.
- **State Tracing:** Any "stuck" artifact is instantly debugged by querying `SELECT id, state FROM WORKSPACE_ARTIFACTS`.
- **System Logs:** All workers write cleanly to standard out, managed by systemd (`journalctl -u nexus.service -f`).
- **Hallucination Dumps:** Every raw Gemini API request payload and exact response is logged to a secure Google Drive `Diagnostics` folder. If the LLM generates a bad categorization, the exact dynamic prompt that caused it is permanently captured for review.