# Layer 0: Resource Topology & Infrastructure

## 0.1 Day Zero Architecture: The Single-Node Monolith
To ensure rapid development, operational simplicity, and immediate MVP deployment, Nexus V3 operates entirely within a single, highly optimized Virtual Machine.

While the logical architecture (CQRS databases and isolated worker loops) is designed to be easily split across a mesh network in the future, co-locating them on Day 0 ensures zero network latency for SQLite filesystem locks and simplifies the DevOps pipeline.

## 0.2 The Physical Infrastructure (GCP Edge)
- **Infrastructure:** Google Cloud Platform (GCP) `e2-micro` (Always Free Tier).
- **Resources:** 2 vCPUs (burstable), 1GB RAM, 30GB Standard Persistent Disk.
- **The 1GB RAM Survival Mandate:** Running a FastAPI server, asynchronous Python ML wrappers, and two SQLite databases on 1GB of RAM will cause Linux Out-Of-Memory (OOM) kernel panics. The `nexus.sh --provision` script **MUST** create a 2GB OS-level swap file (`/swapfile`). 
- **Security:** Exposes standard port 443 (HTTPS) for Google Workspace Webhooks and UI polling via a reverse proxy (e.g., Caddy or Nginx). All internal services bind strictly to `localhost`.

## 0.3 Operational Boundaries
Even though all components share a single VM, they maintain strict isolation to honor the State Machine:
1. **The Ingress API (FastAPI):** Acts strictly as a lightweight receiver. It takes Google Webhooks, drops the JSON payload into `nexus_core.db` as `RAW`, and instantly returns `HTTP 202`. It does *not* wait for AI processing.
2. **The Fusion Engine (systemd):** Background Python processes that independently poll the databases and execute external API calls to Gemini, Document AI, and Google Workspace.
3. **The Data Layer:** Local disk access to `/shared/data/nexus_core.db` and `/shared/data/nexus_kb.db`. Both must use `PRAGMA journal_mode=WAL` to ensure heavy extraction workers do not lock the database and block the fast webhook receiver.

## 0.4 Mermaid Topology Map

```mermaid
---
config:
  layout: elk
---
flowchart TD
    %% External World
    subgraph External["Public Internet"]
        GW[Google Workspace Webhooks]
        UI[Google Apps Script UI]
        GCP_APIs[Gemini & Document AI APIs]
    end

    %% Physical VM Boundary
    subgraph VM["NODE: The Nexus Core (GCP e2-micro)"]
        direction TB
        
        ReverseProxy[Reverse Proxy\nCaddy/Nginx - Port 443]
        Ingress[FastAPI Webhook Receiver\nlocalhost:8000]
        
        subgraph Databases["CQRS Storage (Local Disk)"]
            direction LR
            CoreDB[(nexus_core.db)]
            KBDB[(nexus_kb.db)]
        end
        
        subgraph Workers["Systemd Async Workers"]
            direction TB
            W_Edge[Edge Workers\nRAW, TRIAGE]
            W_Heavy[Heavy Workers\nEVALUATING, ASSIMILATING, ACTIONABLE]
        end
        
        ReverseProxy --> Ingress
        Ingress -->|Writes RAW| CoreDB
        Ingress -->|Reads UI Queries| KBDB
        
        Workers <--> Databases
    end

    %% Connections
    GW -- HTTPS --> ReverseProxy
    UI -- HTTPS --> ReverseProxy
    
    Workers -- Outbound HTTPS --> GCP_APIs
    
    classDef public fill:#1e3a8a,stroke:#60a5fa,stroke-width:2px,color:#fff;
    classDef local fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef storage fill:#7c2d12,stroke:#fb923c,stroke-width:2px,color:#fff;
    
    class External public;
    class VM local;
    class Databases storage;
```