from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import json
from datetime import datetime, timedelta
import os
from typing import Dict, List, Any
from collections import defaultdict

app = FastAPI(title="Sentinel AI Dashboard", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Service URLs
EIDO_API_URL = "http://eido_api:8000"
IDX_API_URL = "http://idx_api:8002"
MAIN_API_URL = "http://api:5000"

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/status")
async def get_status():
    """Get status of all services"""
    services = {
        "eido_api": {"url": f"{EIDO_API_URL}/", "name": "EIDO API"},
        "idx_api": {"url": f"{IDX_API_URL}/health", "name": "IDX API"},
        "main_api": {"url": f"{MAIN_API_URL}/", "name": "Main API"}
    }
    
    status = {}
    async with httpx.AsyncClient() as client:
        for service_id, service in services.items():
            try:
                response = await client.get(service["url"], timeout=5.0)
                status[service_id] = {
                    "name": service["name"],
                    "status": "online" if response.status_code == 200 else "error",
                    "response_time": response.elapsed.total_seconds(),
                    "last_check": datetime.now().isoformat()
                }
            except Exception as e:
                status[service_id] = {
                    "name": service["name"],
                    "status": "offline",
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
    
    return JSONResponse(content=status)

@app.get("/api/analytics/incidents")
async def get_incident_analytics():
    """Get comprehensive incident analytics"""
    try:
        async with httpx.AsyncClient() as client:
            # Get all incidents from EIDO API
            response = await client.get(f"{EIDO_API_URL}/api/v1/incidents", timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch incidents")
            
            incidents = response.json()
            
            # Calculate analytics
            total_incidents = len(incidents)
            active_incidents = len([i for i in incidents if i.get('status', '').lower() == 'active'])
            
            # Incident type distribution
            type_distribution = defaultdict(int)
            for incident in incidents:
                incident_type = incident.get('incident_type', 'Unknown')
                type_distribution[incident_type] += 1
            
            # Time-based analytics (last 24 hours, 7 days, 30 days)
            now = datetime.now()
            last_24h = now - timedelta(days=1)
            last_7d = now - timedelta(days=7)
            last_30d = now - timedelta(days=30)
            
            incidents_24h = 0
            incidents_7d = 0
            incidents_30d = 0
            
            for incident in incidents:
                created_at = incident.get('created_at')
                if created_at:
                    try:
                        incident_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if incident_date >= last_24h:
                            incidents_24h += 1
                        if incident_date >= last_7d:
                            incidents_7d += 1
                        if incident_date >= last_30d:
                            incidents_30d += 1
                    except:
                        pass
            
            # Geographic distribution
            locations = []
            for incident in incidents:
                incident_locations = incident.get('locations', [])
                if incident_locations:
                    for loc in incident_locations:
                        if isinstance(loc, list) and len(loc) == 2:
                            locations.append({
                                'lat': loc[0],
                                'lng': loc[1],
                                'type': incident.get('incident_type', 'Unknown'),
                                'status': incident.get('status', 'Unknown'),
                                'name': incident.get('name', 'Unknown')
                            })
            
            return JSONResponse(content={
                "total_incidents": total_incidents,
                "active_incidents": active_incidents,
                "resolved_incidents": total_incidents - active_incidents,
                "incidents_24h": incidents_24h,
                "incidents_7d": incidents_7d,
                "incidents_30d": incidents_30d,
                "type_distribution": dict(type_distribution),
                "locations": locations,
                "last_updated": datetime.now().isoformat()
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

@app.get("/api/analytics/response-times")
async def get_response_time_analytics():
    """Get response time analytics"""
    try:
        async with httpx.AsyncClient() as client:
            # Get incidents from EIDO API
            response = await client.get(f"{EIDO_API_URL}/api/v1/incidents", timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch incidents")
            
            incidents = response.json()
            
            # Calculate response times (time between creation and last update)
            response_times = []
            for incident in incidents:
                created_at = incident.get('created_at')
                updated_at = incident.get('last_updated_at')
                
                if created_at and updated_at:
                    try:
                        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        response_time = (updated - created).total_seconds() / 60  # in minutes
                        response_times.append(response_time)
                    except:
                        pass
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                min_response_time = min(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = min_response_time = max_response_time = 0
            
            return JSONResponse(content={
                "average_response_time_minutes": round(avg_response_time, 2),
                "min_response_time_minutes": round(min_response_time, 2),
                "max_response_time_minutes": round(max_response_time, 2),
                "total_incidents_analyzed": len(response_times),
                "last_updated": datetime.now().isoformat()
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Response time analytics error: {str(e)}")

@app.get("/api/analytics/trends")
async def get_trend_analytics():
    """Get trend analytics for the last 30 days"""
    try:
        async with httpx.AsyncClient() as client:
            # Get incidents from EIDO API
            response = await client.get(f"{EIDO_API_URL}/api/v1/incidents", timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch incidents")
            
            incidents = response.json()
            
            # Group incidents by day for the last 30 days
            daily_counts = defaultdict(int)
            daily_types = defaultdict(lambda: defaultdict(int))
            
            now = datetime.now()
            for i in range(30):
                date_key = (now - timedelta(days=i)).strftime('%Y-%m-%d')
                daily_counts[date_key] = 0
                daily_types[date_key] = defaultdict(int)
            
            for incident in incidents:
                created_at = incident.get('created_at')
                if created_at:
                    try:
                        incident_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_key = incident_date.strftime('%Y-%m-%d')
                        
                        if date_key in daily_counts:
                            daily_counts[date_key] += 1
                            incident_type = incident.get('incident_type', 'Unknown')
                            daily_types[date_key][incident_type] += 1
                    except:
                        pass
            
            # Convert to sorted lists for charting
            dates = sorted(daily_counts.keys())
            counts = [daily_counts[date] for date in dates]
            
            return JSONResponse(content={
                "daily_counts": {
                    "dates": dates,
                    "counts": counts
                },
                "daily_types": dict(daily_types),
                "last_updated": datetime.now().isoformat()
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend analytics error: {str(e)}")

@app.get("/api/eido/submit", response_class=HTMLResponse)
async def eido_submit_page(request: Request):
    """EIDO report submission page"""
    return templates.TemplateResponse("eido_submit.html", {"request": request})

@app.get("/api/idx/search", response_class=HTMLResponse)
async def idx_search_page(request: Request):
    """IDX search page"""
    return templates.TemplateResponse("idx_search.html", {"request": request})

@app.post("/api/eido/process")
async def process_eido_report(request: Request):
    """Process EIDO report through the API"""
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EIDO_API_URL}/api/v1/process_report",
                json=body,
                timeout=30.0
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/idx/search")
async def search_incidents(request: Request, query: str = ""):
    """Search incidents through IDX API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{IDX_API_URL}/search",
                params={"query": query},
                timeout=10.0
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 