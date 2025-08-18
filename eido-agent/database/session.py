import os
import ssl
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
    during application startup.
    """
    global engine, SessionLocal

    raw_database_url = os.environ.get("DATABASE_URL")
    if not raw_database_url:
        raise RuntimeError("FATAL: DATABASE_URL environment variable not found at runtime.")

    connect_args = {}
    
    # --- ROBUST SSL HANDLING ---
    # Supabase and other cloud providers require SSL.
    # We will enable it by default for any remote DB connection (not localhost).
    # This avoids relying on '?sslmode=require' which can be easily forgotten in secrets.
    is_remote_db = "localhost" not in raw_database_url and "127.0.0.1" not in raw_database_url
    is_ssl_disabled = "sslmode=disable" in raw_database_url

    if is_remote_db and not is_ssl_disabled:
        # For remote databases, we create a custom SSL context.
        # This is more robust for platforms like Fly.io where standard
        # certificate validation might have issues with internal networking.
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # asyncpg uses the 'ssl' connect_arg with a context object.
        connect_args["ssl"] = ssl_context
        logger.info("Database engine: Remote DB detected. A custom SSL context will be used for the connection.")
    else:
        logger.info("Database engine: Local DB or SSL explicitly disabled. Not using custom SSL context.")

    # settings.database_url is the CLEANED url (without query params) from config/settings.py
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncSession:
    """
    FastAPI dependency to get a database session.
    """
    if SessionLocal is None:
         raise RuntimeError("Database session factory has not been initialized. Call create_db_engine_and_session() first.")
    async with SessionLocal() as session:
        yield session