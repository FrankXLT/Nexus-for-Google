import os
import zlib
import time
import uuid
import json
import asyncio
import aiosqlite
from google import genai
from google.genai import types

SHARED_DIR = os.environ.get("NEXUS_SHARED_DIR", ".")
CORE_DB_PATH = os.path.join(SHARED_DIR, "data", "nexus_core.db")

def get_client() -> genai.Client:
    """
    Initializes and returns the Google GenAI SDK client.

    Layer Interactions:
    - Layer 4 (Cognitive AI): Manages the connection to the Gemini API.

    State Interactions:
    - None

    Args/Returns:
    - Returns: `genai.Client`
    """
    api_key = os.environ.get("NEXUS_API_KEY")
    if not api_key:
        raise ValueError("NEXUS_API_KEY is not set in environment.")
    return genai.Client(api_key=api_key)

async def log_ai_audit(artifact_id: str, prompt_name: str, request_text: str, response_text: str, execution_ms: int, total_tokens: int):
    """
    Compresses request and response telemetry using zlib and stores it as SQLite BLOBs.

    Layer Interactions:
    - Layer 1 (Foundation): Logs granular AI execution details for DevSecOps.

    State Interactions:
    - None

    Args/Returns:
    - Args: Telemetry data including compressed text strings
    - Returns: None
    """
    # LAYER 1 INLINE: The use of zlib.compress to store payloads as SQLite BLOBs to save disk space.
    # LLM request/response text can be enormous (up to 32k tokens). Storing them as raw TEXT 
    # rapidly exhausts SQLite limits and disk space. We use zlib to compress them into BLOBs.
    req_blob = zlib.compress(request_text.encode('utf-8'))
    res_blob = zlib.compress(response_text.encode('utf-8'))
    current_ts = int(time.time())
    log_id = str(uuid.uuid4())
    
    async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
        await db.execute("""
            INSERT INTO AI_AUDIT_LOGS (id, artifact_id, prompt_name, request_payload_compressed, response_payload_compressed, execution_ms, total_tokens, created_at_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (log_id, artifact_id, prompt_name, req_blob, res_blob, execution_ms, total_tokens, current_ts))
        await db.commit()

def _generate_content_sync(model_tier, full_prompt, config):
    """
    Synchronous wrapper to execute genai client.

    Layer Interactions:
    - Layer 4 (Cognitive AI): Wraps the actual SDK call.

    State Interactions:
    - None

    Args/Returns:
    - Returns: The Google GenAI response object
    """
    client = get_client()
    return client.models.generate_content(
        model=model_tier,
        contents=full_prompt,
        config=config
    )

async def call_llm(artifact_id: str, prompt_name: str, payload_text: str, response_model=None, use_grounding=False, custom_prompt_text=None, custom_model_tier=None):
    """
    Centralized wrapper for the google-genai SDK. Fetches prompts from the DB.

    Layer Interactions:
    - Layer 4 (Cognitive AI): Core orchestrator for all LLM inference in the system.

    State Interactions:
    - None

    Args/Returns:
    - Args: artifact_id, prompt_name, payload_text, response_model, etc.
    - Returns: Parsed Pydantic model or raw text string
    """
    prompt_text = custom_prompt_text
    model_tier = custom_model_tier
    
    # 1. Fetch Prompt from Database (if not provided dynamically)
    if not prompt_text or not model_tier:
        async with aiosqlite.connect(CORE_DB_PATH, timeout=20.0) as db:
            cursor = await db.execute("SELECT prompt_text, model_tier FROM CONFIG_PROMPTS WHERE prompt_name = ?", (prompt_name,))
            row = await cursor.fetchone()
            if row:
                prompt_text = row[0]
                model_tier = row[1]
            else:
                raise ValueError(f"Prompt '{prompt_name}' not found in CONFIG_PROMPTS.")

    full_prompt = f"{prompt_text}\n\nPayload:\n{payload_text}"
    
    # 2. Configure SDK
    config_kwargs = {"temperature": 0.1}
    
    if use_grounding:
        config_kwargs["tools"] = [{"google_search": {}}]
    elif response_model:
        # LAYER 4 INLINE: How Pydantic models are passed to the response_schema configuration.
        # We pass standard Pydantic models directly to the SDK's `response_schema` parameter 
        # (while setting `response_mime_type` to application/json) to enforce strict JSON output 
        # that exactly matches our expected internal taxonomy structure.
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = response_model

    config = types.GenerateContentConfig(**config_kwargs)
    
    # 3. Invoke LLM asynchronously
    start_time = time.time()
    # LAYER 4 INLINE: Why asyncio.to_thread is used to prevent the synchronous google-genai SDK from blocking the FastAPI event loop.
    # The current Google GenAI SDK (google-genai) heavily utilizes synchronous HTTP requests. 
    # We must offload `generate_content` to a thread pool via `asyncio.to_thread` to prevent 
    # it from blocking the main FastAPI async event loop during long inference calls.
    response = await asyncio.to_thread(_generate_content_sync, model_tier, full_prompt, config)
    end_time = time.time()
    exec_ms = int((end_time - start_time) * 1000)
    
    # 4. Telemetry Logging
    try:
        tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
    except AttributeError:
        tokens = 0
        
    res_text = response.text or ""
    await log_ai_audit(artifact_id, prompt_name or "CUSTOM_PROMPT", full_prompt, res_text, exec_ms, tokens)
    
    # 5. Return Parsed Output
    if response_model and getattr(response, 'parsed', None):
        return response.parsed
    
    return res_text