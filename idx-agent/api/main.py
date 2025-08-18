import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.endpoints import router as api_router
from config.settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="IDX Agent API",
    description="API for categorizing and managing EIDO reports into incidents.",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for simplicity; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    """Logs a message when the application starts."""
    logger.info("IDX Agent API application startup complete.")
    # In the future, you could initialize other resources here if needed.


@app.get("/health", status_code=200, tags=["Health"])
async def healthcheck():
    """A simple health check endpoint to confirm the API is running."""
    return {"status": "ok", "service": "IDX Agent"}

# Include the main API router
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )