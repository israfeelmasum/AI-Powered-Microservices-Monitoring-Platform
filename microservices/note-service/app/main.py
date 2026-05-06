
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from datetime import datetime
from typing import List, Optional
import asyncio
import psutil
from contextlib import asynccontextmanager
from .models.note import Note, NoteCreate, NoteUpdate
from .config.settings import settings
from .middleware.monitoring import NoteServiceMonitoring
from .metrics_collector import NoteMetricsCollector
import aiohttp

session: aiohttp.ClientSession = None  # Global session

metrics_collector = NoteMetricsCollector()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

notes_db = {}
note_id_counter = 1
START_TIME = datetime.utcnow()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global session
    logger.info("Starting Note Service")

    # ✅ Initialize a single session
    session = aiohttp.ClientSession()

    try:
        await register_with_monitoring(session)
    except Exception as e:
        logger.error(f"Failed to register with monitoring: {e}")

    await create_sample_notes()

    # ✅ Start metrics loop using shared session
    task = asyncio.create_task(push_metrics_periodically(session))

    yield

    task.cancel()
    await session.close()  # ✅ Cleanly close session
    logger.info("Shutting down Note Service")



async def register_with_monitoring(session: aiohttp.ClientSession):
    registration_data = {
        "service_name": "note-service",
        "service_url": f"http://localhost:{settings.PORT}",
        "secret_key": settings.NOTE_SERVICE_SECRET,
        "version": "1.0.0",
        "endpoints": [
            {"path": "/notes", "methods": ["GET", "POST"]},
            {"path": "/notes/{note_id}", "methods": ["GET", "PUT", "DELETE"]},
            {"path": "/health", "methods": ["GET"]},
            {"path": "/metrics", "methods": ["GET"]},
        ],
        "registered_at": datetime.utcnow().isoformat()
    }
    async with session.post(
        f"{settings.MONITORING_URL}/api/v1/register-service",
        json=registration_data,
        auth=aiohttp.BasicAuth(settings.MONITORING_ADMIN_USERNAME, settings.MONITORING_ADMIN_PASSWORD)
    ) as response:
        if response.status == 200:
            logger.info("✅ Service registration successful")
        else:
            logger.error(f"❌ Service registration failed: {response.status}")


async def create_sample_notes():
    global note_id_counter
    sample_notes = [
        {"title": "Welcome Note", "content": "Welcome to the Note Service!", "tags": ["welcome", "info"]},
        {"title": "API Documentation", "content": "This service provides CRUD operations for notes", "tags": ["docs", "api"]},
        {"title": "Monitoring Integration", "content": "This service is monitored by our centralized system", "tags": ["monitoring", "system"]},
        {"title": "Performance Testing", "content": "Use this note to test performance monitoring", "tags": ["testing", "performance"]},
        {"title": "Error Testing", "content": "This note can be used to test error scenarios", "tags": ["testing", "errors"]}
    ]
    for note_data in sample_notes:
        note = Note(
            id=note_id_counter,
            title=note_data["title"],
            content=note_data["content"],
            tags=note_data["tags"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        notes_db[note_id_counter] = note
        note_id_counter += 1

app = FastAPI(title="Note Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(NoteServiceMonitoring)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "service": "note-service",
        "version": "1.0.0",
        "notes_count": len(notes_db),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    system_metrics = metrics_collector.collect()
    return {
        "total_notes": len(notes_db),
        "uptime_seconds": (datetime.utcnow() - START_TIME).total_seconds(),
        "system_metrics": system_metrics
    }


@app.get("/notes", response_model=List[Note])
async def get_notes(skip: int = 0, limit: int = 100, tag: Optional[str] = None):
    await asyncio.sleep(0.1)
    notes = list(notes_db.values())
    if tag:
        notes = [note for note in notes if tag in note.tags]
    return notes[skip:skip + limit]

@app.post("/notes", response_model=Note)
async def create_note(note_data: NoteCreate):
    global note_id_counter
    await asyncio.sleep(0.2)
    note = Note(
        id=note_id_counter,
        title=note_data.title,
        content=note_data.content,
        tags=note_data.tags or [],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    notes_db[note_id_counter] = note
    note_id_counter += 1
    return note

@app.get("/notes/{note_id}", response_model=Note)
async def get_note(note_id: int):
    await asyncio.sleep(0.05)
    if note_id not in notes_db:
        raise HTTPException(status_code=404, detail="Note not found")
    return notes_db[note_id]

@app.put("/notes/{note_id}", response_model=Note)
async def update_note(note_id: int, note_data: NoteUpdate):
    await asyncio.sleep(0.15)
    if note_id not in notes_db:
        raise HTTPException(status_code=404, detail="Note not found")
    note = notes_db[note_id]
    if note_data.title is not None:
        note.title = note_data.title
    if note_data.content is not None:
        note.content = note_data.content
    if note_data.tags is not None:
        note.tags = note_data.tags
    note.updated_at = datetime.utcnow()
    return note

@app.delete("/notes/{note_id}")
async def delete_note(note_id: int):
    await asyncio.sleep(0.1)
    if note_id not in notes_db:
        raise HTTPException(status_code=404, detail="Note not found")
    notes_db.pop(note_id)
    return {"message": f"Note {note_id} deleted successfully"}

@app.get("/test/slow")
async def test_slow_endpoint():
    await asyncio.sleep(2)
    return {"message": "This was intentionally slow"}

@app.get("/test/error")
async def test_error_endpoint():
    raise HTTPException(status_code=500, detail="This is a test error")

@app.get("/test/memory")
async def test_memory_endpoint():
    large_data = ["x" * 1000 for _ in range(10000)]
    return {"message": f"Created {len(large_data)} items in memory"}

async def push_metrics_periodically(session: aiohttp.ClientSession):
    while True:
        try:
            metrics = metrics_collector.collect()  # Your metrics logic
            async with session.post(
                f"{settings.MONITORING_URL}/api/v1/metrics/",
                json=metrics,
                headers={
                    "X-Service-Name": "note-service",
                    "X-Service-Secret": settings.NOTE_SERVICE_SECRET
                }
            ) as response:
                if response.status in (200, 201):
                    logger.info("✅ Sent metrics to monitoring-core")
                else:
                    error_text = await response.text()
                    logger.warning(f"❌ Metrics failed: {response.status} - {error_text}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to send metrics: {e}")
        await asyncio.sleep(30)




if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True, log_level="info")
