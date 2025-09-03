from agent.agent_core import get_eido_agent
# In the future, you could import geocoding services here
# from services.geocoding import geocode_clues

def process_text_alert(scenario_description: str, template_name: str) -> dict:
    """
    High-level function to process a raw text alert using the EidoAgent.
    1. Generates a structured EIDO using the agent's RAG-enhanced LLM call.
    2. (Future) Could perform additional steps like geocoding.
    
    :param scenario_description: The raw text of the alert.
    :param template_name: The EIDO template file to use.
    :return: The generated EIDO dictionary.
    """
    print(f"Processing text alert with template '{template_name}'...")
    
    # Step 1: Use the centralized EidoAgent to generate the EIDO.
    # This ensures the RAG logic is always applied.
    agent = get_eido_agent()
    # FIX: Removed incorrect 'await' for a synchronous function call
    generated_eido = agent.generate_eido_from_template_and_scenario(
        template_name, scenario_description
    )
    
    if not generated_eido or "error" in generated_eido:
        print("EIDO generation failed.")
        return generated_eido if generated_eido else {}

    # Future Enhancement: You could add geocoding logic here.
    # For example:
    # if generated_eido.get("location_description"):
    #     coords = await geocode_clues(generated_eido["location_description"])
    #     generated_eido["location"] = coords

    print("EIDO generated successfully.")
    return generated_eido