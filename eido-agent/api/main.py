import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints import router as api_router
from config.settings import settings
from database.session import init_db

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
    print("Initializing database...")
    await init_db()
    print("Database initialized.")

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