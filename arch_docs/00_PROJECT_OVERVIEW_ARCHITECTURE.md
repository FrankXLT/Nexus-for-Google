# Project Nexus: Executive Overview & Baseline Architecture

## 1. The Vision & Core Problem
Modern knowledge workers suffer from "Workspace Fragmentation." Inboxes and cloud drives are chaotic, unindexed dumping grounds of PDFs, receipts, newsletters, and contracts. Native search tools (like Gmail or Drive search) rely on exact keyword matches, completely failing to understand the *semantic intent* or *relationship* between files.

**Project Nexus** is an Asynchronous Closed-Loop Fusion Engine. It bridges the gap between unstructured Google Workspace data and a highly structured, AI-driven Semantic Knowledge Graph. It does not replace Google Workspace; it sits on top of it as an intelligent routing, extraction, and visualization layer.

### Primary Objectives:
1. **Zero-Touch Triage:** Automatically identify, categorize, and route incoming emails and files based on historical context and AI deduction without human intervention.
2. **Data Sovereignty:** Mutate the actual Google Workspace (applying labels, moving folders, injecting metadata) so the organization survives even if Nexus is turned off.
3. **Deep RAG Extraction:** Read the contents of files/emails, extract structured JSON facts (e.g., Invoice Totals, Tracking Numbers), and store them in a lightning-fast Full-Text Search (FTS5) SQLite database.
4. **Visual Knowledge:** Provide an Omnibox-driven interface that visualizes relationships via Heatmaps, Sankey diagrams, and Treemaps.

---

## 2. The 7-Layer Architecture
To prevent AI hallucination and ensure long-term stability, the system is strictly segmented into 7 operational layers. This separation of concerns prevents AI coding agents from creating "spaghetti code" across domains.

~~~mermaid
flowchart TD
    L1[Layer 1: Foundation<br/>DevOps, Caddy, Systemd, Telemetry]
    L2[Layer 2: Data Ontology<br/>CQRS SQLite, FTS5 RAG Index]
    L3[Layer 3: State Machine<br/>Async Worker Loops]
    L4[Layer 4: Cognitive AI<br/>Tiered Gemini LLMs, DocAI OCR]
    L5[Layer 5: Workspace Sync<br/>Bi-Directional Drive/Gmail Mutation]
    L6[Layer 6: Frontend UI<br/>Tri-Mode Search, Omnibox, Virtualization]
    L7[Layer 7: Chromatic Engine<br/>AI Generative Colors, Euclidean Snapping]
    
    L6 -->|API| L1
    L1 --> L2
    L3 -->|Polls| L2
    L3 -->|Invokes| L4
    L3 -->|Mutates| L5
    L7 -->|Styles| L6
    L7 -->|Snaps to API| L5
~~~

---

## 3. The Fusion Engine State Machine
Nexus does not use "step-by-step" linear scripts. It uses a **Blackboard Pattern**. Artifacts are dropped into the database, and isolated Python `asyncio` workers move them through states until they reach `COMPLETED`.

~~~mermaid
stateDiagram-v2
    [*] --> SUB: Proxy Search / Live Webhook
    
    SUB --> RAW: RawWorker (Hydrate Payload)
    RAW --> OCR_PENDING: If Drive PDF/Image
    RAW --> TRIAGE: If Email
    OCR_PENDING --> TRIAGE: OcrWorker Extracts Text
    
    state Triage_Decision {
        TRIAGE --> ACTIONABLE: Entity & Purpose Known (SQL/Micro-LLM)
        TRIAGE --> EVALUATING: Unknown Sender / Novel Data
        EVALUATING --> QUARANTINE: Heavy LLM Deduction
        QUARANTINE --> ACTIONABLE: Human Approval via UI
    }
    
    ACTIONABLE --> ASSIMILATING: Workspace Mutator (Syncs Labels/Folders)
    ASSIMILATING --> COMPLETED: Deep RAG JSON Extraction
    COMPLETED --> [*]
~~~

---

## 4. Operational Ingress Strategy (The Proxy)
Nexus balances real-time automation with deliberate human control to protect API quotas.
1. **Live Webhooks (Priority 1):** Google Cloud Pub/Sub pushes live email/drive events to the API. Processed instantly.
2. **Proxy Search / Staging (Priority 2):** To prevent unwanted legacy data ingestion, the UI features a "Proxy Search" mode. The user searches Gmail natively through the Nexus Omnibox, selects specific historical threads, and queues them for AI ingestion.

---

## 5. Security & Access Control
- **Authentication:** Strict OAuth 2.0 OpenID Connect via "Sign in with Google." Passwords are fundamentally eliminated.
- **The Bouncer:** The backend explicitly verifies the Google JWT signature and cross-references the email against a hardcoded `.env` allowlist (`AUTHORIZED_EMAILS`).
- **Telemetry:** Every LLM request/response is compressed via `zlib` and stored in an `AI_AUDIT_LOGS` table, allowing administrators to audit the exact reasoning behind any AI taxonomy decision.

---

## 6. The Origin of the UARC Directive
The UARC (Unified AI Robotic Coding) framework was created out of necessity after observing how generic AI coding agents destructively interacted with the Nexus architecture:
*   **Framework Thrashing:** AI agents attempted to rewrite the React SPA using Jinja templates, destroying the L6 architecture.
*   **Synchronous Freezing:** Agents wrote standard `requests.get()` calls to Google APIs inside FastAPI routes, completely blocking the event loop and causing the 1GB RAM server to panic. *(Solved by L3: Asynchronous Fusion Engine).*
*   **Hallucination of State:** Agents invented arbitrary artifact states (e.g., `PROCESSING`) that were not accounted for in the UI or backend logic. *(Solved by the Uncharted Sequence Law).*
*   **UI Bloat:** Agents failed to implement DOM Virtualization, causing the browser to crash when loading thousands of emails. *(Solved by L6: Frontend Rendering Law).*