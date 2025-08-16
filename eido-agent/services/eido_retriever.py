import logging
import os
import json
from typing import Dict, List, Any

# This file is responsible for retrieving EIDO-related assets, like templates.
# The previous implementation for vector search has been removed as it was
# causing an ImportError and did not appear to be used by the API endpoints.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Correctly resolve the path to the 'eido_templates' directory relative to this file's location.
# __file__ -> /app/eido-agent/services/eido_retriever.py
# os.path.dirname(__file__) -> /app/eido-agent/services
# os.path.join(..., '..') -> /app/eido-agent
# os.path.join(..., 'eido_templates') -> /app/eido-agent/eido_templates
EIDO_TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'eido_templates'))

def get_template(template_name: str) -> Dict | None:
    """
    Loads a specific EIDO JSON template from the 'eido_templates' directory.
    This function was added because it is required by the API but was missing.

    Args:
        template_name: The filename of the template (e.g., "general_incident.json").

    Returns:
        A dictionary representing the template, or None if not found or invalid.
    """
    if not isinstance(template_name, str) or not template_name.endswith('.json'):
        logger.warning(f"Template name '{template_name}' is invalid or does not end with .json.")
        return None

    template_path = os.path.join(EIDO_TEMPLATE_DIR, template_name)
    logger.info(f"Attempting to load EIDO template from: {template_path}")

    if not os.path.exists(template_path):
        logger.error(f"EIDO template file not found at path: {template_path}")
        return None
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        return template_data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading or parsing EIDO template '{template_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting template '{template_name}': {e}", exc_info=True)
        return None