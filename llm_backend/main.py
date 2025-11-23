import firebase_admin
import pandas as pd
from firebase_admin import firestore, credentials
from fastapi import FastAPI, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from llm_backend.prompts import question_prompt, insight_summary_prompt, build_skill_gap_prompt, parse_resume_prompt, job_seeker_prompt
import requests, os
from dotenv import load_dotenv
import re
from llm_backend.security import get_current_user, get_admin_user
from langchain_groq import ChatGroq
from llm_backend.models import ParsedResume, Input, ResumeInput
from langchain_qdrant import Qdrant
from langchain_community.embeddings import VoyageEmbeddings
from qdrant_client import QdrantClient
from langchain_core.documents import Document
from llm_backend.models import JDInput
from contextlib import asynccontextmanager

load_dotenv()

# --- Initialize Globals (will be populated during lifespan) ---
db = None
llm = None
embeddings_model = None
qdrant_db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === RUNS ON STARTUP ===
    global db, llm, embeddings_model, qdrant_db
    print("Startup Event: Initializing services...")

    # Initialize Firebase
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase-service-key.json")
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Startup: Firebase initialized.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Firestore: {e}")

    # Initialize LLM
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile")
        print("Startup: Groq LLM initialized.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Groq model: {e}")

    # Initialize Embeddings & Qdrant (The slow part)
    try:
        print("Startup: Loading embedding model...")
        embeddings_model = VoyageEmbeddings(
            model = "voyage-3.5-lite",
            voyage_api_key = os.getenv("VOYAGE_API_KEY")
        )
        print("Startup: Embedding model loaded.")

        print("Startup: Connecting to Qdrant...")
        qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            timeout=60
        )
        qdrant_db = Qdrant(
            client=qdrant_client,
            collection_name="scoutiq_resumes_v2",
            embeddings=embeddings_model,
        )
        print("Startup: Qdrant client initialized successfully.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Qdrant/Embeddings: {e}")

    print("Startup complete. Server is ready.")
    yield
    # === RUNS ON SHUTDOWN (optional) ===
    print("Shutdown Event: Cleaning up...")

# --- Pass lifespan to the FastAPI app ---
app = FastAPI(lifespan=lifespan)

class FeedbackInput(BaseModel):
    score: str
    text: Optional[str] = None
    page: str

def get_db():
    if db is None:
        raise HTTPException(status_code=503, detail="Firestore not initialized")
    return db

def get_llm():
    if llm is None:
        raise HTTPException(status_code=503, detail="LLM not initialized")
    return llm

def get_qdrant():
    if qdrant_db is None:
        raise HTTPException(status_code=503, detail="Vector DB not initialized")
    return qdrant_db

# --- API Endpoints ---

@app.post("/generate")
async def generate_questions(data: Input, user: dict = Depends(get_current_user), llm: ChatGroq = Depends(get_llm)):
    prompt = question_prompt(data.jd, data.resume)
    try:
        response = await llm.ainvoke(prompt)
        text = response.content
        output = clean_response(text)
        return {"result": output}
    except Exception as e:
        return {"error": str(e), "raw": "Failed to get response from LLM"}

@app.post("/insight-summary")
async def generate_insight(data: Input, user: dict = Depends(get_current_user), llm: ChatGroq = Depends(get_llm)):
    prompt = insight_summary_prompt(data.jd,data.resume)
    try:
        response = await llm.ainvoke(prompt)
        return {"summary": response.content}
    except Exception as e:
        return {"error": str(e), "raw": "Failed to get response from LLM"}

@app.post("/skill-gap")
async def generate_skill_gap(data: Input, user: dict = Depends(get_current_user), llm: ChatGroq = Depends(get_llm)):
    prompt = build_skill_gap_prompt(data.jd, data.resume)
    try:
        response = await llm.ainvoke(prompt)
        return {"skill_gaps": response.content.strip()}
    except Exception as e:
        return {"error": str(e), "raw": "Failed to get response from LLM"}

@app.post("/parse-resume", response_model=ParsedResume)
async def parse_resume(data: ResumeInput, user: dict = Depends(get_current_user), 
                       qdrant: Qdrant = Depends(get_qdrant), 
                       llm: ChatGroq = Depends(get_llm),
                       db: firestore.Client = Depends(get_db)):
    
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

        content_to_embed = f"""
        Name: {parsed_data.full_name}
        Summary: {parsed_data.summary}
        Skills: {', '.join([s.name for s in parsed_data.skills])}
        """

        doc = Document(
            page_content=content_to_embed,
            metadata={
                "firestore_id": doc_ref.id,
                "user_uid": user["uid"],
                "full_name": parsed_data.full_name
            }
        )

        await qdrant.aadd_documents([doc], ids=[doc_ref.id])
        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {e}")

@app.post("/rank-candidates")
async def rank_candidates(data: JDInput, user: dict = Depends(get_current_user), 
                          qdrant: Qdrant = Depends(get_qdrant),
                          db: firestore.Client = Depends(get_db)):
    
    try:
        search_results = await qdrant.asimilarity_search(
            data.jd,
            k = 10,
            filter={"must": [{"key": "user_uid", "match": {"value": user["uid"]}}]}
        )

        if not search_results:
            return []
        
        firestore_ids = [doc.metadata["firestore_id"] for doc in search_results]
        candidate_refs = [db.collection("candidates").document(fid) for fid in firestore_ids]
        candidate_docs = db.get_all(candidate_refs)

        candidates_data = []
        for doc in candidate_docs:
            if doc.exists:
                candidates_data.append(doc.to_dict())
        
        ordered_candidates = []
        # Create a map based on firestore_id for accurate ordering
        id_to_candidate = {c.id: c.to_dict() for c in candidate_docs if c.exists}
        
        for doc in search_results:
            fs_id = doc.metadata["firestore_id"]
            if fs_id in id_to_candidate:
                ordered_candidates.append(id_to_candidate[fs_id])

        return ordered_candidates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rank candidates: {e}")

@app.post("/improve-resume")
async def improve_resume(data: Input, user: dict = Depends(get_current_user), llm: ChatGroq = Depends(get_llm)):
    prompt = job_seeker_prompt(data.jd, data.resume)
    try:
        response = await llm.ainvoke(prompt)
        return {"improvements": response.content}
    except Exception as e:
        return {"error": str(e), "raw": "Failed to get response from LLM"}

def clean_response(raw_output: str):
    raw_output = raw_output.replace("\\n", "\n").replace("```", "").strip()
    sections = re.split(r"(?i)^\s*(technical questions|behavioral questions|red flag\s*/\s*follow[- ]?up questions)[::]\s*$", raw_output, flags=re.MULTILINE)
    result = {"technical": [], "behavioral": [], "followup": []}
    
    if len(sections) < 2:
        return result

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
async def get_usage_logs(user: dict = Depends(get_admin_user), db: firestore.Client = Depends(get_db)):
    try:
        logs_ref = db.collection("usage_logs").stream()
        logs_list = [log.to_dict() for log in logs_ref]
        return logs_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/admin/embedding-stats")
async def get_embedding_stats(
    user: dict = Depends(get_admin_user),
    db: firestore.Client = Depends(get_db)
):
    """
    Track how many tokens you've used for embeddings
    Helps you monitor your 200M free token limit
    """
    try:
        # Query Firestore for all embedding operations
        logs = db.collection("usage_logs").stream()
        
        total_resumes_parsed = 0
        total_searches = 0
        
        for log in logs:
            data = log.to_dict()
            if data.get("has_insights"):  # Pro users who parsed resumes
                total_resumes_parsed += 1
            # Add search tracking if you implement it
        
        # Estimate token usage (rough calculation)
        avg_resume_tokens = 800
        avg_search_tokens = 400
        
        estimated_tokens = (
            total_resumes_parsed * avg_resume_tokens +
            total_searches * avg_search_tokens
        )
        
        free_tier_limit = 200_000_000  # 200M tokens
        percentage_used = (estimated_tokens / free_tier_limit) * 100
        
        return {
            "total_resumes_parsed": total_resumes_parsed,
            "total_searches": total_searches,
            "estimated_tokens_used": estimated_tokens,
            "free_tier_limit": free_tier_limit,
            "percentage_used": f"{percentage_used:.2f}%",
            "tokens_remaining": free_tier_limit - estimated_tokens,
            "model": "voyage-3.5-lite"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/pro-users")
async def get_pro_users(user: dict = Depends(get_admin_user), db: firestore.Client = Depends(get_db)):
    try:
        users_ref = db.collection("pro_users").stream()
        users_list = [user.to_dict() for user in users_ref]
        return users_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/submit-feedback")
async def submit_feedback(data: FeedbackInput, user: dict = Depends(get_current_user), db: firestore.Client = Depends(get_db)):
    try:
        db.collection("feedback").add({
            "user_uid": user["uid"],
            "user_email": user.get("email"),
            "score": data.score,
            "text": data.text,
            "page": data.page,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {e}")