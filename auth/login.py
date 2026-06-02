import os
import streamlit as st

def require_login():
    if os.getenv("REQUIRE_LOGIN", "true").lower() != "true":
        return

    if st.session_state.get("authenticated", False):
        return

    st.title("Team Access Required")
    st.caption("Sign in with the shared team credential configured in Render environment variables.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    valid_user = os.getenv("TEAM_APP_USERNAME", "team")
    valid_password = os.getenv("TEAM_APP_PASSWORD", "change-me")

    if submitted:
        if username == valid_user and password == valid_password:
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Invalid credentials")

    st.stop()
