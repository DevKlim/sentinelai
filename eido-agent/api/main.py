import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.endpoints import router as api_router
from config.settings import settings
from database.session import init_db, create_db_engine_and_session

logger = logging.getLogger(__name__)

app = FastAPI(
    title="EIDO Agent API",
    description="API for creating, managing, and processing Emergency Incident Data Objects (EIDO).",
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
    """Initializes the database when the application starts."""
    logger.info("Application startup: Initializing database engine and session...")
    
    # --- ADDED: Runtime check for required settings ---
    if not settings.database_url:
        logger.critical("FATAL: DATABASE_URL is not set in the environment. The application cannot start without a database.")
        raise RuntimeError("DATABASE_URL must be set for the EIDO agent to run.")
        
    try:
        # This now creates the engine at the correct time, after env vars are loaded.
        create_db_engine_and_session()
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.critical(f"FATAL: Database initialization failed: {e}", exc_info=True)
        # In a real scenario, you might want to force the app to exit if the DB fails
        # For now, logging the critical error is sufficient.

@app.get("/health", status_code=200, tags=["Health"])
async def healthcheck():
    """A simple health check endpoint."""
    return {"status": "ok"}

# Include the main API router
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )