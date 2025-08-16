from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from data_models.models import Base  # Import the Base from your models file
from config.settings import settings

# Ensure the DATABASE_URL is loaded and available
if not settings.database_url:
    raise ValueError("FATAL: DATABASE_URL is not configured. Please set it in your .env file.")

# Create an async engine for the database connection
engine = create_async_engine(settings.database_url, echo=False, future=True) # Set echo to False for cleaner logs

# Create a sessionmaker for creating new database sessions
# expire_on_commit=False is recommended for FastAPI with async sessions
SessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# --- FIX: Add the missing init_db function ---
async def init_db():
    """
    Initializes the database by creating all tables defined in the models.
    This function is called once on application startup.
    """
    async with engine.begin() as conn:
        # This will create all tables that inherit from the Base declarative base
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncSession:
    """
    FastAPI dependency to get a database session.
    Ensures the session is always closed after the request.
    """
    async with SessionLocal() as session:
        yield session