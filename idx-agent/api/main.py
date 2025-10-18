import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from services.categorizer import categorizer_thread
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

@app.on_event("startup")
def startup_event():
    """Handles application startup logic."""
    # Set default state to enabled if flag doesn't exist
    if not os.path.exists(categorizer_thread.flag_file):
        categorizer_thread.set_enabled(True)
    # Start the categorizer if it's enabled
    categorizer_thread.start_if_enabled()

@app.on_event("shutdown")
def shutdown_event():
    """Handles application shutdown logic."""
    categorizer_thread.stop()

@app.get("/health", status_code=200)
async def healthcheck():
    return {"status": "ok"}

# Include the API router. Endpoints for categorizer control are now in endpoints.py
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
