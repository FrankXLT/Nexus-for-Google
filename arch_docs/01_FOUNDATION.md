# Layer 1: System Foundation & DevOps

## 1.1 Core Architecture Philosophy
Nexus V3 is an **Asynchronous Closed-Loop Fusion Engine**. It securely bridges external data platforms (Google Workspace) into a unified Zero-Trust Semantic Knowledge Graph.
- **Asynchronous Decoupling:** No webhook or ingress point waits for LLM completion. Everything is dropped into a Blackboard Database, and independent workers process state transitions.
- **Data Sovereignty:** Nexus relies on its databases for high-speed UI operations, but true knowledge is continuously injected natively back into Google Drive file properties. If Nexus is destroyed, the user's files retain their taxonomic identity.

## 1.2 Unified DevOps: The `nexus.sh` Shell
All deployment, maintenance, and diagnostics are controlled via a single Bash script at the project root (`nexus.sh`). This script completely eliminates scattered `.ps1` and `.sh` files.

**Modes of Operation:**
1. **Interactive UI:** Running `./nexus.sh` without arguments launches a color-coded terminal GUI menu.
2. **Headless Execution:** Designed for CI/CD or fast developer triggers:
   - `--provision`: Installs Python, SQLite, enables GCP APIs, creates a 2GB swap space (critical to prevent OOM crashes on 1GB e2-micro VMs), and configures the `systemd` daemon.
   - `--deploy`: Secure Zero-Downtime Deployment. Clones the repo to a timestamped folder, creates a Python venv, symlinks `/shared/data/nexus_core.db` and `/shared/data/nexus_kb.db`, updates the `/current` symlink, and restarts the daemon.
   - `--push-ui`: Executes `clasp push` to sync the frontend Single Page Application to Google Apps Script.
   - `--shell`: Opens an IAP-secured SSH tunnel to the active GCP VM.
   - `--clean`: Purges old release folders (keeping the 3 most recent) and executes `VACUUM` on both SQLite databases to optimize disk usage.

## 1.3 Telemetry & Diagnostics
Because the system runs highly parallel background processes, debugging must be deterministic.
- **State Tracing:** Any "stuck" artifact is instantly debugged by querying `SELECT id, state FROM WORKSPACE_ARTIFACTS`.
- **System Logs:** All workers write cleanly to standard out, managed by systemd (`journalctl -u nexus.service -f`).
- **Hallucination Dumps:** Every raw Gemini API request payload and exact response is logged to a secure Google Drive `Diagnostics` folder. If the LLM generates a bad categorization, the exact dynamic prompt that caused it is permanently captured for review.
- **AI Studio Datasets:** Successful (or human-corrected via QUARANTINE) categorizations are logged locally in `.jsonl` format, allowing export to Google AI Studio for fine-tuning.
- **System Blocklist:** `CONFIG_SYSTEM` contains global blocklists (domains, keywords) to intercept known junk before it reaches an LLM.