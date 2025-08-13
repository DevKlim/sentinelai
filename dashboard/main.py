from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import httpx
import os
import json
import io
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import random

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# URLs for backend services from environment variables, with defaults for local dev
EIDO_API_URL = os.environ.get("EIDO_API_URL", "http://python-services:8000")
IDX_API_URL = os.environ.get("IDX_API_URL", "http://python-services:8001")


@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """Serves the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/incident/{incident_id}", response_class=HTMLResponse)
async def get_incident_details(request: Request, incident_id: str):
    """Serves the incident details page for a specific incident."""
    try:
        async with httpx.AsyncClient() as client:
            # The EIDO agent is the source of truth for incident data
            response = await client.get(
                f"{EIDO_API_URL}/api/v1/incidents/{incident_id}",
                timeout=30.0
            )
            response.raise_for_status()
            incident_data = response.json()
            
            if not incident_data:
                raise HTTPException(status_code=404, detail="Incident not found")

            return templates.TemplateResponse("incident_details.html", {
                "request": request,
                "incident": incident_data
            })
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/incidents/{incident_id}/close", response_class=JSONResponse)
async def close_incident_endpoint(incident_id: str):
    """Close an incident. Proxies the request to the IDX Agent."""
    try:
        async with httpx.AsyncClient() as client:
            # The close logic is handled by the IDX agent which then calls the EIDO agent
            response = await client.post(
                f"{IDX_API_URL}/api/v1/incidents/{incident_id}/close",
                timeout=30.0
            )
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint for Report Submission (Text or Audio) ---
@app.post("/api/submit_report")
async def submit_report(file: UploadFile = File(...)):
    """
    Proxies a text or audio file to the EIDO agent for processing.
    If it's a text file, it hits the ingest_alert endpoint.
    If it's an audio file, it hits the (future) transcription endpoint.
    """
    content_type = file.content_type
    file_content = await file.read()

    try:
        # For now, we assume text-based report uploads.
        # In the future, we can inspect content_type to decide which EIDO endpoint to call.
        if "text" in content_type or "json" in content_type:
            alert_text = file_content.decode('utf-8')
            payload = {"alert_text": alert_text}
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                # This endpoint on the EIDO agent will create an EIDO and mark it 'uncategorized'
                # The IDX agent will then pick it up for classification.
                response = await client.post(
                    f"{EIDO_API_URL}/api/v1/ingest_alert", 
                    json=payload
                )
                response.raise_for_status()
                return JSONResponse(content=response.json(), status_code=response.status_code)
        else:
            # Placeholder for audio transcription logic
            raise HTTPException(
                status_code=415, # Unsupported Media Type
                detail=f"Unsupported file type: {content_type}. Only text files are currently supported."
            )

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to EIDO Agent: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- New Routes for HTML Pages ---

@app.get("/eido/submit", response_class=HTMLResponse)
async def eido_submit_page(request: Request):
    """Serves the EIDO report submission HTML page."""
    return templates.TemplateResponse("eido_submit.html", {"request": request})

@app.get("/idx/search", response_class=HTMLResponse)
async def idx_search_page(request: Request):
    """Serves the IDX search HTML page."""
    return templates.TemplateResponse("idx_search.html", {"request": request})

# --- New API Endpoints for Incident Management ---

@app.post("/api/incidents/{incident_id}/tags")
async def add_incident_tag(incident_id: str, request: Request):
    """Proxies a request to add a tag to an incident to the EIDO agent."""
    try:
        tag_data = await request.json()  # expecting {"tag": "new_tag"}
        async with httpx.AsyncClient() as client:
            # Assuming EIDO agent has an endpoint to add tags
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

@app.delete("/api/incidents/{incident_id}")
async def delete_incident(incident_id: str):
    """Proxies a request to delete an incident to the EIDO agent."""
    try:
        async with httpx.AsyncClient() as client:
            # Assuming EIDO agent has an endpoint to delete incidents
            response = await client.delete(
                f"{EIDO_API_URL}/api/v1/incidents/{incident_id}",
                timeout=30.0
            )
            response.raise_for_status()
            if response.status_code == 204:
                return JSONResponse(content={"message": "Incident deleted successfully"}, status_code=204)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incidents/{incident_id}/download")
async def download_incident_zip(incident_id: str):
    """Fetches all EIDOs for an incident, zips them, and returns for download."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EIDO_API_URL}/api/v1/incidents/{incident_id}",
                timeout=30.0
            )
            response.raise_for_status()
            incident = response.json()

        reports = incident.get("reports_core_data", [])
        if not reports:
            raise HTTPException(status_code=404, detail="No EIDO reports found for this incident.")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, report in enumerate(reports):
                report_id = report.get("report_id", f"report_{i+1}")
                eido_json = report.get("original_eido_dict")
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

# --- API Endpoints for Dashboard Widgets ---

@app.get("/api/status")
async def get_status():
    """Checks and returns the status of backend services."""
    services = {
        "eido_api": {"url": f"{EIDO_API_URL}/docs", "name": "EIDO API"},
        "idx_api": {"url": f"{IDX_API_URL}/health", "name": "IDX API"},
    }
    status = {}
    async with httpx.AsyncClient() as client:
        for service_id, service in services.items():
            start_time = datetime.now()
            try:
                response = await client.get(service["url"], timeout=5.0)
                response.raise_for_status()
                status[service_id] = {
                    "name": service["name"],
                    "status": "online",
                    "response_time": (datetime.now() - start_time).total_seconds(),
                }
            except Exception as e:
                status[service_id] = {
                    "name": service["name"],
                    "status": "offline",
                    "error": str(e),
                     "response_time": None,
                }
    return JSONResponse(content=status)


@app.get("/api/analytics/incidents")
async def get_incident_analytics():
    """Fetches all incidents and provides basic analytics for the dashboard."""
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
                    except (ValueError, TypeError):
                        pass

            return JSONResponse(content={
                "total_incidents": total_incidents,
                "active_incidents": active_incidents,
                "incidents_24h": incidents_24h,
                "type_distribution": dict(type_distribution),
                "incidents": incidents,
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@app.get("/api/analytics/response-times")
async def get_response_time_analytics():
    """Provides placeholder response time analytics."""
    return JSONResponse(content={
        "average_response_time_minutes": round(random.uniform(5, 20), 1),
        "min_response_time_minutes": round(random.uniform(1, 5), 1),
        "max_response_time_minutes": round(random.uniform(20, 60), 1),
        "total_incidents_analyzed": random.randint(50, 200),
    })
    
@app.get("/api/analytics/trends")
async def get_trends():
    """Provides real incident trend data for the last 30 days."""
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
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if created_at >= start_date:
                        day_str = created_at.strftime('%Y-%m-%d')
                        daily_counts_map[day_str] += 1
                except (ValueError, TypeError):
                    pass

        dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
        counts = [daily_counts_map[day_str] for day_str in dates]

        return JSONResponse(content={"daily_counts": {"dates": dates, "counts": counts}})
    except Exception as e:
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
        dates.reverse()
        counts = [0] * 30
        return JSONResponse(content={"daily_counts": {"dates": dates, "counts": counts}, "error": f"Analytics error: {str(e)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)