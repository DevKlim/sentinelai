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
