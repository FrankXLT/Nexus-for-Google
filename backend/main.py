from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

from backend.routers import auth, webhooks
from backend.workers.watchdog import WatchdogWorker
from backend.workers.raw_worker import RawWorker
from backend.workers.ocr_worker import OcrWorker

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Initializes and cleans up the Asynchronous Closed-Loop Fusion Engine workers (Layer 3).
    """
    print("Starting background fusion workers...")
    
    watchdog = WatchdogWorker()
    watchdog_task = asyncio.create_task(watchdog.run())
    
    raw_worker = RawWorker()
    raw_task = asyncio.create_task(raw_worker.run())
    
    ocr_worker = OcrWorker()
    ocr_task = asyncio.create_task(ocr_worker.run())
    
    yield
    print("Shutting down background fusion workers...")
    watchdog_task.cancel()
    raw_task.cancel()
    ocr_task.cancel()
    try:
        await watchdog_task
        await raw_task
        await ocr_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(webhooks.router)

@app.get("/api/health")
async def health_check():
    """
    Basic health check endpoint for the Ingress Layer.
    """
    return {"status": "ok", "layer": "ingress"}
