import streamlit as st
st.set_page_config(page_title="ScoutIQ App", layout="centered")
from app.ui import run_ui
from app import auth_functions as auth
from streamlit_feedback import streamlit_feedback
import requests, os

BASE_BACKEND_URL = os.getenv("BACKEND_URL", "[http://127.0.0.1:8000](http://127.0.0.1:8000)")
def main():

    # 🛡️ If already logged in → show main app
    if 'user_info' in st.session_state:
        run_ui()
        return

    st.title("🔐 Log in to ScoutIQ")

    col1, col2, col3 = st.columns([1, 2, 1])
    choice = col2.selectbox("Do you have an account?", ["Yes", "No", "Forgot Password"])

    with col2.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password") if choice in ["Yes", "No"] else ""
        submit = st.form_submit_button("Submit")
    st.page_link("Home.py", label="⬅️ Back to Home", icon="🏠")
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

if __name__ == "__main__":
    main()
