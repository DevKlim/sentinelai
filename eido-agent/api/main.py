import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

from api.endpoints import router as api_router
from config.settings import settings
from database.session import init_db, create_db_engine_and_session

logger = logging.getLogger(__name__)

app = FastAPI(
    title="EIDO Agent API",
    description="API for creating, managing, and processing Emergency Incident Data Objects (EIDO).",
    version="1.0.0",
    lifespan=None # Use startup/shutdown events instead
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def connect_to_db_with_retries():
    """Attempt to connect to the database with retries."""
    retries = 5
    delay = 3
    for i in range(retries):
        try:
            logger.info(f"Attempting to initialize database (Attempt {i+1}/{retries})...")
            create_db_engine_and_session()
            await init_db()
            logger.info("Database initialization successful.")
            return
        except Exception as e:
            if "Name or service not known" in str(e) or "failed to connect" in str(e).lower():
                logger.warning(f"DB connection failed (DNS/Connection Error). Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.critical(f"FATAL: Database initialization failed with a non-recoverable error: {e}", exc_info=True)
                raise
    raise RuntimeError("FATAL: Could not connect to the database after multiple retries.")

@app.on_event("startup")
async def on_startup():
    """Initializes the database when the application starts."""
    logger.info("Application startup: Initializing database connection...")
    
    if not settings.database_url:
        logger.critical("FATAL: DATABASE_URL is not set. The application cannot start.")
        raise RuntimeError("DATABASE_URL must be set for the EIDO agent to run.")
        
    await connect_to_db_with_retries()


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
