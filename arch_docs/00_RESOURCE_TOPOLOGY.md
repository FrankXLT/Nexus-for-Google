# Layer 0: Resource Topology & Infrastructure

## 0.1 Day Zero Architecture: The Single-Node Monolith
To ensure rapid development, operational simplicity, and immediate MVP deployment, Nexus V3 operates entirely within a single, highly optimized Virtual Machine.

While the logical architecture (CQRS databases and isolated worker loops) is designed to be easily split across a mesh network in the future, co-locating them on Day 0 ensures zero network latency for SQLite filesystem locks and simplifies the DevOps pipeline.

## 0.2 The Physical Infrastructure (GCP Edge)
- **Infrastructure:** Google Cloud Platform (GCP) `e2-micro` (Always Free Tier).
- **Resources:** 2 vCPUs (burstable), 1GB RAM, 30GB Standard Persistent Disk.
- **The 1GB RAM Survival Mandate:** Running a FastAPI server, asynchronous Python ML wrappers, and two SQLite databases on 1GB of RAM will cause Linux Out-Of-Memory (OOM) kernel panics. The `nexus.sh --provision` script **MUST** create a 2GB OS-level swap file (`/swapfile`). 
- **Security & Routing (Caddy Proxy):** The VM relies on an OS-level Uncomplicated Firewall (`ufw`) allowing ONLY ports `22` (SSH) and `443` (HTTPS). A **Caddy** Reverse Proxy manages automatic Let's Encrypt SSL termination on port `443` (using the user's provided DDNS or Custom Domain). Caddy statically serves the built Single Page Application (SPA) frontend directly on the root domain and reverse-proxies all `/api/*` and `/webhook/*` traffic internally to the FastAPI server, completely eliminating CORS.

## 0.3 Operational Boundaries (Single-Daemon Model)
All components share a single VM and run under a single `systemd` process (`nexus.service`) to simplify deployment.
1. **The Ingress API:** Acts strictly as a lightweight receiver. It takes Google Webhooks, drops the JSON payload into `nexus_core.db` as `RAW`, and instantly returns `HTTP 202`. It does *not* wait for AI processing.
2. **The Fusion Engine (FastAPI BackgroundTasks):** Asynchronous worker loops run as background tasks within the FastAPI event loop. They poll the databases and execute external API calls to Gemini, Document AI, and Google Workspace.
3. **The Data Layer:** Local disk access to `/opt/nexus/shared/data/nexus_core.db` and `nexus_kb.db`. Both must use `PRAGMA journal_mode=WAL` with a `timeout=20.0` connection parameter.

## 0.4 Mermaid Topology Map
```mermaid
---
config:
  layout: elk
---
flowchart TB
  subgraph External["External"]
        GW["GW"]
        Browser["Browser"]
        GCP_APIs["GCP_APIs"]
  end

  subgraph Daemon["Daemon"]
    direction TB
        Ingress["Ingress"]
        Worker["Worker"]
  end

  subgraph Databases["Databases"]
    direction LR
        CoreDB["CoreDB"]
        KBDB["KBDB"]
  end

  subgraph VM["VM"]
    direction TB
        UFW["UFW"]
        Caddy["Caddy Reverse Proxy<br/>Let's Encrypt SSL<br/>Static SPA & API Router"]
        Daemon
        Databases
  end
    
    Ingress -.-> Worker
    UFW --> Caddy
    Caddy --> Ingress
    Caddy --> Browser
    Ingress --> CoreDB
    Ingress --> KBDB
    Worker <--> Databases
    GW --> UFW
    Browser --> UFW
    Worker --> GCP_APIs
    Databases:::storage---
config:
  layout: elk
---
flowchart TB
  subgraph External["External"]
        GW["GW"]
        Browser["Browser"]
        GCP_APIs["GCP_APIs"]
  end

  subgraph Daemon["Daemon"]
    direction TB
        Ingress["Ingress"]
        Worker["Worker"]
  end

  subgraph Databases["Databases"]
    direction LR
        CoreDB["CoreDB"]
        KBDB["KBDB"]
  end

  subgraph VM["VM"]
    direction TB
        UFW["UFW"]
        Caddy["Caddy Reverse Proxy<br/>Let's Encrypt SSL<br/>Static SPA & API Router"]
        Daemon
        Databases
  end
    
    Ingress -.-> Worker
    UFW --> Caddy
    Caddy --> Ingress
    Caddy --> Browser
    Ingress --> CoreDB
    Ingress --> KBDB
    Worker <--> Databases
    GW --> UFW
    Browser --> UFW
    Worker --> GCP_APIs
    Databases:::storage
```