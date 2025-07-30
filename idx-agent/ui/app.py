import sys
import os
import streamlit as st

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.eido_service import EidoService

st.title("IDX Agent")

eido_service = EidoService()

# Incident creation
st.header("Create a new incident")
incident_text = st.text_area("Incident Description")
if st.button("Create Incident"):
    if incident_text:
        correlation = eido_service.correlate_incidents(incident_text)
        if correlation["status"] == "new":
            incident = eido_service.create_incident(incident_text)
            st.success(f"New incident created with ID: {incident['id']}")
        else:
            st.warning(f"This incident may be an update to incident: {correlation['correlation_id']}")
    else:
        st.error("Please enter an incident description.")

# Incident list
st.header("Incidents")
incidents = eido_service.get_all_incidents()
for incident in incidents:
    st.write(f"**Incident ID:** {incident['id']}")
    st.write(f"**Description:** {incident['text']}")
    st.write("---")