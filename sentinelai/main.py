
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx

app = FastAPI()

EIDO_AGENT_URL = "http://eido_api:8000"
IDX_AGENT_URL = "http://idx-agent:8001"

@app.get("/")
async def health_check():
    return {"status": "online", "service": "sentinel-ai-proxy"}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    target_url = ""
    if path.startswith("eido-agent"):
        target_url = f"{EIDO_AGENT_URL}/{path.replace('eido-agent/', '')}"
    elif path.startswith("idx-agent"):
        target_url = f"{IDX_AGENT_URL}/{path.replace('idx-agent/', '')}"
    else:
        raise HTTPException(status_code=404, detail="Not Found")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=request.headers,
                content=await request.body()
            )
            return response
        except httpx.HTTPStatusError as e:
            return JSONResponse(status_code=e.response.status_code, content=e.response.json())
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Error connecting to the service: {e}")
