
import streamlit as st
import httpx
import pandas as pd

IDX_AGENT_URL = "http://idx-agent-api:8001"

def idx_agent_page():
    st.title("IDX Agent")

    st.header("Incidents")

    if st.button("Refresh Incidents"):
        try:
            response = httpx.get(f"{IDX_AGENT_URL}/api/v1/incidents")
            response.raise_for_status()
            incidents = response.json()

            if incidents:
                df = pd.DataFrame(incidents)
                st.dataframe(df)
            else:
                st.info("No incidents found.")

        except httpx.HTTPStatusError as e:
            st.error(f"Error from IDX Agent: {e.response.text}")
        except httpx.RequestError as e:
            st.error(f"Error connecting to IDX Agent: {e}")

if __name__ == "__main__":
    idx_agent_page()
