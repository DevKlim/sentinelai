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
