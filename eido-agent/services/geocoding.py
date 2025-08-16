from geopy.geocoders import Nominatim
from config.settings import settings

def geocode_address(address: str):
    """Geocodes a street address to latitude and longitude."""
    # Ensure a user agent is set, as it's required by Nominatim's policy
    if not settings.geocoding_user_agent or settings.geocoding_user_agent == "your-app-name-here":
        print("Warning: A unique User-Agent for geocoding is not configured. Using a default.")
        user_agent = "sdsc-eido-agent/1.0"
    else:
        user_agent = settings.geocoding_user_agent
        
    geolocator = Nominatim(user_agent=user_agent)
    try:
        location = geolocator.geocode(address)
        if location:
            return {"latitude": location.latitude, "longitude": location.longitude}
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None

def extract_location_from_eido(eido: dict) -> list:
    """
    Extracts location information from an EIDO.
    This is a simplified placeholder. A real implementation would need to parse
    the complex PIDF-LO structures within the EIDO's locationComponent.
    """
    locations = []
    
    # A real implementation would parse the complex EIDO structure,
    # potentially looking for locationComponent and decoding PIDF-LO XML.
    # For this placeholder, we will just use a default location.
    if not locations:
        locations.append({'latitude': 32.7157, 'longitude': -117.1611}) # Default to San Diego
    
    return locations