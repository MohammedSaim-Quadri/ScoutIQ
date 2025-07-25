import re
import os
import requests
import PyPDF2
import docx
from fpdf import FPDF
import streamlit as st

BACKEND_URL = "http://51.21.134.172:8000/generate" 

def run_prompt_chain(jd_text, resume_text):
    #prompt = question_prompt(jd_text, resume_text)
    print("📨 Sending prompt to Llama...")

    try:
        response = requests.post(
            BACKEND_URL,
            json={"jd": jd_text, "resume": resume_text},
            timeout=60
        )

        response.raise_for_status()
        data = response.json()
        print("🧠 Raw backend response:\n", data)
        result = data.get("result", {})

        return {
            "technical": result.get("technical", []),
            "behavioral": result.get("behavioral", []),
            "followup": result.get("followup", [])
        }

    except requests.exceptions.RequestException as e:
        st.error("[LLM Backend Error] Could not generate questions.")
        st.exception(e)
        return {
            "technical": [],
            "behavioral": [],
            "followup": []
        }


def extract_text_from_pdf(file) -> str:
    reader = PyPDF2.PdfReader(file)
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
    pdf.set_font("Arial", size=13)

    def clean_text(text):
        return text.encode("ascii", errors="ignore").decode("ascii")

    def write_section(title, questions):
        pdf.set_font("Arial", 'B', size=13)
        pdf.cell(200, 10, title, ln=True)
        pdf.set_font("Arial", size=13)
        for q in questions:
            cleaned_q = clean_text(q)
            pdf.multi_cell(0, 10, f"{cleaned_q}")
        pdf.ln()

    write_section("Technical Questions", technical)
    write_section("Behavioral Questions", behavioral)
    write_section("Red Flag / Follow-up Questions", followup)

    return pdf.output(dest='S').encode('latin1')