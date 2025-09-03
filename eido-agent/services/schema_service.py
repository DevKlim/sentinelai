import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from config.settings import settings
from services.embedding import generate_embedding, get_embedding_dimension, EMBEDDING_ENABLED

logger = logging.getLogger(__name__)

# --- Path Definitions ---
SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SERVICE_DIR, '..'))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'eido_templates')
INDEX_FILE_PATH = os.path.join(SERVICE_DIR, 'eido_schema_index.json')

class SchemaService:
    def __init__(self, index_path: str = INDEX_FILE_PATH, templates_dir: str = TEMPLATES_DIR):
        self.index_path = index_path
        self.templates_dir = templates_dir
        self.rag_index = None
        self.embeddings = None
        self._load_index()
        os.makedirs(self.templates_dir, exist_ok=True)

    def _load_index(self):
        if not os.path.exists(self.index_path):
            logger.error(f"FATAL: RAG index file not found at {self.index_path}. The 'rag_indexer.py' script might have failed during the build.")
            return
        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                self.rag_index = json.load(f)
            # Convert list of lists to a NumPy array for efficient calculations
            self.embeddings = np.array(self.rag_index.get("embeddings", []))
            logger.info(f"Successfully loaded RAG index with {len(self.rag_index.get('chunks', []))} chunks.")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load or parse RAG index file: {e}")
            self.rag_index = None
            self.embeddings = None

    def get_rag_chunks(self) -> List[Dict[str, Any]]:
        if not self.rag_index:
            return []
        return self.rag_index.get("chunks", [])

    def get_documentation_for_component(self, component_name: str) -> str:
        if not self.rag_index:
            return f"Error: RAG index not loaded. Cannot retrieve documentation for '{component_name}'."
        
        for chunk in self.rag_index.get("chunks", []):
            # Find the chunk that matches the component name exactly
            if chunk.get("name", "").lower() == component_name.lower():
                return chunk.get("text", f"Documentation for '{component_name}' not found.")
        
        return f"Component '{component_name}' not found in the documentation index."

    def get_template_for_event_type(self, event_type: str) -> Dict[str, Any]:
        """Loads a base template file to guide the LLM."""
        try:
            return self.get_template(event_type)
        except FileNotFoundError:
            logger.warning(f"Base template '{event_type}' not found. Falling back to 'general_incident.json'.")
            try:
                return self.get_template("general_incident.json")
            except FileNotFoundError:
                logger.error("Fallback template 'general_incident.json' not found. Returning empty dict.")
                return {}

    def list_templates(self) -> List[str]:
        """Returns a list of available .json template filenames."""
        if not os.path.isdir(self.templates_dir):
            return []
        return sorted([f for f in os.listdir(self.templates_dir) if f.endswith('.json')])

    def get_template(self, filename: str) -> Dict[str, Any]:
        """Reads and returns the content of a specific template file."""
        if not filename.endswith('.json'):
            raise ValueError("Invalid filename. Must end with .json")
        
        filepath = os.path.join(self.templates_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Template '{filename}' not found.")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_template(self, filename: str, content: Dict[str, Any]) -> None:
        """Saves content to a new template file."""
        if not filename.endswith('.json'):
            raise ValueError("Invalid filename. Must end with .json")
        
        # Basic security check to prevent path traversal
        if'..' in filename or '/' in filename or '\\' in filename:
            raise ValueError("Invalid filename. Contains illegal characters.")

        filepath = os.path.join(self.templates_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)

    def delete_template(self, filename: str) -> None:
        """Deletes a template file."""
        if not filename.endswith('.json'):
            raise ValueError("Invalid filename. Must end with .json")
        if '..' in filename or '/' in filename or '\\' in filename:
            raise ValueError("Invalid filename. Contains illegal characters.")
            
        filepath = os.path.join(self.templates_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Template '{filename}' not found for deletion.")
        os.remove(filepath)

# Singleton instance
schema_service = SchemaService()