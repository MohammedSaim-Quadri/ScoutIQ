import re
import os
import requests
from pypdf import PdfReader
import docx
from fpdf import FPDF
import streamlit as st

#BACKEND_URL = "http://127.0.0.1:8000/generate" #"https://interview-scoutiq.onrender.com/generate" 
BASE_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
BACKEND_URL = f"{BASE_BACKEND_URL}/generate"


def run_prompt_chain(jd_text, resume_text):
    #prompt = question_prompt(jd_text, resume_text)
    print("📨 Sending request..")

    try:

        if 'id_token' not in st.session_state:
            st.error("Authentication token not found. Please log in again")
            return {"technical": [],
                    "behavioral": [],
                    "followup": [],
                    "insight_summary": None,
                    "skill_gaps": None}
        id_token = st.session_state.id_token
        headers = {"Authorization": f"Bearer {id_token}"}

        response = requests.post(
            BACKEND_URL,
            json={"jd": jd_text, "resume": resume_text},
            headers=headers,
            timeout=90
        )

        response.raise_for_status()
        data = response.json()
        print("🧠 Raw backend response:\n", data)
        result = data.get("result", {})

        tier = data.get("tier", "free")
        
        print(f"Response for {tier} tier")

        return {
            "technical": result.get("technical", []),
            "behavioral": result.get("behavioral", []),
            "followup": result.get("followup", []),
            "insight_summary": result.get("insight_summary"),
            "skill_gaps": result.get("skill_gaps")
        }

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            st.error("⏱️ Rate limit reached. Please wait a moment and try again.")
        else:
            st.error(f"❌ Server error: {e.response.status_code}")
        return {
            "technical": [],
            "behavioral": [],
            "followup": [],
            "insight_summary": None,
            "skill_gaps": None
        }
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Please try again.")
        return {
            "technical": [],
            "behavioral": [],
            "followup": [],
            "insight_summary": None,
            "skill_gaps": None
        }
    except requests.exceptions.RequestException as e:
        st.error("❌ Network error. Please check your connection.")
        print(f"Request error: {e}")
        return {
            "technical": [],
            "behavioral": [],
            "followup": [],
            "insight_summary": None,
            "skill_gaps": None
        }

def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def extract_text_from_docx(file) -> str:
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

def generate_pdf(technical, behavioral, followup):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=13)

    # def clean_text(text):
    #     return text.encode("ascii", errors="ignore").decode("ascii")

    def write_section(title, questions):
        pdf.set_font("Helvetica", 'B', size=13)
        pdf.multi_cell(0, 10, title, ln=True)
        pdf.set_font("Helvetica", size=13)
        for q in questions:
            # cleaned_q = clean_text(q)
            pdf.multi_cell(0, 10, f"- {q}", ln=True)
        pdf.ln()

    write_section("Technical Questions", technical)
    write_section("Behavioral Questions", behavioral)
    write_section("Red Flag / Follow-up Questions", followup)

    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, str):  # old fpdf
        pdf_output = pdf_output.encode("latin1")
    elif isinstance(pdf_output, bytearray):  # new fpdf2
        pdf_output = bytes(pdf_output)
    return pdf_output