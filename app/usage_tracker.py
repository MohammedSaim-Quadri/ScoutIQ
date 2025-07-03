# app/usage_tracker.py
import datetime
from firebase_admin import firestore

def get_today_usage(email: str) -> int:
    db = firestore.client()
    today = datetime.date.today().isoformat()
    doc_ref = db.collection("daily_usage").document(f"{email}_{today}")
    doc = doc_ref.get()
    return doc.to_dict().get("count", 0) if doc.exists else 0

def increment_today_usage(email: str):
    db = firestore.client()
    today = datetime.date.today().isoformat()
    doc_ref = db.collection("daily_usage").document(f"{email}_{today}")
    doc_ref.set({
        "count": firestore.Increment(1),
        "timestamp": firestore.SERVER_TIMESTAMP
    }, merge=True)
