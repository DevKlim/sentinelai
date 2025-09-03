
import os
import json
import logging
from functools import lru_cache
from agent.llm_interface import LLMInterface

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EidoAgent:
    def __init__(self):
        """
        Initializes the EidoAgent, setting up the LLM interface.
        """
        self.llm = LLMInterface()

    def generate_eido_from_scenario(self, event_type: str, scenario_description: str) -> dict:
        """
        Generates an EIDO by filling a template with details from a scenario description.
        """
        if not event_type or not isinstance(event_type, str):
            raise ValueError("event_type must be a non-empty string.")

        filled_eido = self.llm.fill_eido_template(event_type, scenario_description)
        
        return filled_eido
        
    def create_eido_template(self, event_type: str, description: str) -> dict:
        """
        Creates a new EIDO template from a natural language description.
        """
        if not event_type or not isinstance(event_type, str):
            raise ValueError("event_type must be a non-empty string.")

        new_template = self.llm.generate_eido_template_from_description(event_type, description)
        
        return new_template

# Use lru_cache to create a singleton instance of the agent.
@lru_cache()
def get_eido_agent():
    return EidoAgent()
