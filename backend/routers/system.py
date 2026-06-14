from fastapi import APIRouter, Depends, HTTPException, Body
import aiosqlite
import os
import json
from pydantic import BaseModel
from typing import Dict
from backend.dependencies import get_current_user
from backend.services.llm import call_llm

router = APIRouter(prefix="/api/system", tags=["system"])
SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

class ThemeResponseSchema(BaseModel):
    support_colors: Dict[str, str]
    category_colors: Dict[str, str]
    purpose_colors: Dict[str, str]

@router.get("/config")
async def get_config(user: str = Depends(get_current_user)):
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT config_key, config_value FROM CONFIG_SYSTEM")
        rows = await cursor.fetchall()
        return {row['config_key']: row['config_value'] for row in rows}

@router.patch("/config")
async def update_config(payload: Dict[str, str] = Body(...), user: str = Depends(get_current_user)):
    """
    Updates global system configuration variables atomically.

    Layer Interactions:
    - Layer 6 (Frontend UI): Saves user preferences from the Settings Modal.

    State Interactions:
    - None

    Args/Returns:
    - Args: Dictionary of keys and values to update
    - Returns: JSON status
    """
    async with aiosqlite.connect(CORE_DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        for k, v in payload.items():
            await db.execute("UPDATE CONFIG_SYSTEM SET config_value = ? WHERE config_key = ?", (str(v), k))
        await db.commit()
        return {"status": "success"}

@router.post("/theme/generate")
async def generate_theme(user: str = Depends(get_current_user)):
    try:
        # Prompt call_llm for the UI theme using Gemini 2.5 Pro
        # Note: We assume call_llm handles fetching 'GENERATE_UI_THEME' from CONFIG_PROMPTS.
        theme_data = await call_llm(
            artifact_id="system", 
            prompt_name="GENERATE_UI_THEME", 
            payload_text="Generate the Chromatic Engine UI Theme.", 
            response_model=ThemeResponseSchema
        )
        
        # If call_llm returns a raw JSON string rather than a Pydantic object, parse it.
        if isinstance(theme_data, str):
            theme_data = ThemeResponseSchema.parse_raw(theme_data)

        support_json = json.dumps(theme_data.support_colors)

        async with aiosqlite.connect(CORE_DB_PATH, timeout=30.0) as db:
            await db.execute("BEGIN IMMEDIATE")
            
            # 1. Update Global Support Colors
            await db.execute(
                "UPDATE CONFIG_SYSTEM SET config_value = ? WHERE config_key = 'ui_theme_support'", 
                (support_json,)
            )
            
            # 2. Update Category Colors
            for cat_name, color in theme_data.category_colors.items():
                await db.execute("UPDATE CATEGORIES SET color_hex = ? WHERE name = ?", (color, cat_name))
                
            # 3. Update Purpose Colors
            for purp_name, color in theme_data.purpose_colors.items():
                await db.execute("UPDATE PURPOSES SET color_hex = ? WHERE name = ?", (color, purp_name))
                
            await db.commit()
            
        return {"status": "success", "colors_applied": len(theme_data.category_colors) + len(theme_data.purpose_colors)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Theme generation failed: {str(e)}")
