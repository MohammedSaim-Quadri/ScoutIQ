"""
ScoutIQ Backend API
Main FastAPI application with routes for interview question generation,
resume parsing, candidate ranking, and analytics.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import logging

import firebase_admin
from firebase_admin import firestore, credentials
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_qdrant import Qdrant
from langchain_community.embeddings import VoyageEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_core.documents import Document

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Local imports
from llm_backend.models import ParsedResume, Input, ResumeInput, JDInput, FeedbackInput
from llm_backend.prompts import free_tier_prompt, pro_tier_prompt, parse_resume_prompt, job_seeker_prompt
from llm_backend.security import get_current_user, get_admin_user
from llm_backend.exceptions import (
    ScoutIQException, LLMServiceError, RateLimitError, InvalidInputError,
    get_error_suggestion
)
from llm_backend.cache import (
    generate_cache_key, get_cached_response, cache_response, cleanup_old_cache
)
from llm_backend.middleware import track_request_middleware
from llm_backend.analytics import track_feature_usage
from llm_backend import dependencies
from llm_backend.utils import call_llm_with_retry, parse_pro_response, extract_section

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic for FastAPI app"""
    logger.info("Starting ScoutIQ Backend...")

    # Initialize Firebase
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase-service-key.json")
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        dependencies.set_db(db)
        logger.info("Firebase initialized.")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")

    # Initialize LLM
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile")
        dependencies.set_llm(llm)
        logger.info("Groq LLM initialized.")
    except Exception as e:
        logger.error(f"LLM initialization failed: {e}")

    # Initialize Embeddings & Qdrant
    try:
        logger.info("Loading Voyage AI embedding model...")
        embeddings_model = VoyageEmbeddings(
            model="voyage-3.5-lite",
            voyage_api_key=os.getenv("VOYAGEAI_API_KEY")
        )
        logger.info("Embedding model loaded.")

        logger.info("Connecting to Qdrant...")
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url or not qdrant_api_key:
            logger.warning("⚠️ QDRANT_URL or QDRANT_API_KEY not set. Resume search features will be disabled.")
            raise ValueError("Qdrant credentials missing")
        
        qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=60
        )

        collection_name = "scoutiq_resumes_v2"
        try:
            qdrant_client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' exists.")
        except Exception:
            logger.info(f"Creating collection '{collection_name}'...")
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=512, distance=Distance.COSINE)
            )
            logger.info(f"Collection created.")

        qdrant_db = Qdrant(
            client=qdrant_client,
            collection_name=collection_name,
            embeddings=embeddings_model,
        )
        dependencies.set_qdrant(qdrant_db)
        logger.info("Qdrant client initialized.")
    except Exception as e:
        logger.error(f"❌ Qdrant/Embeddings initialization failed: {e}")
        logger.warning("⚠️ Resume parsing and candidate ranking features will be unavailable.")
        # Don't crash - let the API start without Qdrant
        dependencies.set_qdrant(None)

    logger.info("Startup complete. Server is ready.")
    yield
    logger.info("Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="ScoutIQ API",
    description="AI-powered interview question generation and candidate ranking",
    version="2.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(ScoutIQException)
async def scoutiq_exception_handler(request: Request, exc: ScoutIQException):
    logger.error(f"ScoutIQ error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.user_message,
            "type": exc.__class__.__name__,
            "suggestion": get_error_suggestion(exc)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    field = errors[0].get("loc")[-1] if errors else "input"
    return JSONResponse(
        status_code=400,
        content={
            "error": f"Invalid {field}. Please check your input.",
            "type": "ValidationError",
            "details": errors,
            "suggestion": "Make sure your Job Description and Resume are properly filled out."
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unexpected error")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Something went wrong on our end. Our team has been notified.",
            "type": "InternalServerError",
            "suggestion": "Please try again in a few moments. If the issue persists, contact support@scoutiq.com"
        }
    )


# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track all requests for monitoring"""
    db = dependencies.get_db() if dependencies._db else None
    return await track_request_middleware(request, call_next, db)


# ============================================================================
# CORE API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ScoutIQ API",
        "version": "2.0.0"
    }


@app.post("/generate")
@limiter.limit("10/minute")
async def generate_questions(
    request: Request,
    data: Input,
    user: dict = Depends(get_current_user),
    llm: ChatGroq = Depends(dependencies.get_llm),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """
    Generate interview questions (and insights for Pro users)
    
    - Free users: Technical, behavioral, and followup questions
    - Pro users: All questions + insight summary + skill gaps
    """
    # Validate input
    if len(data.jd.strip()) < 50:
        raise InvalidInputError("Job Description", "Must be at least 50 characters long")
    if len(data.resume.strip()) < 100:
        raise InvalidInputError("Resume", "Must be at least 100 characters long")

    # Check user tier
    try:
        doc_ref = db.collection("pro_users").document(user["email"].lower())
        doc = doc_ref.get()
        is_pro = doc.exists and doc.to_dict().get("tier") in ["monthly", "yearly", "lifetime"]
        tier = doc.to_dict().get("tier", "free") if doc.exists else "free"
    except Exception as e:
        logger.error(f"Failed to check user tier: {e}")
        is_pro = False
        tier = "free"

    # Check cache
    cache_key = generate_cache_key(data.jd, data.resume, tier)
    cached_result = await get_cached_response(cache_key, db)

    if cached_result:
        return {"result": cached_result, "tier": tier, "cached": True}

    # Generate new response
    try:
        prompt = pro_tier_prompt(data.jd, data.resume) if is_pro else free_tier_prompt(data.jd, data.resume)
        response = await call_llm_with_retry(llm, prompt)
        text = response.content

        result = parse_pro_response(text) if is_pro else {
            "technical": extract_section(text, "technical"),
            "behavioral": extract_section(text, "behavioral"),
            "followup": extract_section(text, "followup"),
            "insight_summary": None,
            "skill_gaps": None
        }

        await cache_response(cache_key, result, tier, db)
        await track_feature_usage(
            user_uid=user["uid"],
            feature="generate_questions",
            metadata={
                "tier": tier,
                "jd_length": len(data.jd),
                "resume_length": len(data.resume),
                "cached": False
            },
            db=db
        )

        logger.info(f"Generated content for {tier} user {user['email']}")
        return {"result": result, "tier": tier, "cached": False}

    except RateLimitError:
        raise RateLimitError()
    except Exception as e:
        logger.exception(f"LLM generation failed for user {user['uid']}")
        raise LLMServiceError()


@app.post("/parse-resume", response_model=ParsedResume)
@limiter.limit("5/minute")
async def parse_resume(
    request: Request,
    data: ResumeInput,
    user: dict = Depends(get_current_user),
    qdrant: Qdrant = Depends(dependencies.get_qdrant),
    llm: ChatGroq = Depends(dependencies.get_llm),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Parse resume and add to candidate database with semantic search"""
    structured_llm = llm.with_structured_output(ParsedResume)
    prompt = parse_resume_prompt(data.resume_text)

    try:
        parsed_data = await call_llm_with_retry(structured_llm, prompt)

        # Save to Firestore
        doc_ref = db.collection("candidates").document()
        doc_ref.set({
            **parsed_data.model_dump(),
            "user_uid": user["uid"],
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Build embedding content (improved with full experience)
        experience_text = "\n".join([
            f"- {exp.job_title} at {exp.company} ({exp.duration}): {exp.summary}"
            for exp in parsed_data.experience
        ])

        skills_text = ", ".join([
            f"{s.name} ({s.level})" if hasattr(s, 'level') and s.level else s.name
            for s in parsed_data.skills
        ])

        content_to_embed = f"""
Candidate: {parsed_data.full_name}
Email: {parsed_data.email or 'Not provided'}
Phone: {parsed_data.phone or 'Not provided'}

Professional Summary:
{parsed_data.summary}

Core Skills:
{skills_text}

Work Experience:
{experience_text}

Total Years of Experience: {len(parsed_data.experience)} roles
        """.strip()

        # Add to Qdrant
        doc = Document(
            page_content=content_to_embed,
            metadata={
                "firestore_id": doc_ref.id,
                "user_uid": user["uid"],
                "full_name": parsed_data.full_name,
                "email": parsed_data.email or "",
                "experience_count": len(parsed_data.experience),
                "skills_count": len(parsed_data.skills)
            }
        )

        await qdrant.aadd_documents([doc], ids=[doc_ref.id])
        logger.info(f"Resume parsed for {parsed_data.full_name}")
        return parsed_data

    except Exception as e:
        logger.exception(f"Failed to parse resume for user {user['uid']}")
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")


@app.post("/rank-candidates")
@limiter.limit("20/minute")
async def rank_candidates(
    request: Request,
    data: JDInput,
    user: dict = Depends(get_current_user),
    qdrant: Qdrant = Depends(dependencies.get_qdrant),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Rank candidates from database by relevance to job description"""
    try:
        search_results = await qdrant.asimilarity_search(
            data.jd,
            k=10,
            filter={"must": [{"key": "user_uid", "match": {"value": user["uid"]}}]}
        )

        if not search_results:
            logger.info(f"No candidates found for user {user['uid']}")
            return []

        # Fetch from Firestore
        firestore_ids = [doc.metadata["firestore_id"] for doc in search_results]
        candidate_refs = [db.collection("candidates").document(fid) for fid in firestore_ids]
        candidate_docs = db.get_all(candidate_refs)

        # Build ordered results
        ordered_candidates = []
        id_to_candidate = {c.id: c.to_dict() for c in candidate_docs if c.exists}

        for i, doc in enumerate(search_results):
            fs_id = doc.metadata["firestore_id"]
            if fs_id in id_to_candidate:
                candidate = id_to_candidate[fs_id]
                candidate["relevance_score"] = round(doc.metadata.get("score", 0), 3)
                candidate["rank"] = i + 1
                ordered_candidates.append(candidate)

        logger.info(f"Ranked {len(ordered_candidates)} candidates")
        return ordered_candidates

    except Exception as e:
        logger.exception(f"Failed to rank candidates for user {user['uid']}")
        raise HTTPException(status_code=500, detail="Failed to rank candidates.")


@app.post("/improve-resume")
@limiter.limit("10/minute")
async def improve_resume(
    request: Request,
    data: Input,
    user: dict = Depends(get_current_user),
    llm: ChatGroq = Depends(dependencies.get_llm)
):
    """Job seeker mode: Get AI-powered resume improvement suggestions"""
    prompt = job_seeker_prompt(data.jd, data.resume)

    try:
        response = await call_llm_with_retry(llm, prompt)
        return {"improvements": response.content}
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached.")
    except Exception as e:
        logger.exception(f"Error improving resume for user {user['uid']}")
        raise HTTPException(status_code=500, detail="Failed to generate improvements.")


@app.post("/submit-feedback")
async def submit_feedback(
    data: FeedbackInput,
    user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Submit user feedback"""
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
        logger.exception(f"Failed to save feedback for user {user['uid']}")
        raise HTTPException(status_code=500, detail="Failed to save feedback.")


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.post("/admin/cleanup-cache")
async def admin_cleanup_cache(
    user: dict = Depends(get_admin_user),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Delete cache entries older than 24 hours"""
    try:
        count = await cleanup_old_cache(db)
        return {"deleted": count}
    except Exception as e:
        logger.exception("Cache cleanup failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/usage-logs")
async def get_usage_logs(
    user: dict = Depends(get_admin_user),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Get all usage logs"""
    try:
        logs_ref = db.collection("usage_logs").stream()
        logs_list = [log.to_dict() for log in logs_ref]
        return logs_list
    except Exception as e:
        logger.exception("Failed to fetch usage logs")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/pro-users")
async def get_pro_users(
    user: dict = Depends(get_admin_user),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Get all pro users"""
    try:
        users_ref = db.collection("pro_users").stream()
        users_list = [user.to_dict() for user in users_ref]
        return users_list
    except Exception as e:
        logger.exception("Failed to fetch pro users")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/embedding-stats")
async def get_embedding_stats(
    user: dict = Depends(get_admin_user),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Get embedding token usage statistics"""
    try:
        logs = db.collection("usage_logs").stream()

        total_resumes_parsed = sum(1 for log in logs if log.to_dict().get("has_insights"))
        estimated_tokens = total_resumes_parsed * 800
        free_tier_limit = 200_000_000
        percentage_used = (estimated_tokens / free_tier_limit) * 100

        return {
            "total_resumes_parsed": total_resumes_parsed,
            "estimated_tokens_used": estimated_tokens,
            "free_tier_limit": free_tier_limit,
            "percentage_used": f"{percentage_used:.2f}%",
            "tokens_remaining": free_tier_limit - estimated_tokens,
            "model": "voyage-3.5-lite"
        }
    except Exception as e:
        logger.exception("Failed to fetch embedding stats")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/analytics/overview")
async def get_analytics_overview(
    user: dict = Depends(get_admin_user),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Get high-level analytics overview (last 7 days)"""
    try:
        seven_days_ago = datetime.now() - timedelta(days=7)
        metrics_ref = db.collection("api_metrics").where("timestamp", ">=", seven_days_ago).stream()

        total_requests = 0
        avg_response_time = []
        status_codes = {}

        for metric in metrics_ref:
            data = metric.to_dict()
            total_requests += 1
            avg_response_time.append(data.get("duration_seconds", 0))
            status_code = data.get("status_code", 500)
            status_codes[status_code] = status_codes.get(status_code, 0) + 1

        feature_usage_ref = db.collection("feature_usage").where("timestamp", ">=", seven_days_ago).stream()
        features = {}
        for usage in feature_usage_ref:
            feature = usage.to_dict().get("feature", "unknown")
            features[feature] = features.get(feature, 0) + 1

        active_users = set()
        for usage in db.collection("usage_logs").where("timestamp", ">=", seven_days_ago).stream():
            active_users.add(usage.to_dict().get("email"))

        return {
            "period": "last_7_days",
            "total_requests": total_requests,
            "avg_response_time_seconds": round(sum(avg_response_time) / len(avg_response_time), 3) if avg_response_time else 0,
            "status_codes": status_codes,
            "success_rate": f"{(status_codes.get(200, 0) / total_requests * 100):.1f}%" if total_requests > 0 else "0%",
            "feature_usage": features,
            "active_users": len(active_users),
            "most_used_feature": max(features.items(), key=lambda x: x[1])[0] if features else None
        }
    except Exception as e:
        logger.exception("Failed to fetch analytics")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/analytics/errors")
async def get_error_analytics(
    user: dict = Depends(get_admin_user),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Get error analytics (last 24 hours)"""
    try:
        yesterday = datetime.now() - timedelta(hours=24)
        error_metrics = db.collection("api_metrics").where(
            "timestamp", ">=", yesterday
        ).where("status_code", ">=", 400).stream()

        errors_by_endpoint = {}
        errors_by_code = {}

        for metric in error_metrics:
            data = metric.to_dict()
            endpoint = data.get("endpoint", "unknown")
            status_code = data.get("status_code", 500)

            if endpoint not in errors_by_endpoint:
                errors_by_endpoint[endpoint] = {"count": 0, "codes": {}}

            errors_by_endpoint[endpoint]["count"] += 1
            errors_by_endpoint[endpoint]["codes"][status_code] = \
                errors_by_endpoint[endpoint]["codes"].get(status_code, 0) + 1

            errors_by_code[status_code] = errors_by_code.get(status_code, 0) + 1

        return {
            "period": "last_24_hours",
            "total_errors": sum(errors_by_code.values()),
            "errors_by_code": errors_by_code,
            "errors_by_endpoint": errors_by_endpoint,
            "critical_endpoints": [
                endpoint for endpoint, data in errors_by_endpoint.items()
                if data["count"] > 10
            ]
        }
    except Exception as e:
        logger.exception("Failed to fetch error analytics")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/analytics/users")
async def get_user_analytics(
    user: dict = Depends(get_admin_user),
    db: firestore.Client = Depends(dependencies.get_db)
):
    """Get user behavior analytics (last 30 days)"""
    try:
        pro_users = list(db.collection("pro_users").stream())
        thirty_days_ago = datetime.now() - timedelta(days=30)
        usage_logs = db.collection("usage_logs").where("timestamp", ">=", thirty_days_ago).stream()

        user_activity = {}
        for log in usage_logs:
            data = log.to_dict()
            email = data.get("email", "unknown")

            if email not in user_activity:
                user_activity[email] = {
                    "total_generations": 0,
                    "tier": data.get("tier", "free")
                }

            user_activity[email]["total_generations"] += 1

        total_users = len(user_activity)
        active_users = sum(1 for u in user_activity.values() if u["total_generations"] > 0)
        pro_user_count = len(pro_users)

        top_users = sorted(
            user_activity.items(),
            key=lambda x: x[1]["total_generations"],
            reverse=True
        )[:10]

        return {
            "period": "last_30_days",
            "total_users": total_users,
            "active_users": active_users,
            "pro_users": pro_user_count,
            "free_users": total_users - pro_user_count,
            "conversion_rate": f"{(pro_user_count / total_users * 100):.1f}%" if total_users > 0 else "0%",
            "top_users": [
                {
                    "email": email,
                    "generations": data["total_generations"],
                    "tier": data["tier"]
                }
                for email, data in top_users
            ]
        }
    except Exception as e:
        logger.exception("Failed to fetch user analytics")
        raise HTTPException(status_code=500, detail=str(e))