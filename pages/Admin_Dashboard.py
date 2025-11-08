# pages/4_Admin_Dashboard.py
import streamlit as st
import requests
import os
import pandas as pd

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("📊 Admin Dashboard")

if 'user_info' not in st.session_state or 'id_token' not in st.session_state:
    st.error("You must be logged in to access this page.")
    st.page_link("pages/Recruiter_Mode.py", label="Log in", icon="🔐")
    st.stop()

# This check happens on the frontend AND backend for security
if st.session_state.user_info.get("email")!= "mohammedsaimquadri@gmail.com":
    st.error("You do not have permission to view this page.")
    st.stop()

id_token = st.session_state.id_token
headers = {"Authorization": f"Bearer {id_token}"}
BASE_BACKEND_URL = os.getenv("BACKEND_URL", "[http://127.0.0.1:8000](http://127.0.0.1:8000)")

try:
    # Fetch Pro Users
    st.subheader("Pro Users")
    pro_users_resp = requests.get(f"{BASE_BACKEND_URL}/admin/pro-users", headers=headers)
    pro_users_resp.raise_for_status()
    pro_users_df = pd.DataFrame(pro_users_resp.json())
    st.dataframe(pro_users_df)

    # Fetch Usage Logs
    st.subheader("Usage Logs")
    usage_logs_resp = requests.get(f"{BASE_BACKEND_URL}/admin/usage-logs", headers=headers)
    usage_logs_resp.raise_for_status()
    usage_logs_df = pd.DataFrame(usage_logs_resp.json())
    st.dataframe(usage_logs_df)

except Exception as e:
    st.error(f"Failed to fetch admin data: {e}")