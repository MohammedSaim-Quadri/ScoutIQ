import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("📊 Admin Dashboard")

if 'user_info' not in st.session_state or 'id_token' not in st.session_state:
    st.error("You must be logged in to access this page.")
    st.stop()

if not st.session_state.user_info.get("admin"):
    st.error("You do not have permission to view this page.")
    st.stop()

id_token = st.session_state.id_token
headers = {"Authorization": f"Bearer {id_token}"}
BASE_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Refresh button
if st.button("🔄 Refresh Data"):
    st.rerun()

try:
    # === ANALYTICS OVERVIEW ===
    st.header("📈 Analytics Overview (Last 7 Days)")
    overview_resp = requests.get(f"{BASE_BACKEND_URL}/admin/analytics/overview", headers=headers)
    overview_resp.raise_for_status()
    overview = overview_resp.json()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Requests", overview["total_requests"])
    with col2:
        st.metric("Avg Response Time", f"{overview['avg_response_time_seconds']}s")
    with col3:
        st.metric("Success Rate", overview["success_rate"])
    with col4:
        st.metric("Active Users", overview["active_users"])
    
    # Feature usage chart
    if overview.get("feature_usage"):
        st.subheader("Feature Usage Breakdown")
        feature_df = pd.DataFrame(
            overview["feature_usage"].items(),
            columns=["Feature", "Count"]
        )
        fig = px.bar(feature_df, x="Feature", y="Count", title="Most Used Features")
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # === ERROR ANALYTICS ===
    st.header("⚠️ Error Analytics (Last 24 Hours)")
    errors_resp = requests.get(f"{BASE_BACKEND_URL}/admin/analytics/errors", headers=headers)
    errors_resp.raise_for_status()
    errors = errors_resp.json()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Errors", errors["total_errors"])
        if errors.get("errors_by_code"):
            st.json(errors["errors_by_code"])
    
    with col2:
        if errors.get("critical_endpoints"):
            st.warning("🚨 Critical Endpoints (>10 errors)")
            for endpoint in errors["critical_endpoints"]:
                st.write(f"- {endpoint}")
        else:
            st.success("✅ No critical endpoints")
    
    st.markdown("---")
    
    # === USER ANALYTICS ===
    st.header("👥 User Analytics (Last 30 Days)")
    users_resp = requests.get(f"{BASE_BACKEND_URL}/admin/analytics/users", headers=headers)
    users_resp.raise_for_status()
    users = users_resp.json()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Users", users["total_users"])
    with col2:
        st.metric("Pro Users", users["pro_users"])
    with col3:
        st.metric("Conversion Rate", users["conversion_rate"])
    
    # Top users table
    if users.get("top_users"):
        st.subheader("Top 10 Users")
        top_users_df = pd.DataFrame(users["top_users"])
        st.dataframe(top_users_df, use_container_width=True)
    
    st.markdown("---")
    
    # === EMBEDDING STATS ===
    st.header("🔢 Embedding Token Usage")
    embedding_resp = requests.get(f"{BASE_BACKEND_URL}/admin/embedding-stats", headers=headers)
    embedding_resp.raise_for_status()
    embedding = embedding_resp.json()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Tokens Used", f"{embedding['estimated_tokens_used']:,}")
        st.metric("Tokens Remaining", f"{embedding['tokens_remaining']:,}")
    
    with col2:
        st.metric("Percentage Used", embedding["percentage_used"])
        st.info(f"Model: {embedding['model']}")
    
    # Progress bar
    percentage = float(embedding["percentage_used"].rstrip("%"))
    st.progress(percentage / 100)
    
    if percentage > 80:
        st.warning("⚠️ Approaching free tier limit!")
    
    st.markdown("---")
    
    # === PRO USERS TABLE ===
    st.header("💎 Pro Users")
    pro_users_resp = requests.get(f"{BASE_BACKEND_URL}/admin/pro-users", headers=headers)
    pro_users_resp.raise_for_status()
    pro_users_df = pd.DataFrame(pro_users_resp.json())
    
    if not pro_users_df.empty:
        st.dataframe(pro_users_df, use_container_width=True)
        st.metric("Total Pro Users", len(pro_users_df))
    else:
        st.info("No pro users yet")
    
    st.markdown("---")
    
    # === USAGE LOGS TABLE ===
    st.header("📝 Recent Usage Logs")
    usage_logs_resp = requests.get(f"{BASE_BACKEND_URL}/admin/usage-logs", headers=headers)
    usage_logs_resp.raise_for_status()
    usage_logs_df = pd.DataFrame(usage_logs_resp.json())
    
    if not usage_logs_df.empty:
        # Show last 50 logs
        st.dataframe(usage_logs_df.tail(50), use_container_width=True)
    else:
        st.info("No usage logs yet")

except Exception as e:
    st.error(f"Failed to fetch admin data: {e}")
    st.exception(e)