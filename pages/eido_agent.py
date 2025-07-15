
import streamlit as st
import httpx

EIDO_AGENT_URL = "http://eido-agent-api:8000"

def eido_agent_page():
    st.title("EIDO Agent")

    st.header("Upload Raw Text for EIDO Conversion")
    raw_text = st.text_area("Enter raw text below:", height=200)

    if st.button("Convert to EIDO"):
        if raw_text:
            with st.spinner("Converting to EIDO..."):
                try:
                    response = httpx.post(f"{EIDO_AGENT_URL}/api/v1/ingest/text", json={"text": raw_text})
                    response.raise_for_status()
                    st.success("Successfully converted to EIDO!")
                    st.json(response.json())
                except httpx.HTTPStatusError as e:
                    st.error(f"Error from EIDO Agent: {e.response.text}")
                except httpx.RequestError as e:
                    st.error(f"Error connecting to EIDO Agent: {e}")
        else:
            st.warning("Please enter some text to convert.")

if __name__ == "__main__":
    eido_agent_page()
