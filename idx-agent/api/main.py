import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .endpoints import router as api_router # <-- FIX: Use relative import
from config.settings import settings
from services.categorizer import start_categorizer

logger = logging.getLogger(__name__)

app = FastAPI(
    title="IDX Agent API",
    description="API for categorizing and managing EIDO reports into incidents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    logger.info("IDX Agent API application startup...")
    # The categorizer will now be started/stopped via API call from the dashboard
    logger.info("Startup complete. Categorizer can be enabled via the API.")

@app.get("/health", status_code=200, tags=["Health"])
async def healthcheck():
    """A simple health check endpoint to confirm the API is running."""
    return {"status": "ok", "service": "IDX Agent"}

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )