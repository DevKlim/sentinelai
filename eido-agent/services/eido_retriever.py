import logging
import os
import json
import numpy as np
import re
from typing import Dict, List, Any, Optional
from functools import lru_cache
from sentence_transformers.util import cos_sim

# Ensure services and utils are importable
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.embedding import generate_embedding, EMBEDDING_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths relative to this file's location
SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE_PATH = os.path.join(SERVICES_DIR, 'eido_schema_index.json')
EIDO_TEMPLATE_DIR = os.path.abspath(os.path.join(SERVICES_DIR, '..', 'eido_templates'))

class EidoSchemaRetriever:
    def __init__(self, index_path: str = INDEX_FILE_PATH):
        self.index_path = index_path
        self.index_data = None
        self.chunk_embeddings = None
        self._load_index()

    def _load_index(self):
        """Loads the pre-computed schema index from a JSON file."""
        if not EMBEDDING_ENABLED:
            logger.error("Cannot load RAG index because embedding service is disabled.")
            return

        if not os.path.exists(self.index_path):
            logger.error(f"EIDO schema index file not found at: {self.index_path}")
            logger.error("Please run `utils/rag_indexer.py` during the build process to create it.")
            return

        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                self.index_data = json.load(f)
            
            # Convert list of lists to a NumPy array for efficient computation
            self.chunk_embeddings = np.array(self.index_data['embeddings'], dtype=np.float32)
            
            num_chunks = len(self.index_data.get('chunks', []))
            logger.info(f"Successfully loaded EIDO schema index with {num_chunks} chunks.")
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.error(f"Error loading or parsing schema index file '{self.index_path}': {e}")
            self.index_data = None
            self.chunk_embeddings = None

    def retrieve_relevant_chunks(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Finds the most relevant schema/context chunks for a given query text.
        """
        if self.chunk_embeddings is None or self.index_data is None:
            logger.warning("RAG index not loaded, cannot retrieve chunks.")
            return []
        
        if not query_text or not isinstance(query_text, str):
            return []
            
        query_embedding = generate_embedding(query_text)
        if query_embedding is None:
            logger.warning(f"Could not generate embedding for query: '{query_text[:100]}...'")
            return []

        # Reshape query embedding for batch comparison with sentence-transformers utility
        query_embedding_np = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
        
        # Compute cosine similarity
        similarities = cos_sim(query_embedding_np, self.chunk_embeddings)[0] # Get the first (and only) row
        
        # Get the indices of the top_k most similar chunks
        top_k_indices = np.argsort(similarities)[-top_k:][::-1] # Sort descending and take top k
        
        relevant_chunks = []
        for idx in top_k_indices:
            # Create a copy of the chunk data to avoid modifying the original index_data
            chunk_info = self.index_data['chunks'][idx].copy()
            chunk_info['score'] = float(similarities[idx])
            relevant_chunks.append(chunk_info)
            
        logger.info(f"Retrieved {len(relevant_chunks)} chunks for query '{query_text[:50]}...'.")
        return relevant_chunks

@lru_cache()
def get_schema_retriever() -> EidoSchemaRetriever:
    """Provides a singleton instance of the EidoSchemaRetriever."""
    return EidoSchemaRetriever()

def get_template(template_name: str) -> Optional[Dict[str, Any]]:
    """Loads a specific EIDO JSON template from the 'eido_templates' directory."""
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
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading or parsing EIDO template '{template_name}': {e}")
        return None

def list_templates() -> List[str]:
    """Lists all available .json template files in the 'eido_templates' directory."""
    if not os.path.isdir(EIDO_TEMPLATE_DIR):
        logger.error(f"Template directory not found: {EIDO_TEMPLATE_DIR}")
        return []
    try:
        return sorted([f for f in os.listdir(EIDO_TEMPLATE_DIR) if f.endswith('.json')])
    except Exception as e:
        logger.error(f"Error listing templates in {EIDO_TEMPLATE_DIR}: {e}")
        return []

def save_template(filename: str, content: Dict[str, Any]) -> bool:
    """
    Safely saves a new template file, protecting core templates.
    Validates the filename to prevent path traversal.
    """
    # Security: Validate filename to prevent path traversal and ensure it's a JSON file
    if not re.match(r'^[a-zA-Z0-9_.-]+\.json$', filename) or '..' in filename:
        logger.error(f"Invalid or unsafe filename provided: {filename}. Filename must end with .json and contain only alphanumeric, underscore, hyphen, or dot characters.")
        raise ValueError(f"Invalid or unsafe filename provided: {filename}. Filename must end with .json and contain only alphanumeric, underscore, hyphen, or dot characters.")
    
    # Business Rule: Protect the core template from being overwritten.
    if filename == "detailed_incident.json":
        logger.error(f"Attempted to overwrite protected template: {filename}")
        raise ValueError("Overwriting the core 'detailed_incident.json' template is not allowed. Please save with a new name.")
    
    file_path = os.path.join(EIDO_TEMPLATE_DIR, filename)
    try:
        # Ensure the directory exists
        os.makedirs(EIDO_TEMPLATE_DIR, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)
        logger.info(f"Successfully saved template: {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving template {filename}: {e}")
        return False

def delete_template(filename: str) -> bool:
    """
    Safely deletes a template file, protecting core templates.
    """
    # Business Rule: Protect the core template from deletion.
    if filename == "detailed_incident.json":
        logger.warning(f"Attempted to delete protected template: {filename}")
        raise ValueError("Cannot delete the core 'detailed_incident.json' template.")

    # Security: Validate filename to prevent path traversal.
    if not re.match(r'^[a-zA-Z0-9_.-]+\.json$', filename) or '..' in filename:
        logger.error(f"Invalid or unsafe filename for deletion: {filename}")
        return False

    file_path = os.path.join(EIDO_TEMPLATE_DIR, filename)
    
    if not os.path.exists(file_path):
        logger.warning(f"Template to delete not found: {filename}")
        return False # Or True if you consider "already deleted" a success

    try:
        os.remove(file_path)
        logger.info(f"Successfully deleted template: {filename}")
        return True
    except OSError as e:
        logger.error(f"OS error deleting template {filename}: {e}")
        return False