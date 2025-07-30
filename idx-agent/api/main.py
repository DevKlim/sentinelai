import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", status_code=200)
async def healthcheck():
    return {"status": "ok"}

app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )