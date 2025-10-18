import json
import logging
from typing import Optional, List, Dict, Any

import google.generativeai as genai
from openai import OpenAI

from config.settings import settings
from models.schemas import GeocodeResponse, AgentStep

logger = logging.getLogger(__name__)

def _safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    """Safely loads JSON from a string, stripping markdown and handling errors."""
    try:
        clean_text = text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Could not decode JSON from LLM response: {text}")
        return None

class GeocodingLLMInterface:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.client = self._initialize_client()
        logger.info(f"Geocoding Agent: LLMInterface initialized for provider: {self.provider}.")

    def _initialize_client(self):
        try:
            if self.provider == 'google':
                if not settings.google_api_key:
                    logger.error("GEOCODING_GOOGLE_API_KEY is not set.")
                    return None
                genai.configure(api_key=settings.google_api_key)
                return genai.GenerativeModel(settings.google_model_name)
            elif self.provider in ['openai', 'openrouter']:
                api_key = settings.openrouter_api_key if self.provider == 'openrouter' else settings.openai_api_key
                if not api_key:
                    logger.error(f"API key for {self.provider} is not set.")
                    return None
                base_url = "https://openrouter.ai/api/v1" if self.provider == 'openrouter' else None
                return OpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            logger.error(f"Failed to initialize LLM client for {self.provider}: {e}")
        return None

    def _generate_content(self, prompt: str, is_json: bool = False) -> str:
        if not self.client:
            raise RuntimeError(f"LLM client for '{self.provider}' is not initialized. Check API keys and configuration.")
        try:
            if self.provider == 'google':
                generation_config = {"response_mime_type": "application/json"} if is_json else None
                response = self.client.generate_content(prompt, generation_config=generation_config)
                return response.text
            elif self.provider in ['openai', 'openrouter']:
                model = settings.openai_model_name
                response_format = {"type": "json_object"} if is_json else {"type": "text"}
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=response_format
                )
                return response.choices[0].message.content
            raise NotImplementedError(f"Provider '{self.provider}' not supported.")
        except Exception as e:
            logger.error(f"LLM content generation failed: {e}")
            raise

    def brainstorm_location_plan(self, description: str) -> Dict:
        prompt = f"""
        You are an AI assistant for emergency dispatch. Your task is to analyze a user's location description and break it down into searchable components.
        The user is located at or near **UC San Diego**.

        User Description: "{description}"

        Based on this, generate a JSON object with:
        1. `search_queries`: A list of 2-3 concise Google Maps search queries to find this location.
        2. `key_landmarks`: A list of keywords representing physical landmarks mentioned or implied.

        Your response must be only a valid JSON object.
        """
        response_text = self._generate_content(prompt, is_json=True)
        plan = _safe_json_loads(response_text)
        if not plan or "search_queries" not in plan:
            raise ValueError("LLM failed to generate a valid brainstorm plan.")
        return plan

    def simulate_web_search(self, query: str) -> str:
        prompt = f"""
        You are a search engine simulator. Given a search query, provide a concise, one-sentence summary of the top result, focusing on location details, address, or defining features relevant to finding it.
        Assume the search is centered around **UC San Diego**.

        Search Query: "{query}"

        Simulated one-sentence summary:
        """
        return self._generate_content(prompt)

    def synthesize_and_geocode(self, original_desc: str, context: str) -> Dict:
        prompt = f"""
        You are a precision geocoding expert. Your task is to synthesize all available information to determine the most likely geographic coordinates (latitude and longitude).

        **Contextual Information:**
        ---
        {context}
        ---

        **Original User Description:** "{original_desc}"

        **Instructions:**
        1. Analyze all information to pinpoint the most probable location.
        2. Your response MUST be ONLY a single, valid JSON object with the following keys:
           - "latitude": <float>
           - "longitude": <float>
           - "confidence": <float between 0.0 and 1.0>
           - "reasoning": "<string, a brief explanation of your conclusion>"
        """
        response_text = self._generate_content(prompt, is_json=True)
        result = _safe_json_loads(response_text)
        if not result or "latitude" not in result:
            raise ValueError("LLM failed to generate valid geocoding synthesis.")
        return result

class GeocodingAgent:
    def __init__(self):
        self.llm_interface = GeocodingLLMInterface()

    def geocode(self, text_description: str) -> Optional[GeocodeResponse]:
        trace: List[AgentStep] = []
        step_num = 1

        # Step 1: Brainstorming & Planning
        plan = {}
        try:
            plan = self.llm_interface.brainstorm_location_plan(text_description)
            trace.append(AgentStep(step_number=step_num, step_name="Brainstorm & Plan", details=f"Extracted landmarks and created search queries.", status="Success", result=plan))
        except Exception as e:
            trace.append(AgentStep(step_number=step_num, step_name="Brainstorm & Plan", details=f"Failed to create plan: {e}", status="Failure"))
            return GeocodeResponse(latitude=0, longitude=0, confidence=0, reasoning="Agent failed at planning stage.", source="llm-agent", agent_trace=trace)
        step_num += 1

        # Step 2: Contextual Search (Simulated)
        search_results = []
        try:
            for query in plan.get("search_queries", []):
                result = self.llm_interface.simulate_web_search(query)
                search_results.append(f"- Query '{query}': {result}")
            details_text = "\n".join(search_results) if search_results else "No search queries were generated."
            trace.append(AgentStep(step_number=step_num, step_name="Simulated Web Search", details="Gathered contextual information from simulated search queries.", status="Success", result={"search_summaries": search_results}))
        except Exception as e:
            trace.append(AgentStep(step_number=step_num, step_name="Simulated Web Search", details=f"Failed during search: {e}", status="Failure"))
            # Continue with what we have
        step_num += 1

        # Step 3: Synthesize & Pinpoint
        try:
            context_for_synthesis = (
                f"The user is at UC San Diego. "
                f"Key landmarks identified: {', '.join(plan.get('key_landmarks', ['N/A']))}. "
                f"Simulated search results:\n{''.join(search_results)}"
            )
            final_geo = self.llm_interface.synthesize_and_geocode(text_description, context_for_synthesis)
            trace.append(AgentStep(step_number=step_num, step_name="Synthesize & Pinpoint", details="Synthesized all information to generate final coordinates and confidence score.", status="Success", result=final_geo))
            return GeocodeResponse(
                latitude=final_geo['latitude'],
                longitude=final_geo['longitude'],
                confidence=final_geo['confidence'],
                reasoning=final_geo['reasoning'],
                source="llm-agent",
                agent_trace=trace
            )
        except Exception as e:
            trace.append(AgentStep(step_number=step_num, step_name="Synthesize & Pinpoint", details=f"Failed to synthesize location: {e}", status="Failure"))
            return GeocodeResponse(latitude=0, longitude=0, confidence=0, reasoning="Agent failed at synthesis stage.", source="llm-agent", agent_trace=trace)

# Singleton instance
geocoding_agent = GeocodingAgent()
