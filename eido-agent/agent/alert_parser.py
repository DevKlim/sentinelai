from agent.llm_interface import generate_eido_from_text
# In the future, you could import geocoding services here
# from services.geocoding import geocode_clues

async def process_text_alert(scenario_description: str, template_name: str) -> dict:
    """
    High-level function to process a raw text alert.
    1. Generates a structured EIDO using an LLM.
    2. (Future) Could perform additional steps like geocoding.
    
    :param scenario_description: The raw text of the alert.
    :param template_name: The EIDO template file to use.
    :return: The generated EIDO dictionary.
    """
    print(f"Processing text alert with template '{template_name}'...")
    
    # Step 1: Generate the base EIDO from the text.
    generated_eido = await generate_eido_from_text(scenario_description, template_name)
    
    if not generated_eido:
        print("EIDO generation failed.")
        return {}

    # Future Enhancement: You could add geocoding logic here.
    # For example:
    # if generated_eido.get("location_description"):
    #     coords = await geocode_clues(generated_eido["location_description"])
    #     generated_eido["location"] = coords

    print("EIDO generated successfully.")
    return generated_eido