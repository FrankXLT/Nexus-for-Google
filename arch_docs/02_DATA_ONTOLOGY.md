# Layer 2: Data Ontology & Schema (The Truth Matrix)

## 2.1 The CQRS Database Paradigm
Nexus strictly separates operational routing from deep analytical search to guarantee UI performance.

### `nexus_core.db` (The Muscle)
- **Role:** High-speed OLTP. Handles state-machine routing, taxonomy configuration, registries, and webhook ingress.
- **Configuration:** Uses `PRAGMA journal_mode=WAL` and strictly typed tables (`STRICT` keyword).
- **UI Payload:** Holds the `ui_summary` (1-3 sentences) so the UI Treemap/Heatmap can render thousands of nodes instantly without loading heavy text.

### `nexus_kb.db` (The Brain)
- **Role:** Heavy OLAP. Handles the Knowledge Base.
- **Configuration:** Houses SQLite `FTS5` (Full-Text Search) Virtual Tables.
- **Data Payload:** Stores the deep JSON key-value key facts extracted by the RAG workers.

## 2.2 The Active Schema Law
Prompts and routing logic are **NOT hardcoded in Python**. The database acts as the Prompt Engineer.
- The `CONFIG_PROMPTS` table holds prompt text and explicit `model_tier` targets (e.g., `gemini-2.5-flash-8b` vs `gemini-1.5-pro`).
- The `PURPOSES` and `CATEGORIES` tables map to these prompts via `extraction_prompt_id`. 
- When an artifact needs extraction, the Python worker queries the database for the assigned prompt. 

## 2.3 The Lexical Law (Taxonomy)
1. **Categories & Purposes:** MUST be exactly **ONE WORD** (e.g., `Finance`, `Discussion`). 
2. **Aliases:** Default to official acronyms (`AWS`, `IRS`).
3. **Canonical Names:** Retain full legal names (`Amazon Web Services, Inc.`) for precise RAG indexing.

## 2.4 Schema Map (Entity Relationship)

```mermaid
---
config:
  layout: elk
---
erDiagram
	direction TB
	CONFIG_PROMPTS {
		TEXT prompt_name PK ""  
		TEXT model_tier  ""  
	}

	CONFIG_SYSTEM {
		TEXT key PK ""  
		TEXT value_json  ""  
	}

	CATEGORIES {
		INTEGER id PK ""  
		TEXT name  "Strictly One Word"  
		INTEGER extraction_prompt_id FK ""  
		INTEGER top_entities_limit  ""  
		TEXT gmail_sync_mode  ""  
	}

	ENTITIES {
		INTEGER id PK ""  
		INTEGER category_id FK ""  
		INTEGER parent_entity_id FK "Supports Sub-Entities"  
		TEXT canonical_name  ""  
		TEXT workspace_alias  ""  
		TEXT primary_color_hex  ""  
		TEXT gmail_sync_mode  ""  
	}

	ALIASES {
		INTEGER id PK ""  
		INTEGER entity_id FK ""  
		TEXT alias_string  ""  
	}

	PURPOSES {
		INTEGER id PK ""  
		TEXT name  "Strictly One Word"  
		TEXT allowed_category_ids  ""  
		INTEGER extraction_prompt_id FK ""  
		BOOLEAN is_gmail_shortcut  ""  
	}

	LABEL_REGISTRY {
		TEXT label_id PK "Immutable Gmail ID"  
		TEXT linkage_id FK ""  
		TEXT nexus_applied_name  ""  
		TEXT user_modified_name  ""  
	}

	FOLDER_REGISTRY {
		TEXT folder_id PK "Immutable Drive ID"  
		TEXT linkage_id FK ""  
		TEXT nexus_applied_name  ""  
		TEXT user_modified_name  ""  
	}

	TAXONOMY_LINKAGES {
		TEXT linkage_id PK ""  
		INTEGER category_id FK ""  
		INTEGER entity_id FK ""  
		INTEGER purpose_id FK ""  
		TEXT nexus_state  ""  
		INTEGER last_active_ts  ""  
	}

	WORKSPACE_ARTIFACTS {
		TEXT id PK ""  
		TEXT mapped_linkage_id FK ""  
		TEXT thread_id  ""  
		BOOLEAN nexus_important  ""  
		BOOLEAN nexus_starred  ""  
		TEXT ui_summary  ""  
		TEXT state  "RAW to COMPLETED"  
	}

	ARTIFACT_KNOWLEDGE {
		TEXT artifact_id PK,FK ""  
		TEXT extracted_facts_json  "FTS5 Indexed (nexus_kb.db)"  
	}

	CONFIG_PROMPTS||--o{PURPOSES:"instructs"
	CATEGORIES||--o{ENTITIES:"owns"
	ENTITIES||--o{ALIASES:"identified_by"
	ENTITIES||--o{TAXONOMY_LINKAGES:"anchors"
	PURPOSES||--o{TAXONOMY_LINKAGES:"anchors"
	TAXONOMY_LINKAGES||--o{WORKSPACE_ARTIFACTS:"routes"
	TAXONOMY_LINKAGES||--o{LABEL_REGISTRY:"tracked_by"
	TAXONOMY_LINKAGES||--o{FOLDER_REGISTRY:"tracked_by"
```