from agent.llm_interface import extract_geolocatable_clues, geocode_address_with_llm
from services.local_geocoder import LocalGeocoder # Assuming local_geocoder provides a simple geocoder

class AdvancedGeocodingService:
    """
    A service that combines multiple geocoding strategies.
    1. Extracts location clues from text using an LLM.
    2. Tries to geocode clues using a fast, local geocoder.
    3. Falls back to a more powerful (but slower) LLM-based geocoder if needed.
    """
    def __init__(self):
        self.local_geocoder = LocalGeocoder()
        print("Advanced Geocoding Service Initialized.")

    async def geocode_text_to_coordinates(self, text: str) -> dict | None:
        """
        Takes raw text and attempts to find the single best lat/lon coordinate pair.
        """
        if not text:
            return None

        # Step 1: Extract potential location clues from the text
        clues = await extract_geolocatable_clues(text)
        if not clues:
            print("No geolocatable clues found in text.")
            return None
        
        print(f"Found clues: {clues}")

        # Step 2: Try the fast, local geocoder first on each clue
        for clue in clues:
            local_coords = self.local_geocoder.geocode(clue)
            if local_coords:
                print(f"Local geocoder succeeded for clue: '{clue}'")
                return local_coords
        
        # Step 3: If local fails, fall back to the powerful LLM geocoder
        print("Local geocoder failed, falling back to LLM geocoding.")
        # We'll use the first (often best) clue for the LLM call to save tokens
        llm_coords = await geocode_address_with_llm(clues[0])
        if llm_coords:
            print(f"LLM geocoder succeeded for clue: '{clues[0]}'")
            return llm_coords
            
        print("All geocoding attempts failed.")
        return None

# --- Singleton Pattern for the service ---
advanced_geocoder_service_instance = AdvancedGeocodingService()

def get_advanced_geocoding_service():
    """Returns the singleton instance of the geocoding service."""
    return advanced_geocoder_service_instance