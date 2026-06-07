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

## 1.2 Unified DevOps, VM Security & Auth (`nexus.sh`)
All deployment and maintenance are controlled via `nexus.sh`. The coding agent MUST reference the Dead Repo (`Nexus-for-Google-DeadRepo/scripts/`) for legacy Bash/PowerShell syntax, but refactor it into this unified, idempotent script.

**The `--provision` Sequence (VM Standup):**
When a fresh GCP `e2-micro` VM is spun up, the script MUST execute this strict security baseline:
1. **The Swap Law:** Allocate a 2GB `/swapfile` (`swappiness=10`) to prevent OOM panics during LLM and database processing on the 1GB RAM VM.
2. **OS Firewall (`ufw`):** Enable Uncomplicated Firewall. Strictly allow *only* Port `443` (HTTPS) and Port `22` (SSH). Block all others.
3. **GCP Network Firewall:** Use the `gcloud` CLI to attach a network tag explicitly allowing TCP `443` and dropping all other external ingress.
4. **IAP Identity Proxy:** Configure GCP Identity-Aware Proxy (IAP) to allow zero-trust SSH access from the developer without exposing Port `22` to the open internet.
5. **Reverse Proxy:** Install Caddy (or Nginx) to securely terminate SSL (Let's Encrypt) and reverse-proxy external Port `443` traffic to the internal FastAPI `127.0.0.1:8000` port.
6. **Daemonization:** Create `nexus.service` in `systemd` to ensure the asynchronous worker loops automatically restart on VM reboot or crash.

**The Auth Tunnel (`--auth-tunnel`):**
- Harvest the auth-tunneling concept from the Dead Repo (`auth_tunnel.sh`/`ps1`). Because Nexus runs on a headless VM, standard OAuth 2.0 flows fail when attempting to launch a local browser. The script must establish a secure SSH port-forwarding tunnel via GCP IAP so the developer can click a `localhost` link on their physical machine, authenticate, and securely route the callback to the headless VM.

## 1.3 Telemetry & Diagnostics
Because the system runs highly parallel background processes, debugging must be deterministic.
- **State Tracing:** Any "stuck" artifact is instantly debugged by querying `SELECT id, state FROM WORKSPACE_ARTIFACTS`.
- **System Logs:** All workers write cleanly to standard out, managed by systemd (`journalctl -u nexus.service -f`).
- **Hallucination Dumps:** Every raw Gemini API request payload and exact response is logged to a secure Google Drive `Diagnostics` folder. If the LLM generates a bad categorization, the exact dynamic prompt that caused it is permanently captured for review.
- **AI Studio Datasets:** Successful (or human-corrected via QUARANTINE) categorizations are logged locally in `.jsonl` format, allowing export to Google AI Studio for fine-tuning.
- **System Blocklist:** `CONFIG_SYSTEM` contains global blocklists (domains, keywords) to intercept known junk before it reaches an LLM.