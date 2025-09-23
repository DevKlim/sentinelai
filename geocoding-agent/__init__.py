```

#### `sentinelai/geocoding-agent/models/schemas.py`
```python
# sentinelai/geocoding-agent/models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class GeocodeRequest(BaseModel):
    text_description: str
    area_context: Optional[str] = None

class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    source: str # e.g., "llm-geocoded", "area-cache"

class Area(BaseModel):
    name: str = Field(..., description="Unique name for the area, e.g., 'Disneyland Park'.")
    aliases: List[str] = Field(default=[], description="Alternative names, e.g., 'Disney', 'Magic Kingdom'.")
    latitude: float
    longitude: float
    radius_meters: float = Field(default=500, description="Approximate radius of the area in meters.")
    context_clues: List[str] = Field(default=[], description="List of descriptive clues, e.g., 'near the Matterhorn ride', 'red brick building with a clock'.")
```

#### `sentinelai/geocoding-agent/config/settings.py`
```python
# sentinelai/geocoding-agent/config/settings.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    """
    Pydantic settings for the Geocoding agent.
    Values are automatically read from environment variables.
    """
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8002, env="API_PORT")

    # LLM Provider settings with GEOCODING_ prefix
    llm_provider: str = Field(default="google", env="GEOCODING_LLM_PROVIDER")
    
    google_api_key: Optional[str] = Field(default=None, env="GEOCODING_GOOGLE_API_KEY")
    google_model_name: str = Field(default="gemini-1.5-flash-latest", env="GEOCODING_GOOGLE_MODEL_NAME")

    openai_api_key: Optional[str] = Field(default=None, env="GEOCODING_OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-4o", env="GEOCODING_OPENAI_MODEL_NAME")
    
    openrouter_api_key: Optional[str] = Field(default=None, env="GEOCODING_OPENROUTER_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

settings = Settings()
```

#### `sentinelai/geocoding-agent/services/area_store.py`
```python
# sentinelai/geocoding-agent/services/area_store.py
import json
import os
import logging
from typing import Dict, List, Optional
from threading import RLock
from models.schemas import Area

logger = logging.getLogger(__name__)

# Define paths
SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SERVICE_DIR, '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
AREAS_FILE = os.path.join(DATA_DIR, 'areas.json')

class AreaStore:
    def __init__(self, file_path: str = AREAS_FILE):
        self.file_path = file_path
        self._lock = RLock()
        self._areas: Dict[str, Area] = {} # Keyed by normalized name
        self._alias_map: Dict[str, str] = {} # Maps normalized alias to normalized name
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self._load()

    def _normalize(self, name: str) -> str:
        return name.strip().lower()

    def _load(self):
        with self._lock:
            if not os.path.exists(self.file_path) or os.path.getsize(self.file_path) == 0:
                self._areas = {}
                self._alias_map = {}
                self._save()
                return

            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._areas.clear()
                self._alias_map.clear()
                
                # The file is a dict where keys are the original cased names
                for _, area_data in data.items():
                    area = Area(**area_data)
                    norm_name = self._normalize(area.name)
                    self._areas[norm_name] = area
                    for alias in area.aliases:
                        self._alias_map[self._normalize(alias)] = norm_name
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load areas file from {self.file_path}: {e}")
                self._areas = {}
                self._alias_map = {}

    def _save(self):
        with self._lock:
            try:
                # Save with the original name as the key for readability
                data_to_save = {area.name: area.model_dump() for area in self._areas.values()}
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2)
            except IOError as e:
                logger.error(f"Failed to save areas file to {self.file_path}: {e}")
    
    def get_all_areas(self) -> List[Area]:
        with self._lock:
            return sorted(list(self._areas.values()), key=lambda x: x.name)

    def find_area(self, name: str) -> Optional[Area]:
        with self._lock:
            norm_name = self._normalize(name)
            if norm_name in self._areas:
                return self._areas[norm_name]
            if norm_name in self._alias_map:
                main_name = self._alias_map[norm_name]
                return self._areas.get(main_name)
            return None

    def save_area(self, area: Area) -> Area:
        with self._lock:
            norm_name = self._normalize(area.name)
            
            # Check for conflict: if a different-cased version already exists
            if norm_name in self._areas and self._areas[norm_name].name != area.name:
                raise ValueError(f"An area with the name '{area.name}' but different casing already exists.")
            
            # Remove old aliases if this is an update
            if norm_name in self._areas:
                old_area = self._areas[norm_name]
                for alias in old_area.aliases:
                    self._alias_map.pop(self._normalize(alias), None)
            
            self._areas[norm_name] = area
            for alias in area.aliases:
                self._alias_map[self._normalize(alias)] = norm_name
            
            self._save()
            return area

    def delete_area(self, name: str) -> bool:
        with self._lock:
            area = self.find_area(name)
            if not area:
                return False
            
            norm_name = self._normalize(area.name)
            del self._areas[norm_name]
            for alias in area.aliases:
                self._alias_map.pop(self._normalize(alias), None)
            
            self._save()
            return True

# Singleton instance
area_store = AreaStore()
```

#### `sentinelai/geocoding-agent/agent/geocoding_core.py`
```python
# sentinelai/geocoding-agent/agent/geocoding_core.py
import json
import logging
from typing import Optional

import google.generativeai as genai
from openai import OpenAI

from config.settings import settings
from services.area_store import area_store
from models.schemas import GeocodeResponse

logger = logging.getLogger(__name__)

class GeocodingLLMInterface:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.client = None
        logger.info(f"Geocoding Agent: LLMInterface created for provider: {self.provider}.")

    def _get_client(self):
        if self.client is None:
            self.client = self._initialize_client()
        return self.client

    def _initialize_client(self):
        if self.provider == 'google':
            if not settings.google_api_key: return None
            genai.configure(api_key=settings.google_api_key)
            return genai.GenerativeModel(settings.google_model_name)
        elif self.provider == 'openai' or self.provider == 'openrouter':
            api_key = settings.openrouter_api_key if self.provider == 'openrouter' else settings.openai_api_key
            if not api_key: return None
            base_url = "https://openrouter.ai/api/v1" if self.provider == 'openrouter' else None
            return OpenAI(api_key=api_key, base_url=base_url)
        return None

    def _generate_content(self, prompt: str) -> str:
        client = self._get_client()
        if not client:
            raise RuntimeError(f"Geocoding Agent: LLM client for provider '{self.provider}' could not be initialized.")
        
        try:
            if self.provider == 'google':
                response = client.generate_content(prompt)
                return response.text
            elif self.provider == 'openai' or self.provider == 'openrouter':
                model = settings.openai_model_name
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            raise NotImplementedError(f"Provider '{self.provider}' not implemented.")
        except Exception as e:
            logger.error(f"Error during LLM content generation: {e}")
            raise RuntimeError(f"Could not get response from LLM: {e}")

    def geocode_with_llm(self, text_description: str) -> Optional[GeocodeResponse]:
        prompt = f"""
You are a precision geocoding expert AI. Your task is to analyze a text description of a location and determine its most likely geographic coordinates (latitude and longitude). The description may be vague, contain landmarks, or be a standard address.

**Instructions:**
1.  Read the "Location Description" carefully.
2.  Synthesize all clues to pinpoint the most probable location.
3.  Provide a confidence score between 0.0 (no confidence) and 1.0 (certainty).
4.  Briefly explain your reasoning.
5.  Your response MUST be ONLY a single, valid JSON object with the following keys: "latitude", "longitude", "confidence", "reasoning". Do not include any other text or markdown.

**Location Description:**
---
{text_description}
---

**JSON Output Format:**
{{
  "latitude": <float>,
  "longitude": <float>,
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<string>"
}}
"""
        response_text = ""
        try:
            response_text = self._generate_content(prompt)
            clean_response = response_text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_response)
            return GeocodeResponse(
                latitude=data['latitude'],
                longitude=data['longitude'],
                confidence=data['confidence'],
                reasoning=data['reasoning'],
                source="llm-geocoded"
            )
        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Failed to geocode with LLM. Error: {e}. Raw response: {response_text}")
            return None

class GeocodingAgent:
    def __init__(self):
        self.llm_interface = GeocodingLLMInterface()

    def _normalize(self, text: str) -> str:
        return text.strip().lower()

    def geocode(self, text_description: str) -> Optional[GeocodeResponse]:
        # Step 1: Preprocessing and Area Search
        found_area = None
        norm_desc = self._normalize(text_description)
        for area in area_store.get_all_areas():
            if self._normalize(area.name) in norm_desc:
                found_area = area
                break
            if any(self._normalize(alias) in norm_desc for alias in area.aliases):
                found_area = area
                break
        
        # Step 2: Context Assembly
        enriched_description = text_description
        if found_area:
            logger.info(f"Found matching area: '{found_area.name}'. Enriching context for LLM.")
            context_clues = "; ".join(found_area.context_clues)
            enriched_description = (
                f"The location is likely within or near the '{found_area.name}' area "
                f"(approx. coordinates: {found_area.latitude}, {found_area.longitude}). "
                f"Known landmarks/clues in this area include: [{context_clues}]. "
                f"The specific user-provided description is: '{text_description}'"
            )
        else:
            logger.info("No matching area found. Using raw description for geocoding.")

        # Step 3: LLM Geocoding
        return self.llm_interface.geocode_with_llm(enriched_description)

# Singleton instance
geocoding_agent = GeocodingAgent()
```

#### `sentinelai/geocoding-agent/api/main.py`
```python
# sentinelai/geocoding-agent/api/main.py
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
```

#### `sentinelai/geocoding-agent/api/endpoints.py`
```python
# sentinelai/geocoding-agent/api/endpoints.py
from fastapi import APIRouter, HTTPException, status, Body
from typing import List, Dict, Any

from agent.geocoding_core import geocoding_agent
from services.area_store import area_store
from models.schemas import GeocodeRequest, GeocodeResponse, Area
from config.settings import settings
from agent.geocoding_core import GeocodingLLMInterface

router = APIRouter(prefix="/api/v1", tags=["Geocoding"])

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_text(request: GeocodeRequest):
    """
    Performs context-aware geocoding on a text description.
    """
    result = geocoding_agent.geocode(request.text_description)
    if not result:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get a valid response from the geocoding agent.")
    return result

@router.get("/areas", response_model=List[Area])
async def list_areas():
    """Lists all known geofenced areas."""
    return area_store.get_all_areas()

@router.post("/areas", response_model=Area, status_code=status.HTTP_201_CREATED)
async def create_area(area: Area):
    """Creates a new geofenced area with context clues."""
    try:
        return area_store.save_area(area)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.delete("/areas/{area_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_area(area_name: str):
    """Deletes a known area."""
    if not area_store.delete_area(area_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Area '{area_name}' not found.")
    return

# --- Settings Endpoint ---
@router.get("/settings/env", response_model=dict, tags=["Settings"])
async def get_geocoding_env_settings():
    settings_keys = [
        "GEOCODING_LLM_PROVIDER", "GEOCODING_GOOGLE_API_KEY", "GEOCODING_OPENAI_API_KEY",
        "GEOCODING_OPENROUTER_API_KEY", "GEOCODING_GOOGLE_MODEL_NAME", "GEOCODING_OPENAI_MODEL_NAME"
    ]
    current_settings = {}
    for key in settings_keys:
        value = getattr(settings, key.replace("GEOCODING_", "").lower(), None)
        if "API_KEY" in key and value:
            current_settings[key] = "********"
        else:
            current_settings[key] = value or ""
    return current_settings

@router.post("/settings/env", tags=["Settings"])
async def update_env_settings(payload: dict = Body(...)):
    new_settings = payload.get("settings", {})
    key_map = {
        "GEOCODING_LLM_PROVIDER": "llm_provider",
        "GEOCODING_GOOGLE_API_KEY": "google_api_key",
        "GEOCODING_OPENAI_API_KEY": "openai_api_key",
        "GEOCODING_OPENROUTER_API_KEY": "openrouter_api_key",
        "GEOCODING_GOOGLE_MODEL_NAME": "google_model_name",
        "GEOCODING_OPENAI_MODEL_NAME": "openai_model_name",
    }
    try:
        for key, value in new_settings.items():
            attr_name = key_map.get(key.upper())
            if attr_name and hasattr(settings, attr_name) and value != "********":
                setattr(settings, attr_name, value)
        
        # Re-initialize the agent's LLM interface
        geocoding_agent.llm_interface = GeocodingLLMInterface()
        return {"message": "Geocoding Agent settings updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. System Integration

Here are the changes to integrate the new service into your Docker and NGINX setup.

#### `sentinelai/.env.example`
```
# sentinelai/.env.example
# Rename this file to .env and fill in your secrets

# === PostgreSQL Database (Shared) ===
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=eido_db

# === EIDO Agent LLM Settings ===
EIDO_LLM_PROVIDER="google"
EIDO_GOOGLE_API_KEY=""
EIDO_GOOGLE_MODEL_NAME="gemini-1.5-flash-latest"
EIDO_OPENAI_API_KEY=""
EIDO_OPENAI_MODEL_NAME="gpt-4o"
EIDO_OPENROUTER_API_KEY=""
EIDO_OPENROUTER_MODEL_NAME="google/gemini-flash-1.5"
EIDO_LOCAL_LLM_URL=""

# === IDX Agent LLM Settings ===
IDX_LLM_PROVIDER="google"
IDX_GOOGLE_API_KEY=""
IDX_GOOGLE_MODEL_NAME="gemini-1.5-flash-latest"
IDX_OPENAI_API_KEY=""
IDX_OPENAI_MODEL_NAME="gpt-4o"
IDX_OPENROUTER_API_KEY=""
IDX_OPENROUTER_MODEL_NAME="google/gemini-flash-1.5"
IDX_LOCAL_LLM_URL=""

# === Geocoding Agent LLM Settings ===
GEOCODING_LLM_PROVIDER="google"
GEOCODING_GOOGLE_API_KEY=""
GEOCODING_GOOGLE_MODEL_NAME="gemini-1.5-flash-latest"
GEOCODING_OPENAI_API_KEY=""
GEOCODING_OPENAI_MODEL_NAME="gpt-4o"
GEOCODING_OPENROUTER_API_KEY=""
GEOCODING_OPENROUTER_MODEL_NAME="google/gemini-flash-1.5"

# === Dashboard Settings ===
DASHBOARD_SECRET_KEY="change-this-to-a-long-random-string-for-production" # Used for signing JWT tokens for the settings page