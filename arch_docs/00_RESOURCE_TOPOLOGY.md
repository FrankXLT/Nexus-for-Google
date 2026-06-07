# Layer 0: Resource Topology & Infrastructure

## 0.1 Day Zero Architecture: The Single-Node Monolith
To ensure rapid development, operational simplicity, and immediate MVP deployment, Nexus V3 operates entirely within a single, highly optimized Virtual Machine.

While the logical architecture (CQRS databases and isolated worker loops) is designed to be easily split across a mesh network in the future, co-locating them on Day 0 ensures zero network latency for SQLite filesystem locks and simplifies the DevOps pipeline.

## 0.2 The Physical Infrastructure (GCP Edge)
- **Infrastructure:** Google Cloud Platform (GCP) `e2-micro` (Always Free Tier).
- **Resources:** 2 vCPUs (burstable), 1GB RAM, 30GB Standard Persistent Disk.
- **The 1GB RAM Survival Mandate:** Running a FastAPI server, asynchronous Python ML wrappers, and two SQLite databases on 1GB of RAM will cause Linux Out-Of-Memory (OOM) kernel panics. The `nexus.sh --provision` script **MUST** create a 2GB OS-level swap file (`/swapfile`). 
- **Security (UFW & Caddy):** The VM relies on an OS-level Uncomplicated Firewall (`ufw`) allowing ONLY ports `22` (SSH) and `443` (HTTPS). A **Caddy** Reverse Proxy manages automatic Let's Encrypt SSL termination on port `443` (using the user's provided hostname) and routes traffic internally to the FastAPI application.

## 0.3 Operational Boundaries (Single-Daemon Model)
All components share a single VM and run under a single `systemd` process (`nexus.service`) to simplify deployment.
1. **The Ingress API:** Acts strictly as a lightweight receiver. It takes Google Webhooks, drops the JSON payload into `nexus_core.db` as `RAW`, and instantly returns `HTTP 202`. It does *not* wait for AI processing.
2. **The Fusion Engine (FastAPI BackgroundTasks):** Asynchronous worker loops run as background tasks within the FastAPI event loop. They poll the databases and execute external API calls to Gemini, Document AI, and Google Workspace.
3. **The Data Layer:** Local disk access to `/opt/nexus/shared/data/nexus_core.db` and `nexus_kb.db`. Both must use `PRAGMA journal_mode=WAL` to ensure heavy extraction workers do not lock the database and block the fast webhook receiver.

## 0.4 Mermaid Topology Map

```mermaid
---
config:
  layout: elk
---
flowchart TB
 subgraph External["Public Internet"]
        GW["Google Workspace Webhooks"]
        UI["Google Apps Script UI"]
        GCP_APIs["Gemini & Document AI APIs"]
  end
 subgraph Daemon["Systemd Process (nexus.service)"]
    direction TB
        Ingress["FastAPI Webhook Receiver"]
        Worker["FastAPI BackgroundTasks\nAsync Polling & Execution"]
  end
 subgraph Databases["CQRS Storage (/opt/nexus/shared/)"]
    direction LR
        CoreDB[("nexus_core.db")]
        KBDB[("nexus_kb.db")]
  end
 subgraph VM["NODE: The Nexus Core (GCP e2-micro)"]
    direction TB
        UFW["UFW Firewall - Port 443 & 22 only"]
        Caddy@{ label: "Caddy Reverse Proxy\\nLet's Encrypt SSL" }
        Daemon
        Databases
  end
    Ingress -. Triggers .-> Worker
    UFW --> Caddy
    Caddy --> Ingress
    Ingress -- Writes RAW --> CoreDB
    Ingress -- Reads UI Queries --> KBDB
    Worker <--> Databases
    GW -- HTTPS --> UFW
    UI -- HTTPS --> UFW
    Worker -- Outbound HTTPS --> GCP_APIs

    Caddy@{ shape: rect}
     Databases:::storage
```