from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
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
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import traceback

# Attempt to import LLM clients
try:
    import google.generativeai as genai
except ImportError:
    genai = None
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# Load environment variables from a .env file if it exists
load_dotenv()

app = FastAPI()
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)
templates.env.filters['tojson'] = json.dumps

# --- In-memory Configuration Store ---
config = {
    "EIDO_API_URL": os.environ.get("EIDO_API_URL", "http://python-services:8000"),
    "IDX_API_URL": os.environ.get("IDX_API_URL", "http://python-services:8001"),
    "LLM_PROVIDER": os.environ.get("LLM_PROVIDER", "google"),
    "LLM_MODEL": os.environ.get("LLM_MODEL", "gemini-1.5-flash-latest"),
    "LLM_API_KEY": os.environ.get("LLM_API_KEY"),
}
llm_client = None

def initialize_llm_client():
    """Initializes the LLM client based on the current configuration."""
    global llm_client
    provider = config.get("LLM_PROVIDER", "google").lower()
    api_key = config.get("LLM_API_KEY")
    model_name = config.get("LLM_MODEL")

    if not api_key:
        llm_client = None
        print("Dashboard: LLM_API_KEY not found. LLM features will be disabled.")
        return

    try:
        if provider == 'google':
            if not genai:
                raise ImportError("google-generativeai is not installed.")
            genai.configure(api_key=api_key)
            llm_client = genai.GenerativeModel(model_name)
            print(f"Dashboard: Successfully initialized Google Generative AI client for model {model_name}.")
        elif provider == 'openai' or provider == 'openrouter':
            if not OpenAI:
                raise ImportError("openai library is not installed.")
            base_url = "https://openrouter.ai/api/v1" if provider == 'openrouter' else None
            llm_client = OpenAI(api_key=api_key, base_url=base_url)
            print(f"Dashboard: Successfully initialized {provider.title()} client.")
        else:
            llm_client = None
            print(f"Dashboard: Unsupported LLM provider: {provider}")

    except Exception as e:
        llm_client = None
        print(f"Dashboard: Failed to initialize LLM client for provider {provider}: {e}")

async def generate_llm_content(prompt: str) -> str:
    """A wrapper to generate content using the configured LLM client."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM client not configured. Please set up your API key in the Settings page.")

    provider = config.get("LLM_PROVIDER", "").lower()
    model_name = config.get("LLM_MODEL")

    try:
        if provider == 'google':
            response = llm_client.generate_content(prompt)
            return response.text
        elif provider == 'openai' or provider == 'openrouter':
            response = llm_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        else:
            raise HTTPException(status_code=501, detail=f"LLM provider '{provider}' not supported by dashboard.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during LLM processing: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """On application startup, initialize the LLM client."""
    initialize_llm_client()


class SettingsUpdate(BaseModel):
    settings: Dict[str, Any]

class DashboardSettings(BaseModel):
    EIDO_API_URL: str
    IDX_API_URL: str
    LLM_PROVIDER: str = Field(default="google")
    LLM_MODEL: str = Field(default="gemini-1.5-flash-latest")
    LLM_API_KEY: Optional[str] = None

# --- Add Pydantic models for new requests ---
class TemplateCreationRequest(BaseModel):
    description: str

class TemplateSaveRequest(BaseModel):
    filename: str
    content: Dict[str, Any]

# --- Core Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/incident/{incident_id}", response_class=HTMLResponse)
async def get_incident_details(request: Request, incident_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['EIDO_API_URL']}/api/v1/incidents/{incident_id}", timeout=30.0
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

async def ingest_eido(client: httpx.AsyncClient, eido_to_ingest: dict, source: str):
    """Helper function to ingest a single EIDO."""
    ingest_payload = {
        "source": source,
        "original_eido": eido_to_ingest
    }
    ingest_url = f"{config['EIDO_API_URL']}/api/v1/ingest"
    ingest_response = await client.post(ingest_url, json=ingest_payload)
    ingest_response.raise_for_status()
    return ingest_response.json()

@app.post("/api/submit_report", response_class=JSONResponse)
async def submit_report(
    file: UploadFile = File(...),
    template_name: str = Form("detailed_incident.json")
):
    """
    Processes an uploaded file.
    - Tries to ingest it as a single EIDO JSON.
    - If it's a .jsonl file, it processes each line as a separate report.
    - Otherwise, it treats the file as raw text and uses an LLM to find one or more reports.
    """
    file_content = await file.read()
    incident_texts: List[str] = []
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Case 1: Handle as a single, complete EIDO JSON file.
            if file.content_type == "application/json" and not (file.filename and file.filename.endswith(".jsonl")):
                try:
                    eido_to_ingest = json.loads(file_content)
                    result = await ingest_eido(client, eido_to_ingest, f"dashboard-upload:{file.filename}")
                    return JSONResponse(content=result, status_code=200)
                except json.JSONDecodeError:
                    pass  # Fall through to treat as text

            try:
                raw_text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="The uploaded file could not be read as text. Please upload a text-based file.")

            # Case 2: Explicitly handle .jsonl files for reliability
            if file.filename and file.filename.endswith(".jsonl"):
                for line in raw_text.strip().split('\n'):
                    if line.strip():
                        incident_texts.append(line.strip())
            
            # Case 3: For other text files, use LLM to split into reports
            else:
                prompt = f"""
You are an AI data processor. You will receive a block of text which may contain one or more distinct incident reports. Your task is to split this text into individual reports.
Here is the text:
---
{raw_text}
---
Return a JSON object with a single key 'reports', which is a list of strings. Each string in the list should be a complete, distinct incident report. Do not include reports that are empty or just whitespace.
"""
                try:
                    llm_response_text = await generate_llm_content(prompt)
                    clean_response = llm_response_text.strip().replace("```json", "").replace("```", "").strip()
                    split_result = json.loads(clean_response)
                    
                    llm_reports = split_result.get("reports", [])
                    if not isinstance(llm_reports, list):
                        raise ValueError("'reports' key in LLM response is not a list.")

                    incident_texts = [
                        report for report in llm_reports 
                        if isinstance(report, str) and report.strip()
                    ]
                except (json.JSONDecodeError, ValueError) as e:
                    raise HTTPException(status_code=500, detail=f"LLM returned malformed data. Error: {str(e)}")

            if not incident_texts:
                raise HTTPException(status_code=400, detail="Could not identify any valid, non-empty incident reports in the file.")

            # Unified Processing Loop
            gen_url = f"{config['EIDO_API_URL']}/api/v1/generate_eido_from_template"
            results = []
            for i, text in enumerate(incident_texts):
                scenario_description = text
                try:
                    # If the text is a JSON string (from .jsonl), extract transcript
                    report_data = json.loads(text)
                    if isinstance(report_data, dict) and 'Transcript' in report_data:
                        scenario_description = report_data['Transcript']
                except (json.JSONDecodeError, TypeError):
                    # It's plain text from an LLM split, which is fine.
                    pass

                gen_payload = {"template_name": template_name, "scenario_description": scenario_description}
                gen_response = await client.post(gen_url, json=gen_payload)
                gen_response.raise_for_status()
                eido_to_ingest = gen_response.json().get("generated_eido")
                
                if eido_to_ingest:
                    ingest_result = await ingest_eido(client, eido_to_ingest, f"dashboard-bulk-upload:{file.filename}-part-{i+1}")
                    results.append(ingest_result)
            
            return JSONResponse(content={"processed_reports": len(results), "results": results})

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text or f"Received status {e.response.status_code} with no error detail."
        try:
            nested_error = json.loads(error_detail)
            error_message = nested_error.get("detail", error_detail)
        except json.JSONDecodeError:
            error_message = error_detail
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {error_message}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to EIDO Agent: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {type(e).__name__}")


@app.delete("/api/incidents/{incident_id}", status_code=204)
async def delete_incident(incident_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{config['EIDO_API_URL']}/api/v1/incidents/{incident_id}", timeout=30.0
            )
            response.raise_for_status()
            return JSONResponse(content=None, status_code=204)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/incidents/create")
async def create_incident_from_scratch(request: Request):
    """Creates a new, empty incident with just a name."""
    try:
        body = await request.json()
        name = body.get("name")
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Incident name cannot be empty.")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['EIDO_API_URL']}/api/v1/incidents/create",
                json={"name": name},
                timeout=30.0
            )
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/eido/submit", response_class=HTMLResponse)
async def eido_submit_page(request: Request):
    templates_available = ["detailed_incident.json", "general_incident.json", "fire_incident.json"]
    return templates.TemplateResponse("eido_submit.html", {"request": request, "templates": templates_available})

# --- NEW: EIDO Creator Interface and API Endpoints ---

@app.get("/eido/create", response_class=HTMLResponse)
async def eido_creator_page(request: Request):
    """Serves the EIDO Template Creator page."""
    return templates.TemplateResponse("eido_template_creator.html", {"request": request})

@app.get("/api/eido/templates", response_class=JSONResponse)
async def list_eido_templates_proxy():
    """Proxies request to list EIDO templates from the EIDO agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config['EIDO_API_URL']}/api/v1/templates", timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch templates from EIDO Agent: {e}")

@app.get("/api/eido/templates/{filename}", response_class=JSONResponse)
async def get_single_template_proxy(filename: str):
    """Proxies request to get a single EIDO template from the EIDO agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config['EIDO_API_URL']}/api/v1/templates/{filename}", timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch template from EIDO Agent: {e}")

@app.delete("/api/eido/templates/{filename}", status_code=204)
async def delete_single_template_proxy(filename: str):
    """Proxies request to delete a single EIDO template on the EIDO agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{config['EIDO_API_URL']}/api/v1/templates/{filename}", timeout=15.0)
            response.raise_for_status()
            return JSONResponse(content=None, status_code=204)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not delete template on EIDO Agent: {e}")

@app.post("/api/eido/templates/generate", response_class=JSONResponse)
async def generate_eido_template_proxy(request: TemplateCreationRequest):
    """Proxies request to generate a new EIDO template to the EIDO agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['EIDO_API_URL']}/api/v1/templates/generate",
                json={"description": request.description},
                timeout=120.0  # Allow longer timeout for LLM generation
            )
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not generate template from EIDO Agent: {e}")

@app.post("/api/eido/templates/save", response_class=JSONResponse)
async def save_eido_template_proxy(request: TemplateSaveRequest):
    """Proxies request to save a new EIDO template to the EIDO agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['EIDO_API_URL']}/api/v1/templates",
                json={"filename": request.filename, "content": request.content},
                timeout=15.0
            )
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not save template on EIDO Agent: {e}")

@app.get("/api/eido/schema/index", response_class=JSONResponse)
async def get_schema_index_proxy():
    """Proxies the request for the EIDO schema index to the EIDO agent."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config['EIDO_API_URL']}/api/v1/schema/index", timeout=20.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch schema index from EIDO Agent: {e}")

@app.get("/idx/search", response_class=HTMLResponse)
async def idx_search_page(request: Request):
    return templates.TemplateResponse("idx_search.html", {"request": request})

@app.post("/api/incidents/{incident_id}/close", response_class=JSONResponse)
async def close_incident_endpoint(incident_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['EIDO_API_URL']}/api/v1/incidents/{incident_id}/close", timeout=30.0
            )
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/incidents/{incident_id}/tags")
async def add_incident_tag(incident_id: str, request: Request):
    try:
        tag_data = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['EIDO_API_URL']}/api/v1/incidents/{incident_id}/tags",
                json=tag_data,
                timeout=30.0
            )
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/incidents/{incident_id}/rename")
async def rename_incident_endpoint(incident_id: str, request: Request):
    """Endpoint to handle renaming an incident."""
    try:
        body = await request.json()
        new_name = body.get("name")
        if not new_name or not new_name.strip():
            raise HTTPException(status_code=400, detail="New name must not be empty.")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['EIDO_API_URL']}/api/v1/incidents/{incident_id}/rename",
                json={"name": new_name},
                timeout=30.0
            )
            response.raise_for_status()
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incidents/{incident_id}/download")
async def download_incident_zip(incident_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['EIDO_API_URL']}/api/v1/incidents/{incident_id}", timeout=30.0
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

@app.get("/api/incidents/{incident_id}/composite-eido", response_class=JSONResponse)
async def create_composite_eido(incident_id: str):
    # Check for LLM client moved to generate_llm_content
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['EIDO_API_URL']}/api/v1/incidents/{incident_id}", timeout=30.0
            )
            response.raise_for_status()
            incident = response.json()
        eidos_to_process = [report.get("original_eido") for report in incident.get("reports", []) if report.get("original_eido")]
        if not eidos_to_process:
            raise HTTPException(status_code=404, detail="No EIDO reports found for this incident to create a composite.")
        eidos_history_str = json.dumps(eidos_to_process, indent=2)
        prompt = f"""
You are an expert emergency services data analyst. You will be given a list of EIDO (Emergency Incident Data Object) JSONs that all pertain to the same incident, ordered from oldest to newest.
Your task is to analyze all of them and create a single, comprehensive, composite EIDO that summarizes and consolidates the information.
Follow these rules:
1. Use the structure of the first EIDO as a template for the output JSON.
2. Prioritize the most recent and specific information from the list of EIDOs.
3. Combine narratives from the 'notesComponent' of all EIDOs into a single, chronological summary.
4. The final output MUST be a single, valid JSON object and nothing else.
Here is the full history of EIDOs for the incident:
---
{eidos_history_str}
---
Now, generate the single composite EIDO based on the provided history.
"""
        try:
            llm_response_text = await generate_llm_content(prompt)
            clean_response = llm_response_text.strip().replace("```json", "").replace("```", "").strip()
            composite_eido = json.loads(clean_response)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=500, detail=f"LLM returned malformed JSON data. Error: {str(e)}\nRaw Response: {llm_response_text}")

        return JSONResponse(content=composite_eido, status_code=200)

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected internal error occurred: {str(e)}")

@app.get("/api/status")
async def get_status():
    services = {
        "eido_api": {"url": f"{config['EIDO_API_URL']}/health", "name": "EIDO API"},
        "idx_api": {"url": f"{config['IDX_API_URL']}/health", "name": "IDX API"},
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
            response = await client.get(f"{config['EIDO_API_URL']}/api/v1/incidents", timeout=10.0)
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
                    if created_at.tzinfo is None: created_at = created_at.replace(tzinfo=timezone.utc)
                    if created_at > last_24h: incidents_24h += 1
                except (ValueError, TypeError): pass
        return JSONResponse(content={
            "total_incidents": total_incidents, "active_incidents": active_incidents,
            "incidents_24h": incidents_24h, "type_distribution": dict(type_distribution),
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
            response = await client.get(f"{config['EIDO_API_URL']}/api/v1/incidents", timeout=10.0)
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

# --- Settings Page and API ---

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/api/settings/dashboard", response_model=DashboardSettings)
async def get_dashboard_settings():
    """Gets current dashboard-level settings."""
    masked_key = config.get("LLM_API_KEY")
    if masked_key:
        masked_key = "********"
    return {
        "EIDO_API_URL": config["EIDO_API_URL"],
        "IDX_API_URL": config["IDX_API_URL"],
        "LLM_PROVIDER": config.get("LLM_PROVIDER"),
        "LLM_MODEL": config.get("LLM_MODEL"),
        "LLM_API_KEY": masked_key
    }

async def push_settings_to_agent(agent: str, settings_to_push: dict):
    """Helper function to push settings to a backend agent."""
    if agent == "eido": url = f"{config['EIDO_API_URL']}/api/v1/settings/env"
    elif agent == "idx": url = f"{config['IDX_API_URL']}/api/v1/settings/env"
    else: return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"settings": settings_to_push}, timeout=15.0)
            response.raise_for_status()
        print(f"Successfully pushed settings to {agent} agent.")
    except Exception as e:
        print(f"Warning: Could not push settings to {agent} agent: {e}")

@app.post("/api/settings/dashboard", response_model=dict)
async def update_dashboard_settings(new_settings: DashboardSettings):
    """Updates dashboard-level settings, re-initializes clients, and propagates to agents."""
    global config
    config["EIDO_API_URL"] = new_settings.EIDO_API_URL
    config["IDX_API_URL"] = new_settings.IDX_API_URL
    config["LLM_PROVIDER"] = new_settings.LLM_PROVIDER
    config["LLM_MODEL"] = new_settings.LLM_MODEL

    # Update dashboard's own LLM client
    if new_settings.LLM_API_KEY and new_settings.LLM_API_KEY != "********":
        config["LLM_API_KEY"] = new_settings.LLM_API_KEY
    initialize_llm_client()

    # --- FIX: Propagate LLM settings to agents ---
    if new_settings.LLM_API_KEY and new_settings.LLM_API_KEY != "********":
        common_api_key = new_settings.LLM_API_KEY
        common_provider = new_settings.LLM_PROVIDER
        common_model = new_settings.LLM_MODEL

        # Prepare settings for EIDO agent
        eido_settings = {
            "EIDO_LLM_PROVIDER": common_provider,
            "EIDO_GOOGLE_MODEL_NAME": common_model,
            "EIDO_OPENAI_MODEL_NAME": common_model,
            "EIDO_OPENROUTER_MODEL_NAME": common_model,
            "EIDO_GOOGLE_API_KEY": common_api_key,
            "EIDO_OPENAI_API_KEY": common_api_key,
            "EIDO_OPENROUTER_API_KEY": common_api_key,
        }
        await push_settings_to_agent("eido", eido_settings)

        # Prepare settings for IDX agent
        idx_settings = {
            "IDX_LLM_PROVIDER": common_provider,
            "IDX_GOOGLE_MODEL_NAME": common_model,
            "IDX_OPENAI_MODEL_NAME": common_model,
            "IDX_OPENROUTER_MODEL_NAME": common_model,
            "IDX_GOOGLE_API_KEY": common_api_key,
            "IDX_OPENAI_API_KEY": common_api_key,
            "IDX_OPENROUTER_API_KEY": common_api_key,
        }
        await push_settings_to_agent("idx", idx_settings)
        
        return {"message": "Dashboard settings updated and propagated to agents successfully."}

    return {"message": "Dashboard settings updated successfully."}


@app.get("/api/settings/agent/{agent}")
async def get_agent_settings(agent: str):
    if agent == "eido": url = f"{config['EIDO_API_URL']}/api/v1/settings/env"
    elif agent == "idx": url = f"{config['IDX_API_URL']}/api/v1/settings/env"
    else: raise HTTPException(status_code=404, detail="Agent not found")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to {agent} agent: {e}")

@app.post("/api/settings/agent/{agent}")
async def update_agent_settings(agent: str, payload: SettingsUpdate):
    if agent == "eido": url = f"{config['EIDO_API_URL']}/api/v1/settings/env"
    elif agent == "idx": url = f"{config['IDX_API_URL']}/api/v1/settings/env"
    else: raise HTTPException(status_code=404, detail="Agent not found")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload.dict(), timeout=15.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not update settings on {agent} agent: {e}")

@app.get("/api/settings/idx/categorizer/status")
async def get_categorizer_status():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config['IDX_API_URL']}/api/v1/settings/categorizer/status", timeout=10.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not get categorizer status from IDX agent: {e}")

@app.post("/api/settings/idx/categorizer/toggle")
async def toggle_categorizer(request: Request):
    body = await request.json()
    enable = body.get('enable')
    if enable is None: raise HTTPException(status_code=400, detail="Missing 'enable' parameter.")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{config['IDX_API_URL']}/api/v1/settings/categorizer/toggle", json={"enable": enable}, timeout=15.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not toggle categorizer on IDX agent: {e}")
        
# --- EIDO Management Page and API ---

@app.get("/eido/manage", response_class=HTMLResponse)
async def eido_management_page(request: Request):
    active_incidents = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config['EIDO_API_URL']}/api/v1/incidents?status=open", timeout=10.0)
            response.raise_for_status()
            active_incidents = response.json()
    except Exception as e:
        print(f"Could not fetch active incidents for EIDO management page: {e}")
    
    return templates.TemplateResponse("eido_management.html", {
        "request": request,
        "active_incidents": active_incidents
    })

@app.get("/api/eidos")
async def get_all_eidos_proxy(status: Optional[str] = None):
    try:
        params = {"status": status} if status else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config['EIDO_API_URL']}/api/v1/eidos", params=params, timeout=30.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/eidos/bulk-actions")
async def eido_bulk_actions_proxy(request: Request):
    try:
        payload = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{config['EIDO_API_URL']}/api/v1/eidos/bulk-actions", json=payload, timeout=60.0)
            response.raise_for_status()
            return JSONResponse(content=response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/eidos/{eido_id}", status_code=204)
async def delete_single_eido_proxy(eido_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{config['EIDO_API_URL']}/api/v1/eidos/{eido_id}", timeout=15.0)
            response.raise_for_status()
            return JSONResponse(content=None, status_code=204)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from EIDO Agent: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))