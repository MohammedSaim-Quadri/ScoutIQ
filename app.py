import streamlit as st
from app.ui import is_pro_user
from app import auth_functions as auth
import os
import requests
from streamlit_feedback import streamlit_feedback

st.set_page_config(page_title="ScoutIQ - AI Interview Questions", layout="centered")
BASE_BACKEND_URL = os.getenv("BACKEND_URL", "[http://127.0.0.1:8000](http://127.0.0.1:8000)")

def login_page():
    """
    This function contains the login form logic,
    extracted from the old pages/Recruiter_Mode.py
    """
    st.title("🔐 Log in to ScoutIQ")

    col1, col2, col3 = st.columns([1, 2, 1])
    choice = col2.selectbox("Do you have an account?", ["Yes", "No", "Forgot Password"])

    with col2.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password") if choice in ["Yes", "No"] else ""
        submit = st.form_submit_button("Submit")
    
    # This is the new "Back to Home" for the login page
    st.page_link("app.py", label="⬅️ Back to Home", icon="🏠") 

    if submit:
        if choice == "Yes":
            auth.sign_in(email, password)
        elif choice == "No":
            auth.create_account(email, password)
        elif choice == "Forgot Password":
            auth.reset_password(email)

    if 'auth_success' in st.session_state:
        st.success(st.session_state.auth_success)
        del st.session_state.auth_success
    elif 'auth_warning' in st.session_state:
        st.warning(st.session_state.auth_warning)
        del st.session_state.auth_warning
    # If login is successful, auth.sign_in() will trigger a rerun.
    # On rerun, 'user_info' will be in session_state.

def welcome_page():
    """
    This is the original content from Home.py, shown to logged-out users.
    """
    st.title("Welcome to ScoutIQ!")
    st.subheader("AI-powered Interview Question Generator")
    st.markdown("""
    ScoutIQ helps **founders**, **recruiters**, and **job seekers** instantly generate high-quality, role-specific interview questions using AI.

    ### 🚀 How It Works:
    1. Paste a **Job Description**
    2. Upload or paste a **Candidate Resume**
    3. Get **tailored technical, behavioral, and red flag questions** in seconds!

    ---
    ### 💎 Pricing
    | Tier       | Features                                    |
    |------------|---------------------------------------------|
    [cite_start]| **Free** | 3 generations/month, PDF export             | [cite: 25]
    | **Pro** | Unlimited generations, priority support     |
    
    ---

    ### 🔐 Ready to get started?
    Click below to log in and launch the app.
    """)
    # This button now just goes to the login page
    st.page_link(pg_login, label="Launch ScoutIQ App", icon="💻")
    with st.sidebar:
        st.markdown("👋 Not a Pro user yet?")
        st.page_link(pg_pricing, label="💎 Upgrade to Pro")

def logout_page():
    """A simple page function to log the user out."""
    auth.sign_out()
    st.rerun()

# --- Page Definitions ---
# Define all possible pages in the app using st.Page
pg_welcome = st.Page(welcome_page, title="Home", icon="🏠", default=True)
pg_login = st.Page(login_page, title="Login", icon="🔐")
pg_logout = st.Page(logout_page, title="Logout", icon="👋")
# Point to the new 'app_pages' directory
pg_recruiter = st.Page("app_pages/Recruiter_Mode.py", title="Recruiter Mode", icon="💻")
pg_candidate_db = st.Page("app_pages/Candidate_database.py", title="Candidate Database", icon="🗂️")
pg_job_seeker = st.Page("app_pages/Job_Seeker_mode.py", title="Job Seeker Mode", icon="🚀")
pg_pricing = st.Page("app_pages/Pricing.py", title="Pricing", icon="💎")
pg_admin = st.Page("app_pages/Admin_Dashboard.py", title="Admin Dashboard", icon="📊")

# --- State Check ---
is_logged_in = 'user_info' in st.session_state
user_tier = "free"
is_admin = False

if is_logged_in:
    # FIX 4a: Check for and cache the user tier ONCE
    if 'user_tier' not in st.session_state:
        st.session_state.user_tier = is_pro_user(st.session_state.user_info['email'])
    
    user_tier = st.session_state.get("user_tier", "free")
    
    # FIX :Check for the 'admin' claim from the ID token info,
    # which is stored in st.session_state.user_info
    is_admin = st.session_state.user_info.get("admin") == True

# --- Dynamic Navigation Logic (Fixes Priority 5) ---
if not is_logged_in:
    # User is logged out. Show Home, Login, and Pricing.
    pg = st.navigation([pg_welcome, pg_login, pg_pricing])
else:
    # User is logged in. Build the sidebar dynamically.
    page_map = {
        "ScoutIQ": [pg_recruiter, pg_pricing]
    }

    pro_tools = []
    if user_tier != "free":
        pro_tools.append(pg_candidate_db)
        pro_tools.append(pg_job_seeker)

    if pro_tools:
        page_map["Pro Tools"] = pro_tools

    admin_tools = []
    if is_admin:
        admin_tools.append(pg_admin)

    if admin_tools:
        page_map["Admin"] = admin_tools
    
    # Add logout to the bottom
    page_map["Account"] = [pg_logout]

    # Create the navigation menu
    pg = st.navigation(page_map)

# --- Run the selected page ---
pg.run()