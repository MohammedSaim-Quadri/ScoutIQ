"""
Analytics and feature usage tracking
"""
from firebase_admin import firestore
import logging

logger = logging.getLogger(__name__)


async def track_feature_usage(
    user_uid: str,
    feature: str,
    metadata: dict = None,
    db: firestore.Client = None
):
    """
    Track feature usage for analytics
    
    Args:
        user_uid: User's unique ID
        feature: Feature name (e.g., "generate_questions", "parse_resume")
        metadata: Additional context (tier, input lengths, etc.)
        db: Firestore client
    """
    try:
        if db:
            db.collection("feature_usage").add({
                "user_uid": user_uid,
                "feature": feature,
                "metadata": metadata or {},
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            logger.debug(f"Tracked feature: {feature} for user {user_uid}")
    except Exception as e:
        logger.error(f"Failed to track feature usage: {e}")