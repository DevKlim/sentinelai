
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import threading
from services.categorizer import run_categorizer

from api.endpoints import router as api_router
from config.settings import settings

app = FastAPI(
    title="IDX Agent API",
    description="API for correlating and managing emergency incidents.",
    version="1.0.0",
)

allowed_origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8080",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

categorizer_thread = None
stop_categorizer_event = threading.Event()

def start_categorizer():
    """Starts the categorizer thread."""
    global categorizer_thread, stop_categorizer_event
    stop_categorizer_event.clear()
    categorizer_thread = threading.Thread(target=run_categorizer, args=(stop_categorizer_event,), daemon=True)
    categorizer_thread.start()

def stop_categorizer():
    """Stops the categorizer thread."""
    global categorizer_thread, stop_categorizer_event
    if categorizer_thread and categorizer_thread.is_alive():
        stop_categorizer_event.set()
        categorizer_thread.join()

@app.on_event("startup")
def startup_event():
    start_categorizer()
    asyncio.create_task(watch_for_restart_signal())

@app.on_event("shutdown")
def shutdown_event():
    stop_categorizer()

async def watch_for_restart_signal():
    """Checks for a restart signal and restarts the categorizer."""
    while True:
        if os.path.exists("restart_categorizer.flag"):
            print("Restarting categorizer...")
            stop_categorizer()
            os.remove("restart_categorizer.flag")
            start_categorizer()
        await asyncio.sleep(5)

@app.get("/health", status_code=200)
async def healthcheck():
    return {"status": "ok"}

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
