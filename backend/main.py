from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

from backend.routers import auth, webhooks, data, knowledge, audit, taxonomy, system, proxy
from backend.workers.watchdog import WatchdogWorker
from backend.workers.raw_worker import RawWorker
from backend.workers.ocr_worker import OcrWorker
from backend.workers.triage_worker import TriageWorker
from backend.workers.evaluating_worker import EvaluatingWorker
from backend.workers.actionable_worker import ActionableWorker
from backend.workers.assimilating_worker import AssimilatingWorker

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting background fusion workers...")
    
    watchdog_task = asyncio.create_task(WatchdogWorker().run())
    raw_task = asyncio.create_task(RawWorker().run())
    ocr_task = asyncio.create_task(OcrWorker().run())
    triage_task = asyncio.create_task(TriageWorker().run())
    evaluating_task = asyncio.create_task(EvaluatingWorker().run())
    actionable_task = asyncio.create_task(ActionableWorker().run())
    assimilating_task = asyncio.create_task(AssimilatingWorker().run())
    
    yield
    
    print("Shutting down background fusion workers...")
    for task in [watchdog_task, raw_task, ocr_task, triage_task, evaluating_task, actionable_task, assimilating_task]:
        task.cancel()

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(data.router)
app.include_router(knowledge.router)
app.include_router(audit.router)
app.include_router(taxonomy.router)
app.include_router(system.router)
app.include_router(proxy.router)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "layer": "ingress"}
