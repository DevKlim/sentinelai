
import streamlit as st
import streamlit_authenticator as stauth

# --- USER AUTHENTICATION ---
def get_authenticator():
    # In a real app, you'd load this from a secure source
    users = {
        "usernames": {
            "admin": {
                "name": "Admin User",
                "password": "password123", # In a real app, use hashed passwords
            }
        }
    }
    return stauth.Authenticate(
        users["usernames"],
        "some_cookie_name",
        "some_signature_key",
        cookie_expiry_days=30,
    )

authenticator = get_authenticator()

name, authentication_status, username = authenticator.login("Login", "main")

if st.session_state["authentication_status"]:
    st.session_state.authenticated = True
    st.switch_page("app.py")
elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
