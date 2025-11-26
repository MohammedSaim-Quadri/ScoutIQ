"""
FastAPI dependency injection functions
"""
from fastapi import HTTPException
from firebase_admin import firestore
from langchain_groq import ChatGroq
from langchain_qdrant import Qdrant

# Global state (populated during app startup)
_db = None
_llm = None
_qdrant_db = None


def set_db(db: "firestore.Client"):
    """Set the global Firestore client"""
    global _db
    _db = db


def set_llm(llm: ChatGroq):
    """Set the global LLM client"""
    global _llm
    _llm = llm


def set_qdrant(qdrant: Qdrant):
    """Set the global Qdrant client"""
    global _qdrant_db
    _qdrant_db = qdrant


def get_db() -> "firestore.Client":
    """Get Firestore client dependency"""
    if _db is None:
        raise HTTPException(status_code=503, detail="Firestore not initialized")
    return _db


def get_llm():
    """Get LLM client dependency"""
    if _llm is None:
        raise HTTPException(status_code=503, detail="LLM not initialized")
    return _llm


def get_qdrant():
    """Get Qdrant client dependency"""
    if _qdrant_db is None:
        raise HTTPException(status_code=503, detail="Vector database not available. Resume parsing and candidate ranking features are currently disabled. Please contact support.")
    return _qdrant_db