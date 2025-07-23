from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

app = FastAPI()

EIDO_AGENT_URL = "http://eido_api:8000"
IDX_AGENT_URL = "http://idx_api:8001"
LLM_GEOCODING_SERVICE_URL = "http://llm_geocoding_service:8005"

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    target_url = ""
    if path.startswith("eido-agent"):
        target_url = f"{EIDO_AGENT_URL}/{path.replace('eido-agent/', '')}"
    elif path.startswith("idx-agent"):
        target_url = f"{IDX_AGENT_URL}/{path.replace('idx-agent/', '')}"
    elif path.startswith("llm-geocoding-service"):
        target_url = f"{LLM_GEOCODING_SERVICE_URL}/{path.replace('llm-geocoding-service/', '')}"
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
            return StreamingResponse(
                response.aiter_bytes(),
                status_code=response.status_code,
                headers=response.headers
            )
        except httpx.HTTPStatusError as e:
            return JSONResponse(status_code=e.response.status_code, content=e.response.json())
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Error connecting to the service: {e}")