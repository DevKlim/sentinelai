import uvicorn
from fastapi import FastAPI, Body, HTTPException
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
# A simple file-based flag to enable/disable categorizer across restarts
CATEGORIZER_ENABLED_FLAG = "categorizer_enabled.flag"

def is_categorizer_enabled():
    return os.path.exists(CATEGORIZER_ENABLED_FLAG)

def set_categorizer_enabled(enable: bool):
    if enable:
        if not os.path.exists(CATEGORIZER_ENABLED_FLAG):
            open(CATEGORIZER_ENABLED_FLAG, 'a').close()
    else:
        if os.path.exists(CATEGORIZER_ENABLED_FLAG):
            os.remove(CATEGORIZER_ENABLED_FLAG)

def start_categorizer():
    """Starts the categorizer thread if it's enabled and not running."""
    global categorizer_thread, stop_categorizer_event
    if is_categorizer_enabled() and (categorizer_thread is None or not categorizer_thread.is_alive()):
        print("Starting categorizer thread...")
        stop_categorizer_event.clear()
        categorizer_thread = threading.Thread(target=run_categorizer, args=(stop_categorizer_event,), daemon=True)
        categorizer_thread.start()

def stop_categorizer():
    """Stops the categorizer thread."""
    global categorizer_thread, stop_categorizer_event
    if categorizer_thread and categorizer_thread.is_alive():
        print("Stopping categorizer thread...")
        stop_categorizer_event.set()
        categorizer_thread.join(timeout=5)
        categorizer_thread = None

def get_categorizer_status():
    """Returns the status of the categorizer thread."""
    status = "stopped"
    if categorizer_thread and categorizer_thread.is_alive():
        status = "running"
    return {"enabled": is_categorizer_enabled(), "status": status}


@app.on_event("startup")
def startup_event():
    # Set default state to enabled if flag doesn't exist
    if not os.path.exists(CATEGORIZER_ENABLED_FLAG):
        set_categorizer_enabled(True)
    start_categorizer()
    asyncio.create_task(watch_for_restart_signal())

@app.on_event("shutdown")
def shutdown_event():
    stop_categorizer()

async def watch_for_restart_signal():
    """Checks for a restart signal and restarts the categorizer."""
    while True:
        if os.path.exists("restart_categorizer.flag"):
            print("Restarting categorizer due to settings change...")
            stop_categorizer()
            os.remove("restart_categorizer.flag")
            # Give it a moment before restarting
            await asyncio.sleep(1)
            start_categorizer()
        await asyncio.sleep(5)

@app.get("/health", status_code=200)
async def healthcheck():
    return {"status": "ok"}

@app.post("/api/v1/settings/categorizer/toggle")
async def toggle_categorizer_endpoint(payload: dict = Body(...)):
    """Enable or disable the categorizer routine."""
    enable = payload.get('enable')
    if enable is None:
        raise HTTPException(status_code=400, detail="Missing 'enable' boolean in request body.")

    set_categorizer_enabled(enable)
    if enable:
        start_categorizer()
    else:
        stop_categorizer()
    return {"message": f"Categorizer has been {'enabled' if enable else 'disabled'}.", "new_state": get_categorizer_status()}

@app.get("/api/v1/settings/categorizer/status")
async def get_categorizer_status_endpoint():
    """Gets the status of the incident categorizer routine."""
    return get_categorizer_status()


app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )