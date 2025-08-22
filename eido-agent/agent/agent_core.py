# file: sentinelai/eido-agent/agent/agent_core.py
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
        Initializes the EidoAgent, setting up the LLM interface and template directory.
        """
        self.llm = LLMInterface()
        # Correctly resolve the path to the 'eido_templates' directory
        self.template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'eido_templates'))
        logger.info(f"EIDO templates directory set to: {self.template_dir}")

    def generate_eido_from_template_and_scenario(self, template_name: str, scenario_description: str) -> dict:
        """
        Generates an EIDO by filling a template with details from a scenario description.

        Args:
            template_name: The filename of the EIDO template (e.g., "general_incident.json").
            scenario_description: The raw text describing the incident.

        Returns:
            A dictionary representing the structured EIDO.

        Raises:
            FileNotFoundError: If the specified template_name does not exist.
            Exception: For errors during LLM processing or JSON parsing.
        """
        if not template_name or not isinstance(template_name, str):
            raise ValueError("template_name must be a non-empty string.")

        template_path = os.path.join(self.template_dir, template_name)
        logger.info(f"Attempting to load template from: {template_path}")

        if not os.path.exists(template_path):
            logger.error(f"Template file not found at path: {template_path}")
            raise FileNotFoundError(f"Template not found at {template_path}")

        try:
            with open(template_path, 'r') as f:
                template_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from template file: {template_path}")
            raise ValueError(f"Invalid JSON in template file: {e}")

        # Call the LLM to populate the template based on the scenario
        filled_eido = self.llm.fill_template(template_data, scenario_description)
        
        return filled_eido

# Use lru_cache to create a singleton instance of the agent.
# This ensures that the agent and its LLM interface are initialized only once.
@lru_cache()
def get_eido_agent():
    return EidoAgent()