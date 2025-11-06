import firebase_admin
import pandas as pd
from firebase_admin import firestore, credentials
from fastapi import FastAPI, Request, Depends, HTTPException
from pydantic import BaseModel
from llm_backend.prompts import question_prompt, insight_summary_prompt, build_skill_gap_prompt, parse_resume_prompt
import requests, os
from dotenv import load_dotenv
import re
from llm_backend.security import get_current_user, get_admin_user
from langchain_groq import ChatGroq
from llm_backend.models import ParsedResume, Input, ResumeInput
from langchain_qdrant import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from langchain_core.documents import Document
from llm_backend.models import JDInput

load_dotenv()
app = FastAPI()

# --- Initialize Firebase ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase-service-key.json")
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error initializing Firestore: {e}")
    db = None

embeddings_model = None
qdrant_db = None

# --- Initialize LLM ---
try:
    llm = ChatGroq(model="llama-3.3-70b-versatile")
except Exception as e:
    print(f"Error initializing Groq model: {e}")
    llm = None

def get_qdrant():
    """Dependency to lazy-load embeddings and Qdrant client"""
    global embeddings_model, qdrant_db
    
    # This block only runs ONCE, on the first API call
    if qdrant_db is None:
        print("First request: Initializing embeddings and Qdrant...")
        try:
            # 1. THIS IS THE SLOW STEP we moved
            embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            print("Embedding model loaded.")
            
            # 2. This is the network step we moved
            qdrant_client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY"),
                timeout=60
            )
            
            qdrant_db = Qdrant(
                client=qdrant_client,
                collection_name="scoutiq_resumes",
                embeddings=embeddings_model,
            )
            print("Embeddings and Qdrant client initialized successfully.")
        except Exception as e:
            print(f"CRITICAL: Failed to initialize Qdrant/Embeddings: {e}")
            # This will cause the first request to fail, but the server stays alive.
            
    return qdrant_db


@app.post("/generate")
async def generate_questions(data: Input, user: dict = Depends(get_current_user)):
    if not llm:
        return {"error": "LLM not initialized. Check API key.", "raw": ""}
    

    prompt = question_prompt(data.jd, data.resume)

    try:
        # Use LangChain to invoke the model
        response = await llm.ainvoke(prompt)
        # The output from the model is a string. We pass it to your
        # existing clean_response function to parse it.
        text = response.content
        output = clean_response(text)
        return {"result": output}
    except Exception as e:
        return {"error": str(e), "raw": "Failed to get response from LLM"}

    # headers = {
    #     "Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}",
    #     "Content-Type": "application/json"
    # }

    # payload = {
    #     "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    #     "messages": [{"role": "user", "content": prompt}],
    #     "max_tokens": 512,
    #     "temperature": 0.7,
    # }

    # response = requests.post("https://api.together.xyz/v1/chat/completions", json=payload, headers=headers)
    # try:
    #     text = response.json()['choices'][0]['message']['content']
    #     output = clean_response(text)
    #     return {"result": output}
    # except Exception as e:
    #     return {"error": str(e), "raw": response.text}

@app.post("/insight-summary")
async def generate_insight(data: Input, user: dict = Depends(get_current_user)):
    if not llm:
        return {"error": "LLM not initialized.", "raw": ""}
    
    prompt = insight_summary_prompt(data.jd,data.resume)

    try:
        # This endpoint just needs a simple string response
        response = await llm.ainvoke(prompt)
        return {"summary": response.content}
    except Exception as e:
        return {"error": str(e), "raw": "Failed to get response from LLM"}

    # headers = {
    #     "Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}",
    #     "Content-Type": "application/json"
    # }
    # payload = {
    #     "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    #     "messages": [{"role": "user", "content": prompt}],
    #     "max_tokens": 512,
    #     "temperature": 0.7,
    # }

    # response = requests.post("https://api.together.xyz/v1/chat/completions", json=payload, headers=headers)

    # try:
    #     text = response.json()['choices'][0]['message']['content']
    #     return {"summary": text}
    # except Exception as e:
    #     return {"error": str(e), "raw": response.text}


@app.post("/skill-gap")
async def generate_skill_gap(data: Input, user: dict = Depends(get_current_user)):
    if not llm:
        return {"error": "LLM not initialized.", "raw": ""}
    
    prompt = build_skill_gap_prompt(data.jd, data.resume)

    try:
        # This endpoint also just needs a simple string response
        response = await llm.ainvoke(prompt)
        return {"skill_gaps": response.content.strip()}
    except Exception as e:
        return {"error": str(e), "raw": "Failed to get response from LLM"}

    # headers = {
    #     "Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}",
    #     "Content-Type": "application/json"
    # }

    # payload = {
    #     "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    #     "messages": [{"role": "user", "content": prompt}],
    #     "max_tokens": 500,
    #     "temperature": 0.7,
    # }

    # response = requests.post("https://api.together.xyz/v1/chat/completions", json=payload, headers=headers)
    # try:
    #     text = response.json()['choices'][0]['message']['content']
    #     return {"skill_gaps": text.strip()}
    # except Exception as e:
    #     return {"error": str(e), "raw": response.text}

@app.post("/parse-resume", response_model=ParsedResume)
async def parse_resume(data: ResumeInput, user: dict = Depends(get_current_user), qdrant: Qdrant = Depends(get_qdrant)):
    if not llm or not db or not qdrant: 
        raise HTTPException(status_code = 503, detail="LLM not initialized")
    
    structured_llm = llm.with_structured_output(ParsedResume)
    prompt = parse_resume_prompt(data.resume_text)

    try:
        parsed_data = await structured_llm.ainvoke(prompt)
        doc_ref = db.collection("candidates").document()
        doc_ref.set({
            **parsed_data.model_dump(),
            "user_uid": user["uid"],
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Create a text blob to embed
        content_to_embed = f"""
        Name: {parsed_data.full_name}
        Summary: {parsed_data.summary}
        Skills: {', '.join([s.name for s in parsed_data.skills])}
        """

        # Create a LangChain Document
        doc = Document(
            page_content=content_to_embed,
            metadata={
                "firestore_id": doc_ref.id,
                "user_uid": user["uid"],
                "full_name": parsed_data.full_name
            }
        )

        # Add to Qdrant
        await qdrant.aadd_documents([doc], ids=[doc_ref.id])

        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {e}")

@app.post("/rank-candidates")
async def rank_candidates(data: JDInput, user: dict = Depends(get_current_user), qdrant: Qdrant = Depends(get_qdrant)):
    
    if not qdrant or not db:
        raise HTTPException(status_code=503, detail="Database or Vector service not initialized")
    
    try:
        search_results = await qdrant.asimilarity_search(
            data.jd,
            k = 10,
            filter={"must": [{"key": "user_uid", "match": {"value": user["uid"]}}]}
        )

        if not search_results:
            return
        
        firestore_ids = [doc.metadata["firestore_id"] for doc in search_results]
        candidate_refs = [db.collection("candidates").document(fid) for fid in firestore_ids]
        candidate_docs = db.get_all(candidate_refs)

        candidates_data = []
        for doc in candidate_docs:
            if doc.exists:
                candidates_data.append(doc.to_dict())
        
        ordered_candidates = []
        id_to_candidate = {c['full_name']: c for c in candidates_data} # A simple map
        for doc in search_results:
            if doc.metadata["full_name"] in id_to_candidate:
                ordered_candidates.append(id_to_candidate[doc.metadata["full_name"]])

        return ordered_candidates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rank candidates: {e}")

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


@app.get("/admin/usage-logs")
async def get_usage_logs(user: dict = Depends(get_admin_user)):
    try:
        logs_ref = db.collection("usage_logs").stream()
        logs_list = [log.to_dict() for log in logs_ref]
        return logs_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/pro-users")
async def get_pro_users(user: dict = Depends(get_admin_user)):
    try:
        users_ref = db.collection("pro_users").stream()
        users_list = [user.to_dict() for user in users_ref]
        return users_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))