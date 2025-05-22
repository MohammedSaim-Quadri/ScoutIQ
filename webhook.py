from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

app = Flask(__name__)

cred_dict = json.loads(st.secrets["FIREBASE_CREDS"])
cred = credentials.Certificate(cred_dict)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route("gumroad-webhook", methods=["POST"])
def gumroad_webhook():
    data = request.form.to_dict()

    email = data.get("email")
    product_name = data.get("product_name", "").lower()

    if email:
        if "lifetime" in product_name:
            tier = "lifetime"
        elif "yearly" in product_name:
            tier = "yearly"
        elif "monthly" in product_name:
            tier = "monthly"
        else:
            tier = "pro"

        doc_ref = db.collection("pro_users").document(email.lower())
        doc_ref.set({
            "tier": tier,
            "source": "gumroad",
            "created_at": firestore.SERVER_TIMESTAMP
        })

        return jsonify({"success": True, "message": "User upgraded"}), 200
    
    return jsonify({"error":"Email not found"}), 400


if __name__ == "__main__":
    app.run(debug=True)