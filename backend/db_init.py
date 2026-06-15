import asyncio
import aiosqlite
import sqlite3
import json
import os
from pathlib import Path

# Paths
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", "/opt/nexus/shared")
DATA_DIR = Path(SHARED_DIR) / "data"
CORE_DB_PATH = DATA_DIR / "nexus_core.db"
KB_DB_PATH = DATA_DIR / "nexus_kb.db"
DEFAULTS_PATH = Path(__file__).parent.parent / "DEFAULTS" / "nexus_defaults.json"

async def init_core_db():
    print(f"Initializing {CORE_DB_PATH}...")
    # Ensure dir exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS CONFIG_PROMPTS (
            prompt_name TEXT PRIMARY KEY,
            model_tier TEXT NOT NULL,
            prompt_text TEXT NOT NULL
        ) STRICT;

        CREATE TABLE IF NOT EXISTS CONFIG_SYSTEM (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        ) STRICT;

        CREATE TABLE IF NOT EXISTS CATEGORIES (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            color_hex TEXT NOT NULL,
            extraction_prompt_name TEXT,
            top_entities_limit INTEGER NOT NULL,
            gmail_sync_mode TEXT NOT NULL,
            FOREIGN KEY(extraction_prompt_name) REFERENCES CONFIG_PROMPTS(prompt_name)
        ) STRICT;

        CREATE TABLE IF NOT EXISTS ENTITIES (
            id INTEGER PRIMARY KEY,
            category_id INTEGER NOT NULL,
            parent_entity_id INTEGER,
            canonical_name TEXT NOT NULL,
            workspace_alias TEXT,
            primary_color_hex TEXT,
            gmail_sync_mode TEXT,
            FOREIGN KEY(category_id) REFERENCES CATEGORIES(id),
            FOREIGN KEY(parent_entity_id) REFERENCES ENTITIES(id)
        ) STRICT;

        CREATE TABLE IF NOT EXISTS ALIASES (
            id INTEGER PRIMARY KEY,
            entity_id INTEGER NOT NULL,
            alias_string TEXT NOT NULL,
            FOREIGN KEY(entity_id) REFERENCES ENTITIES(id)
        ) STRICT;

        CREATE TABLE IF NOT EXISTS PURPOSES (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            color_hex TEXT NOT NULL,
            allowed_category_ids TEXT NOT NULL,
            extraction_prompt_name TEXT,
            is_gmail_shortcut INTEGER NOT NULL,
            FOREIGN KEY(extraction_prompt_name) REFERENCES CONFIG_PROMPTS(prompt_name)
        ) STRICT;

        CREATE TABLE IF NOT EXISTS LABEL_REGISTRY (
            label_id TEXT PRIMARY KEY,
            linkage_id TEXT,
            nexus_applied_name TEXT,
            user_modified_name TEXT
        ) STRICT;

        CREATE TABLE IF NOT EXISTS FOLDER_REGISTRY (
            folder_id TEXT PRIMARY KEY,
            linkage_id TEXT,
            nexus_applied_name TEXT,
            user_modified_name TEXT
        ) STRICT;

        CREATE TABLE IF NOT EXISTS TAXONOMY_LINKAGES (
            linkage_id TEXT PRIMARY KEY,
            category_id INTEGER,
            entity_id INTEGER,
            purpose_id INTEGER,
            nexus_state TEXT NOT NULL,
            last_active_ts INTEGER NOT NULL,
            FOREIGN KEY(category_id) REFERENCES CATEGORIES(id),
            FOREIGN KEY(entity_id) REFERENCES ENTITIES(id),
            FOREIGN KEY(purpose_id) REFERENCES PURPOSES(id)
        ) STRICT;

        CREATE TABLE IF NOT EXISTS WORKSPACE_ARTIFACTS (
            id TEXT PRIMARY KEY,
            mapped_linkage_id TEXT,
            thread_id TEXT,
            source_sender TEXT,
            context_hint TEXT,
            priority INTEGER NOT NULL,
            nexus_important INTEGER,
            nexus_starred INTEGER,
            ui_summary TEXT,
            state TEXT NOT NULL,
            locked_at_ts INTEGER,
            FOREIGN KEY(mapped_linkage_id) REFERENCES TAXONOMY_LINKAGES(linkage_id)
        ) STRICT;

        CREATE TABLE IF NOT EXISTS WEBHOOK_REGISTRY (
            channel_id TEXT PRIMARY KEY,
            service_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            expiration_ts INTEGER NOT NULL
        ) STRICT;

        CREATE TABLE IF NOT EXISTS AI_AUDIT_LOGS (
            id TEXT PRIMARY KEY,
            artifact_id TEXT NOT NULL,
            prompt_name TEXT NOT NULL,
            request_payload_compressed BLOB NOT NULL,
            response_payload_compressed BLOB NOT NULL,
            execution_ms INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            created_at_ts INTEGER NOT NULL,
            FOREIGN KEY(artifact_id) REFERENCES WORKSPACE_ARTIFACTS(id)
        ) STRICT;
        """)
        
        # Add missing columns dynamically
        new_columns = [
            "extracted_headers TEXT",
            "extracted_body TEXT",
            "source_system TEXT",
            "created_at_ts INTEGER",
            "updated_at_ts INTEGER"
        ]
        for col in new_columns:
            try:
                await db.execute(f"ALTER TABLE WORKSPACE_ARTIFACTS ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass # Column likely already exists

        await db.commit()

async def init_kb_db():
    print(f"Initializing {KB_DB_PATH}...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(KB_DB_PATH, timeout=20.0) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS ARTIFACT_KNOWLEDGE USING fts5(
            artifact_id,
            extracted_facts_json,
            tokenize='trigram'
        );
        """)
        await db.commit()

async def seed_database():
    """
    Populates the initial database with default taxonomy, configuration, and system parameters.

    Layer Interactions:
    - Layer 2 (Data Ontology): Seeds `nexus_core.db` using JSON defaults.

    State Interactions:
    - None

    Args/Returns:
    - None
    """
    if not DEFAULTS_PATH.exists():
        print(f"Warning: Defaults file {DEFAULTS_PATH} not found. Skipping seed.")
        return

    print("Seeding database...")
    with open(DEFAULTS_PATH, 'r') as f:
        data = json.load(f)

    async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
        for p in data.get("prompts", []):
            await db.execute("""
                INSERT OR IGNORE INTO CONFIG_PROMPTS (prompt_name, model_tier, prompt_text)
                VALUES (?, ?, ?)
            """, (p["prompt_name"], p["model_tier"], p["prompt_text"]))
            
        for c in data.get("categories", []):
            await db.execute("""
                INSERT OR IGNORE INTO CATEGORIES (id, name, description, color_hex, extraction_prompt_name, top_entities_limit, gmail_sync_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (c["id"], c["name"], c["description"], c["color_hex"], c.get("extraction_prompt_name"), c["top_entities_limit"], c["gmail_sync_mode"]))

        for p in data.get("purposes", []):
            await db.execute("""
                INSERT OR IGNORE INTO PURPOSES (id, name, description, color_hex, allowed_category_ids, extraction_prompt_name, is_gmail_shortcut)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["name"], p["description"], p["color_hex"], p["allowed_category_ids"], p.get("extraction_prompt_name"), int(p["is_gmail_shortcut"])))

        for s in data.get("system_config", []):
            await db.execute("""
                INSERT OR IGNORE INTO CONFIG_SYSTEM (key, value_json)
                VALUES (?, ?)
            """, (s["key"], s["value_json"]))
        
        await db.commit()
    print("Seeding complete.")

async def main():
    await init_core_db()
    await init_kb_db()
    await seed_database()

if __name__ == "__main__":
    asyncio.run(main())