"""
Caching utilities for LLM responses
"""
import hashlib
from datetime import datetime, timedelta
from firebase_admin import firestore
import logging

logger = logging.getLogger(__name__)

def generate_cache_key(jd: str, resume: str, tier: str) -> str:
    """Generate unique cache key based on content + tier"""
    content = f"{jd}::{resume}::{tier}"
    return hashlib.sha256(content.encode()).hexdigest()


async def get_cached_response(cache_key: str, db: "firestore.Client"):
    """
    Check if we have a cached response (24hr TTL)
    
    Args:
        cache_key: Unique hash of the request
        db: Firestore client
        
    Returns:
        Cached result dict or None if cache miss
    """
    try:
        cache_ref = db.collection("llm_cache").document(cache_key)
        cached_doc = cache_ref.get()

        if cached_doc.exists:
            cached_data = cached_doc.to_dict()
            created_at = cached_data.get("created_at")

            if created_at:
                cache_age = datetime.now() - created_at
                if cache_age < timedelta(hours=24):
                    logger.info(f"cache hit(age: {cache_age.seconds//3600}h)")
                    return cached_data["result"]
                else:
                    logger.info(f"Cache expired (age: {cache_age.days}d {cache_age.seconds//3600}h)")

        logger.info("Cache miss")
        return None
    except Exception as e:
        logger.error(f"Cache lookup error: {e}")
        return None
    
async def cache_response(cache_key: str, result: dict, tier: str, db: "firestore.Client"):
    """
    Cache the LLM response for 24 hours
    
    Args:
        cache_key: Unique hash of the request
        result: The LLM response to cache
        tier: User tier (free, monthly, yearly, lifetime)
        db: Firestore client
    """
    try:
        cache_ref = db.collection("llm_cache").document(cache_key)
        cache_ref.set({
            "result": result,
            "tier": tier,
            "created_at": datetime.now(),
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        logger.info("Response cached")
    except Exception as e:
        logger.error(f"Cache save error: {e}")


async def cleanup_old_cache(db: "firestore.Client") -> int:
    """
    Delete cache entries older than 24 hours
    
    Args:
        db: Firestore client
        
    Returns:
        Number of deleted entries
    """
    try:
        cutoff = datetime.now() - timedelta(hours=24)
        old_docs = db.collection("llm_cache").where(
            "created_at", "<", cutoff
        ).stream()
        
        batch = db.batch()
        count = 0
        for doc in old_docs:
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:  # Firestore batch limit
                batch.commit()
                batch = db.batch()
        
        batch.commit()
        logger.info(f"Cleaned up {count} old cache entries")
        return count
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        raise