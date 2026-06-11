# Nexus V3: Asynchronous Closed-Loop Fusion Engine

Nexus V3 is an enterprise-grade AI engine designed to bridge the gap between unstructured data sources (Gmail, Google Drive) and a structured knowledge graph ontology. It employs a 7-Layer Architecture to maintain a single source of truth, enforce declarative access control, and provide a visually generative UI interface.

## 7-Layer Architecture

1. **L1: Foundation** - Base DevOps, automated deployment (`nexus.sh`), systemd integration, and root telemetry.
2. **L2: Data Ontology** - A unified CQRS SQLite approach. `nexus_core.db` handles system routing and fast lookups; `nexus_kb.db` powers full-text search (FTS5) and RAG capabilities.
3. **L3: State Machine** - Core async loop (Raw -> Assimilating -> Evaluating -> Triage -> Actionable -> Completed). Workers poll the database idempotently, ensuring the engine never halts.
4. **L4: Cognitive AI** - Hybrid LLM triage (Tier 1 vs. Tier 2) with DocAI extraction fallbacks to securely parse attachments and emails.
5. **L5: Workspace Sync** - Declarative folder mapping, label synchronization, and pruning against Google Workspace.
6. **L6: Frontend UI** - An Omnibox-driven React UI, featuring DOM Virtualization, Server-side pagination, and an interactive Visual Query Builder (VQB).
7. **L7: Chromatic Engine** - Dynamic UI theming via generated CSS variables aligned with Euclidean distances for WCAG compliance.

## Tech Stack
* **Backend:** Node.js/Python (FastAPI hybrid structure)
* **Frontend:** React, Vite, Vanilla CSS + Tailwind, SVG Data Vis
* **Database:** SQLite (CQRS structure)
* **Infrastructure:** Caddy, Systemd, GCP Pub/Sub

See `DEPLOYMENT_GUIDE.md` for zero-downtime deployment instructions and GCP provisioning.