import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from data_models.models import Base
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# --- DEFERRED INITIALIZATION ---
engine: create_async_engine = None
SessionLocal: sessionmaker = None

def create_db_engine_and_session():
    """
    Creates the database engine and session factory. This must be called
    during application startup after environment variables are loaded.
    """
    global engine, SessionLocal

    if not settings.database_url:
        raise RuntimeError("FATAL: Database URL is not available in settings at runtime.")

    logger.info(f"Creating database engine for URL (host: ...@{settings.database_url.split('@')[-1]})")

    # The asyncpg driver will handle SSL automatically based on the `sslmode` in the URL.
    # No custom `connect_args` are needed for Neon.
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True
    )

    SessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("Database engine and session factory created successfully.")

async def init_db():
    """
    Initializes the database by creating all tables defined in the models.
    """
    if engine is None:
        raise RuntimeError("Database engine has not been initialized. Call create_db_engine_and_session() first.")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error(f"Error during table creation in init_db: {e}", exc_info=True)
        raise

async def get_db() -> AsyncSession:
    """
    FastAPI dependency to get a database session.
    """
    if SessionLocal is None:
         raise RuntimeError("Database session factory has not been initialized.")
    async with SessionLocal() as session:
        yield session
