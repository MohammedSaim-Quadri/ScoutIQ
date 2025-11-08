import streamlit as st
import requests
import os
from io import BytesIO
from app.generator import extract_text_from_pdf, extract_text_from_docx
from streamlit_feedback import streamlit_feedback

st.set_page_config(page_title="Job Seeker Mode", layout="centered")
st.title("🚀 ScoutIQ - for Job Seekers")

if 'user_info' not in st.session_state or 'id_token' not in st.session_state:
    st.error("You must be logged in to access this page.")
    st.page_link("pages/Recruiter_Mode.py", label="Log in", icon="🔐")
    st.stop()

if 'user_tier' not in st.session_state:
    # This triggers if they've been logged in, but the session state is old
    # We can try to fetch it, but for now, we'll just ask them to re-log
    st.error("Could not determine user tier. Please return to the main App page and try again.")
    st.page_link("pages/Recruiter_Mode.py", label="Go to App Page", icon="🏠")
    st.stop()

if st.session_state.user_tier == "free":
    st.error("Job Seeker Mode is a Pro feature.")
    st.page_link("pages/Pricing.py", label="💎 Upgrade to Pro to get AI resume feedback.", icon="💎")
    st.stop()

id_token = st.session_state.id_token
headers = {"Authorization": f"Bearer {id_token}"}
BASE_BACKEND_URL = os.getenv("BACKEND_URL", "[http://127.0.0.1:8000](http://127.0.0.1:8000)")

st.info("Paste your resume and a job description to get AI-powered feedback on how to improve it.")

jd_input = st.text_area("📄 Paste Target Job Description", height=200)

resume_text = ""
resume_file = st.file_uploader("Upload Your Resume (PDF or Docx)", type=["pdf", "docx"])

if resume_file:
    file_bytes = BytesIO(resume_file.read())
    if resume_file.name.endswith(".pdf"):
        resume_text = extract_text_from_pdf(file_bytes)
    elif resume_file.name.endswith(".docx"):
        resume_text = extract_text_from_docx(file_bytes)
    st.text_area("Your Resume Text", value=resume_text, height=200)
else:
    resume_text = st.text_area("Or Paste Your Resume Text", height=200)

if st.button("✨ Get Feedback"):
    if jd_input.strip() and resume_text.strip():
        with st.spinner("Analyzing your resume..."):
            try:
                response = requests.post(
                    f"{BASE_BACKEND_URL}/improve-resume",
                    json={"jd": jd_input, "resume": resume_text},
                    headers=headers,
                    timeout=60
                )
                response.raise_for_status()
                feedback = response.json().get("improvements", "No feedback generated.")

                st.subheader("💡 Your Improvement Plan")
                st.markdown(feedback)
            except Exception as e:
                st.error(f"Failed to get feedback: {e}")
    else:
        st.warning("Please provide both a JD and your resume.")

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
    args=("Job Seeker Mode",) # Change this for each page
)