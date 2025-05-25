from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import smtplib
from email.message import EmailMessage

app = Flask(__name__)


GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GUMROAD_SECRET = os.environ.get("GUMROAD_SECRET")


def send_confirmation_email(email, tier):
    msg = EmailMessage()
    msg["Subject"] = "ScoutIQ Pro Access Confirmed"
    msg["From"] = GMAIL_USER
    msg["To"] = email
    msg.set_content(f"""
        Hi there 👋,

        Thanks for purchasing the {tier.capitalize()} plan on ScoutIQ!

        You now have full Pro access to unlimited interview question generations.

        👉 Log in here: https://scoutiq-khsaxctllirftnbwrx6588.streamlit.app/

        Enjoy,  
        - The ScoutIQ Team 🚀
        """)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Confirmation email sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send email to {email}: {e}")

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-service-key.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/gumroad-webhook", methods=["POST"])
def gumroad_webhook():
    if request.args.get("secret") != GUMROAD_SECRET:
        print("Invalid webhook")
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.form.to_dict()
    print("🚨 Received webhook:", data)

    email = data.get("email")
    product_name = data.get("product_name", "").lower()
    print(f"Parsed email: {email}, product: {product_name}")

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
        send_confirmation_email(email,tier)

        return jsonify({"success": True, "message": "User upgraded"}), 200
    
    return jsonify({"error":"Email not found"}), 400



if __name__ == "__main__":
    app.run(debug=True)