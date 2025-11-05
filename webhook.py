from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import JSONResponse
import firebase_admin
from firebase_admin import credentials, firestore
import os
import smtplib
from email.message import EmailMessage
from typing import Annotated

app = FastAPI()

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

@app.post("/gumroad-webhook")
async def gumroad_webhook(
    request: Request,
    email: Annotated[str, Form()] = None,
    product_name: Annotated[str, Form()] = ""
):
    # Verify secret from query parameters
    secret = request.query_params.get("secret")
    if secret != GUMROAD_SECRET:
        print("Invalid webhook")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Get form data
    form_data = await request.form()
    print("🚨 Received webhook:", dict(form_data))

    email = form_data.get("email")
    product_name = form_data.get("product_name", "").lower()
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
        send_confirmation_email(email, tier)

        return JSONResponse(
            content={"success": True, "message": "User upgraded"}, 
            status_code=200
        )
    
    raise HTTPException(status_code=400, detail="Email not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)