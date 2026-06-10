from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

from backend.routers import auth, webhooks, data, knowledge, audit, taxonomy, system
from backend.workers.watchdog import WatchdogWorker
from backend.workers.raw_worker import RawWorker
from backend.workers.ocr_worker import OcrWorker
from backend.workers.triage_worker import TriageWorker
from backend.workers.evaluating_worker import EvaluatingWorker
from backend.workers.actionable_worker import ActionableWorker
from backend.workers.assimilating_worker import AssimilatingWorker
from backend.workers.sweeper_worker import SweeperWorker

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
    
    triage_worker = TriageWorker()
    triage_task = asyncio.create_task(triage_worker.run())
    
    evaluating_worker = EvaluatingWorker()
    evaluating_task = asyncio.create_task(evaluating_worker.run())
    
    actionable_worker = ActionableWorker()
    actionable_task = asyncio.create_task(actionable_worker.run())
    
    assimilating_worker = AssimilatingWorker()
    assimilating_task = asyncio.create_task(assimilating_worker.run())
    
    sweeper_worker = SweeperWorker()
    sweeper_task = asyncio.create_task(sweeper_worker.run())
    
    yield
    print("Shutting down background fusion workers...")
    watchdog_task.cancel()
    raw_task.cancel()
    ocr_task.cancel()
    triage_task.cancel()
    evaluating_task.cancel()
    actionable_task.cancel()
    assimilating_task.cancel()
    sweeper_task.cancel()
    try:
        await watchdog_task
        await raw_task
        await ocr_task
        await triage_task
        await evaluating_task
        await actionable_task
        await assimilating_task
        await sweeper_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(data.router)
app.include_router(knowledge.router)
app.include_router(audit.router)
app.include_router(taxonomy.router)
app.include_router(system.router)

@app.get("/api/health")
async def health_check():
    """
    Basic health check endpoint for the Ingress Layer.
    """
    return {"status": "ok", "layer": "ingress"}
"""
    return {"status": "ok", "layer": "ingress"}
