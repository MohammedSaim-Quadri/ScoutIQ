import streamlit as st
st.set_page_config(page_title="ScoutIQ App", layout="centered")
from app.ui import run_ui
from streamlit_feedback import streamlit_feedback
import requests, os

BASE_BACKEND_URL = os.getenv("BACKEND_URL", "[http://127.0.0.1:8000](http://127.0.0.1:8000)")

# The login check is now handled by the main app.py router.
# If we are here, the user is already logged in.
if 'user_info' not in st.session_state:
    st.error("Please log in to access this page.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

# The user_tier is also cached by app.py
if 'user_tier' not in st.session_state:
    st.error("Could not determine user tier. Please log in again.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()
    
# Run the main application UI
run_ui()
    
def send_feedback(feedback_data, page_name):
    # This callback runs when feedback is submitted
    try:
        id_token = st.session_state.id_token
        headers = {"Authorization": f"Bearer {id_token}"}
        response = requests.post(
            f"{BASE_BACKEND_URL}/submit-feedback",
            json={
                "score": feedback_data.get("score"),
                "text": feedback_data.get("text"),
                "page": page_name
            },
            headers=headers
        )
        response.raise_for_status()
        st.toast("Feedback submitted! Thank you.", icon="❤️")
    except Exception as e:
        st.error(f"Failed to submit feedback: {e}")

st.divider()
st.subheader("Was this helpful?")
streamlit_feedback(
    feedback_type="thumbs",
    optional_text_label="Please provide more detail:",
    on_submit=send_feedback,
    args=("Recruiter Mode",) # Change this for each page
)