import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import json
from app.generator import run_prompt_chain, extract_text_from_pdf, extract_text_from_docx, generate_pdf
from io import BytesIO
from datetime import datetime

cred_dict = json.loads(st.secrets["FIREBASE_CREDS"])
cred = credentials.Certificate(cred_dict)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

def log_usage_to_firestore(email):
    try:
        doc_ref = db.collection("usage_logs").document(email.lower())
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.update({
                "total_generations":firestore.Increment(1),
                "last_used_at":firestore.SERVER_TIMESTAMP
            })
        else:
            doc_ref.set({
                "total_generations": 1,
                "last_used_at": firestore.SERVER_TIMESTAMP
            })
    except Exception as e:
        print(f"❌ Firestore logging error for {email}: {e}")


def is_pro_user(email):
    try:
        doc_ref = firestore.client().collection("pro_users").document(email.lower())
        doc = doc_ref.get()
        return doc.exists and doc.to_dict().get("pro",False)
    except Exception as e:
        st.warning(f"Error checking pro status.")
        return False
    

def run_ui():

    if 'user_info' not in st.session_state:
        st.error("You must be logged in to access this page.")
        st.stop()

    user_email = st.session_state.user_info['email']
    is_pro = is_pro_user(user_email)

    key = f"gen_count_{user_email}"
    date_key = f"gen_date_{user_email}"

    today = datetime.now().strftime("%Y-%m-%d")

    if st.session_state.get(date_key) != today:
        st.session_state[date_key] = today
        st.session_state[key] = 0

    st.set_page_config(page_title="AI Interview Q Generator", layout="centered")
    st.title("🎯 AI-Powered Interview Question Generator")
    if is_pro:
        st.success("💎 You are a Pro user — unlimited generations unlocked.")
    else:
        remaining = 3 - st.session_state.get(key, 0)
        st.info(f"🧮 You have {remaining} free generations left today.")

    # JD Input
    jd_input = st.text_area("📄 Paste Job Description", height=200)

    # Resume Input
    st.markdown("**Resume Input**(choose one)")
    resume_text = ""
    resume_file = st.file_uploader("Upload Resume (PDF or Docx)", type=["pdf", "docx"])

    if resume_file is not None:
        file_bytes = BytesIO(resume_file.read())
        if resume_file.name.endswith(".pdf"):
            resume_text = extract_text_from_pdf(file_bytes)
            st.success("Resume text extracted successfully!")
        elif resume_file.name.endswith(".docx"):
            resume_text = extract_text_from_docx(file_bytes)
            st.success("Resume text extracted successfully!")
        
        st.text_area("Extracted Resume Text(read-only)", value=resume_text, height=200, disabled=True)
    else:
        resume_text = st.text_area("Or Paste Resume Text below", height=200)

    # Generate Button
    if not is_pro and st.session_state.get(key, 0) >= 3:
        st.error("🚫 You’ve hit your free tier limit of 3 generations today.")
        st.markdown(
            "**💎 Upgrade to Pro for unlimited access →** "
            "[View Pricing](pages/Pricing.py)", unsafe_allow_html=True
        )
        st.stop()

    if st.button("🚀 Generate Questions"):
        if jd_input.strip() == "" or resume_text.strip() == "":
            st.warning("Please provide both Job Description and Resume.")
        else:
            with st.spinner("Generating questions..."):
                # Run the prompt chain
                results = run_prompt_chain(jd_input, resume_text)
                st.text_area("🧪 Raw Model Output", value="\n".join(results['technical'] + results['behavioral'] + results['followup']), height=250)

                st.subheader("🔧 Technical Questions")
                for q in results['technical']:
                    st.markdown(f"{q}")

                st.subheader("💬 Behavioral Questions")
                for q in results['behavioral']:
                    st.markdown(f"{q}")

                st.subheader("⚠️ Red Flag / Follow-up Questions")
                for q in results['followup']:
                    st.markdown(f"{q}")
            # Download PDF
            pdf_bytes = generate_pdf(results['technical'], results['behavioral'], results['followup'])
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name="interview_questions.pdf",
                mime="application/pdf"
            )
            st.session_state[key] += 1
            log_usage_to_firestore(user_email)

            log_entry = {
                "email": user_email,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pro": is_pro,
                "technical_qs": len(results['technical']),
                "behavioral_qs": len(results['behavioral']),
                "followup_qs": len(results['followup']),
                "total_qs": len(results['technical']) + len(results['behavioral']) + len(results['followup'])
            }

            db.collection("usage_logs").add(log_entry)

    if user_email == "mohammedsaimquadri@gmail.com":  # replace with your email
        st.subheader("📊 Admin: Generation Log")
        import pandas as pd
        try:
            df = pd.read_csv("usage_logs.csv")
            st.dataframe(df)
        except FileNotFoundError:
            st.info("No usage logs yet.")


