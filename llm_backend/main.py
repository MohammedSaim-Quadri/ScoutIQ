from fastapi import FastAPI, Request
from pydantic import BaseModel
from prompts import question_prompt, insight_summary_prompt, build_skill_gap_prompt
import requests, os
from dotenv import load_dotenv
import re

load_dotenv()
app = FastAPI()

class Input(BaseModel):
    jd: str
    resume: str

@app.post("/generate")
def generate_questions(data: Input):
    prompt = question_prompt(data.jd, data.resume)
    headers = {
        "Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7,
    }

    response = requests.post("https://api.together.xyz/v1/chat/completions", json=payload, headers=headers)
    try:
        text = response.json()['choices'][0]['message']['content']
        output = clean_response(text)
        return {"result": output}
    except Exception as e:
        return {"error": str(e), "raw": response.text}

@app.post("/insight-summary")
def generate_insight(data: Input):
    prompt = insight_summary_prompt(data.jd,data.resume)
    headers = {
        "Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7,
    }

    response = requests.post("https://api.together.xyz/v1/chat/completions", json=payload, headers=headers)

    try:
        text = response.json()['choices'][0]['message']['content']
        return {"summary": text}
    except Exception as e:
        return {"error": str(e), "raw": response.text}


@app.post("/skill-gap")
def generate_skill_gap(data: Input):
    prompt = build_skill_gap_prompt(data.jd, data.resume)
    headers = {
        "Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.7,
    }

    response = requests.post("https://api.together.xyz/v1/chat/completions", json=payload, headers=headers)
    try:
        text = response.json()['choices'][0]['message']['content']
        return {"skill_gaps": text.strip()}
    except Exception as e:
        return {"error": str(e), "raw": response.text}

def clean_response(raw_output: str):
    # Normalize
    raw_output = raw_output.replace("\\n", "\n").replace("```", "").strip()

    # Split sections using robust regex
    sections = re.split(r"(?i)^\s*(technical questions|behavioral questions|red flag\s*/\s*follow[- ]?up questions)[:：]\s*$", raw_output, flags=re.MULTILINE)

    # We expect: ['', 'Technical Questions', '...questions...', 'Behavioral Questions', '...questions...', ...]
    result = {"technical": [], "behavioral": [], "followup": []}
    
    if len(sections) < 2:
        return result  # fallback in case nothing matched

    label_map = {
        "technical questions": "technical",
        "behavioral questions": "behavioral",
        "red flag / follow-up questions": "followup",
        "red flag/ follow-up questions": "followup",
        "red flag/follow-up questions": "followup",
        "red flag-follow-up questions": "followup",
    }

    for i in range(1, len(sections), 2):
        label = sections[i].strip().lower()
        questions_block = sections[i + 1].strip()
        key = label_map.get(label)
        if not key:
            continue
        questions = re.findall(r"[-•]\s+(.*)", questions_block)
        result[key] = questions

    return result
