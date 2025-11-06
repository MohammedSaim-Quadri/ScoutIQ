import streamlit as st
import requests
import os
from io import BytesIO
from app.generator import extract_text_from_pdf, extract_text_from_docx

st.set_page_config(page_title="Job Seeker Mode", layout="centered")
st.title("🚀 ScoutIQ - for Job Seekers")

if 'user_info' not in st.session_state or 'id_token' not in st.session_state:
    st.error("You must be logged in to access this page.")
    st.page_link("pages/App.py", label="Log in", icon="🔐")
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