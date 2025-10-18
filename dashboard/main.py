from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
import httpx
import os
import json
import io
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import random
from pydantic import BaseModel
from typing import Dict, Any, Annotated

# Import authentication components
from . import auth
from .auth import User

app = FastAPI()

# Add the /token endpoint to the root of the dashboard app
# This is where a login form would post to get a token.
@app.post("/dashboard/token", response_model=auth.Token, tags=["Authentication"])
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = auth.get_user(form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- FastAPI App Setup ---
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)
templates.env.filters['tojson'] = json.dumps

EIDO_API_URL = os.environ.get("EIDO_API_URL", "http://python-services:8000")
IDX_API_URL = os.environ.get("IDX_API_URL", "http://python-services:8001")
GEOCODING_API_URL = os.environ.get("GEOCODING_API_URL", "http://python-services:8002")

class SettingsUpdate(BaseModel):
    settings: Dict[str, Any]

# --- Public Pages (No Authentication Required) ---
@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/incident/{incident_id}", response_class=HTMLResponse)
async def get_incident_details(request: Request, incident_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EIDO_API_URL}/api/v1/incidents/{incident_id}", timeout=30.0
            )
            response.raise_for_status()
            incident_data = response.json()
            return templates.TemplateResponse("incident_details.html", {
                "request": request,
                "incident": incident_data
            })
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/eido/submit", response_class=HTMLResponse)
async def eido_submit_page(request: Request):
    templates_available = ["general_incident.json", "fire_incident.json", "detailed_incident.json"]
    return templates.TemplateResponse("eido_submit.html", {"request": request, "templates": templates_available})

@app.get("/idx/search", response_class=HTMLResponse)
async def idx_search_page(request: Request):
    return templates.TemplateResponse("idx_search.html", {"request": request})

@app.get("/geocoding", response_class=HTMLResponse)
async def geocoding_page(request: Request):
    return templates.TemplateResponse("geocoding_agent.html", {"request": request})

# --- Public API Endpoints (No Authentication Required) ---
@app.post("/api/submit_report", response_class=JSONResponse)
async def submit_report(
    file: UploadFile = File(...),
    template_name: str = Form("general_incident.json")
):
    """
    Proxies a file to the EIDO agent.
    - If JSON, it's ingested directly.
    - If text, it's used to generate a new EIDO using a template.
    - Other types are rejected.
    """
    content_type = file.content_type
    file_content = await file.read()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            eido_to_ingest = None

            if "json" in content_type:
                # If the file is JSON, it's the EIDO itself.
                eido_to_ingest = json.loads(file_content)
            elif "text" in content_type:
                # If the file is text, generate an EIDO from it.
                gen_url = f"{EIDO_API_URL}/api/v1/generate_eido_from_scenario"
                gen_payload = {
                    "event_type": template_name,
                    "scenario_description": file_content.decode('utf-8')
                }
                response = await client.post(gen_url, json=gen_payload)
                response.raise_for_status()
                eido_to_ingest = response.json().get("generated_eido")
            else:
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported file type: {content_type}. Only JSON and text files are supported."
                )

            if not eido_to_ingest:
                raise HTTPException(status_code=500, detail="Failed to get a valid EIDO object to ingest.")

            # Now, wrap the EIDO object in the required ingest payload format and ingest it.
            ingest_payload = {
                "source": f"dashboard-upload:{file.filename}",
                "original_eido": eido_to_ingest
            }
            ingest_url = f"{EIDO_API_URL}/api/v1/ingest"
            ingest_response = await client.post(ingest_url, json=ingest_payload)
            ingest_response.raise_for_status()
            
            return JSONResponse(content=ingest_response.json(), status_code=ingest_response.status_code)

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to EIDO Agent: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/incidents/{incident_id}", status_code=204)
async def delete_incident(incident_id: str, current_user: User = Depends(auth.get_current_user)):
    """Proxies a request to delete an incident to the EIDO agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{EIDO_API_URL}/api/v1/incidents/{incident_id}",
                timeout=30.0
            )
            response.raise_for_status()
            # DELETE should return 204 No Content on success
            return JSONResponse(content=None, status_code=204)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/incidents/{incident_id}/close", response_class=JSONResponse)
async def close_incident_endpoint(incident_id: str, current_user: User = Depends(auth.get_current_user)):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EIDO_API_URL}/api/v1/incidents/{incident_id}/close", timeout=30.0
            )
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/incidents/{incident_id}/tags")
async def add_incident_tag(incident_id: str, request: Request, current_user: User = Depends(auth.get_current_user)):
    try:
        tag_data = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EIDO_API_URL}/api/v1/incidents/{incident_id}/tags",
                json=tag_data,
                timeout=30.0
            )
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incidents/{incident_id}/download")
async def download_incident_zip(incident_id: str, current_user: User = Depends(auth.get_current_user)):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EIDO_API_URL}/api/v1/incidents/{incident_id}", timeout=30.0
            )
            response.raise_for_status()
            incident = response.json()

        reports = incident.get("reports", [])
        if not reports:
            raise HTTPException(status_code=404, detail="No EIDO reports found for this incident.")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, report in enumerate(reports):
                report_id = report.get("id", f"report_{i+1}")
                eido_json = report.get("original_eido")
                if eido_json:
                    file_name = f"eido_report_{report_id}.json"
                    json_str = json.dumps(eido_json, indent=2)
                    zip_file.writestr(file_name, json_str.encode('utf-8'))

        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=incident_{incident_id}_eidos.zip"}
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    services = {
        "eido_api": {"url": f"{EIDO_API_URL}/health", "name": "EIDO API"},
        "idx_api": {"url": f"{IDX_API_URL}/health", "name": "IDX API"},
        "geocoding_api": {"url": f"{GEOCODING_API_URL}/health", "name": "Geocoding API"},
    }
    status = {}
    async with httpx.AsyncClient() as client:
        for service_id, service in services.items():
            start_time = datetime.now()
            try:
                response = await client.get(service["url"], timeout=5.0)
                response.raise_for_status()
                status[service_id] = {"name": service["name"], "status": "online", "response_time": (datetime.now() - start_time).total_seconds()}
            except Exception as e:
                status[service_id] = {"name": service["name"], "status": "offline", "error": str(e), "response_time": None}
    return JSONResponse(content=status)

@app.get("/api/analytics/incidents")
async def get_incident_analytics():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{EIDO_API_URL}/api/v1/incidents", timeout=10.0)
            response.raise_for_status()
            incidents = response.json()

        total_incidents = len(incidents)
        active_incidents = len([i for i in incidents if i.get('status', '').lower() == 'open'])
        type_distribution = defaultdict(int)
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(days=1)
        incidents_24h = 0
        
        for incident in incidents:
            type_distribution[incident.get('incident_type', 'Unknown')] += 1
            created_at_str = incident.get('created_at')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if created_at > last_24h:
                        incidents_24h += 1
                except (ValueError, TypeError): pass

        return JSONResponse(content={
            "total_incidents": total_incidents,
            "active_incidents": active_incidents,
            "incidents_24h": incidents_24h,
            "type_distribution": dict(type_distribution),
            "incidents": incidents,
        })
    except Exception as e:
        return JSONResponse(content={"error": f"Analytics error: {str(e)}"}, status_code=500)

@app.get("/api/analytics/response-times")
async def get_response_time_analytics():
    return JSONResponse(content={
        "average_response_time_minutes": round(random.uniform(5, 20), 1),
        "min_response_time_minutes": round(random.uniform(1, 5), 1),
        "max_response_time_minutes": round(random.uniform(20, 60), 1),
        "total_incidents_analyzed": random.randint(50, 200),
    })
    
@app.get("/api/analytics/trends")
async def get_trends():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{EIDO_API_URL}/api/v1/incidents", timeout=10.0)
            response.raise_for_status()
            incidents = response.json()

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=29)
        daily_counts_map = defaultdict(int)
        
        for incident in incidents:
            created_at_str = incident.get('created_at')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at.tzinfo is None: created_at = created_at.replace(tzinfo=timezone.utc)
                    if created_at >= start_date:
                        daily_counts_map[created_at.strftime('%Y-%m-%d')] += 1
                except (ValueError, TypeError): pass

        dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
        counts = [daily_counts_map[day_str] for day_str in dates]
        return JSONResponse(content={"daily_counts": {"dates": dates, "counts": counts}})
    except Exception as e:
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
        dates.reverse()
        return JSONResponse(content={"daily_counts": {"dates": dates, "counts": [0]*30}, "error": f"Analytics error: {str(e)}"})

# --- Geocoding Agent Page and API ---

@app.post("/api/geo/geocode")
async def proxy_geocode(request: Request):
    """Proxies geocoding requests to the geocoding agent."""
    payload = await request.json()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{GEOCODING_API_URL}/api/v1/geocode", json=payload, timeout=20.0)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error communicating with Geocoding Agent: {e}")

@app.get("/api/geo/areas")
async def proxy_get_areas(current_user: User = Depends(auth.get_current_user)):
    """Proxies get areas requests to the geocoding agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GEOCODING_API_URL}/api/v1/areas", timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error communicating with Geocoding Agent: {e}")

@app.post("/api/geo/areas")
async def proxy_create_area(request: Request, current_user: User = Depends(auth.get_current_user)):
    """Proxies create area requests to the geocoding agent."""
    payload = await request.json()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{GEOCODING_API_URL}/api/v1/areas", json=payload, timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error communicating with Geocoding Agent: {e}")

@app.delete("/api/geo/areas/{area_name}")
async def proxy_delete_area(area_name: str, current_user: User = Depends(auth.get_current_user)):
    """Proxies delete area requests to the geocoding agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{GEOCODING_API_URL}/api/v1/areas/{area_name}", timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=None, status_code=response.status_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error communicating with Geocoding Agent: {e}")

# --- PROTECTED: Settings Page and API ---

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, current_user: User = Depends(auth.get_current_user)):
    """Serves the main settings page. Requires authentication."""
    return templates.TemplateResponse("settings.html", {"request": request, "user": current_user})

@app.get("/api/settings/{agent}")
async def get_agent_settings(agent: str, current_user: User = Depends(auth.get_current_user)):
    """Proxy to get settings from a specific agent. Requires authentication."""
    if agent == "eido":
        url = f"{EIDO_API_URL}/api/v1/settings/env"
    elif agent == "idx":
        url = f"{IDX_API_URL}/api/v1/settings/env"
    elif agent == "geo":
        url = f"{GEOCODING_API_URL}/api/v1/settings/env"
    else:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to {agent} agent: {e}")

@app.post("/api/settings/{agent}")
async def update_agent_settings(agent: str, payload: SettingsUpdate, current_user: User = Depends(auth.get_current_user)):
    """Proxy to update settings for a specific agent. Requires authentication."""
    if agent == "eido":
        url = f"{EIDO_API_URL}/api/v1/settings/env"
    elif agent == "idx":
        url = f"{IDX_API_URL}/api/v1/settings/env"
    elif agent == "geo":
        url = f"{GEOCODING_API_URL}/api/v1/settings/env"
    else:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    try:
        async with httpx.AsyncClient() as client:
            # The payload is already a Pydantic model, so we send its dictionary representation
            response = await client.post(url, json=payload.model_dump(), timeout=15.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not update settings on {agent} agent: {e}")

@app.get("/api/settings/idx/categorizer/status")
async def get_categorizer_status(current_user: User = Depends(auth.get_current_user)):
    """Proxy to get IDX categorizer status. Requires authentication."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{IDX_API_URL}/api/v1/settings/categorizer/status", timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not get categorizer status from IDX agent: {e}")

@app.post("/api/settings/idx/categorizer/toggle")
async def toggle_categorizer(request: Request, current_user: User = Depends(auth.get_current_user)):
    """Proxy to toggle the IDX categorizer. Requires authentication."""
    body = await request.json()
    enable = body.get('enable')
    if enable is None:
        raise HTTPException(status_code=400, detail="Missing 'enable' parameter.")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{IDX_API_URL}/api/v1/settings/categorizer/toggle", json={"enable": enable}, timeout=15.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not toggle categorizer on IDX agent: {e}")
