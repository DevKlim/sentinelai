from fastapi import FastAPI
from api.endpoints import router as api_router

app = FastAPI(
    title="Geocoding Agent API",
    description="API for advanced, context-aware geocoding using LLMs and known areas.",
    version="1.0.0",
)

@app.get("/health", status_code=200, tags=["Health"])
def healthcheck():
    return {"status": "ok"}

app.include_router(api_router)
