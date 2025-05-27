import re
import os
import requests
import PyPDF2
import docx
from fpdf import FPDF
from app.prompts import question_prompt
import streamlit as st
OLLAMA_URL = st.secrets.get("OLLAMA_URL", "http://localhost:11434")

def run_prompt_chain(jd_text, resume_text):
    prompt = question_prompt(jd_text, resume_text)
    print("📨 Sending prompt to Mistral...")

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model":st.secrets.get("OLLAMA_MODEL", "llama3.2:1b"),
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        print("✅ Got response from Mistral!")

        data = response.json()
        answer = data.get("message", {}).get("content", "")
        print("🧠 Raw response:\n", answer)

        # Basic parsing based on section headers in the LLM output
        technical, behavioral, red_flags = [], [], []
        current_section = None

        for line in answer.splitlines():
            line = line.strip()

            if "technical" in line.lower() and "question" in line.lower():
                current_section = "technical"
                continue
            elif "behavioral" in line.lower() and "question" in line.lower():
                current_section = "behavioral"
                continue
            elif ("red flag" in line.lower() or "follow-up" in line.lower()) and "question" in line.lower():
                current_section = "red"
                continue
            elif line and current_section:
                if re.match(r"^(\d+[\.\)]|[-•])\s*", line):
                    clean_line = re.sub(r"^(\d+[\.\)]|[-•])\s*", "", line)
                    if current_section == "technical":
                        technical.append(clean_line)
                    elif current_section == "behavioral":
                        behavioral.append(clean_line)
                    elif current_section == "red":
                        red_flags.append(clean_line)

        return {
            "technical": technical,
            "behavioral": behavioral,
            "followup": red_flags
        }

    except Exception as e:
        print(f"LLM Error: {e}")
        return {
            "technical": ["[LLM Error Generating Questions]"],
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