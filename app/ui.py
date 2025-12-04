import firebase_admin
import requests, os
from app.usage_tracker import get_today_usage, increment_today_usage
from firebase_admin import credentials, firestore
import streamlit as st
import json
from app.generator import run_prompt_chain, extract_text_from_pdf, extract_text_from_docx, generate_pdf
from io import BytesIO
from datetime import datetime

# try:
#     firebase_creds = st.secrets["FIREBASE_CREDS"]

#     # Cloud → JSON string
#     if isinstance(firebase_creds, str):
#         cred_dict = json.loads(firebase_creds)
#     else:
#         # Local/EC2 → already dict-like
#         cred_dict = dict(firebase_creds)

#     cred = credentials.Certificate(cred_dict)

#     if not firebase_admin._apps:
#         firebase_admin.initialize_app(cred)
# except Exception as e:
#     st.error(f"Firebase initialization error: {e}")
#     st.stop()

# Firebase initialization
try:
    # Check if the app is already initialized
    if not firebase_admin._apps:
        # Point to the service key file directly for local development
        cred = credentials.Certificate("firebase-service-key.json")
        firebase_admin.initialize_app(cred)
except Exception as e:
    # Catch potential errors like file not found
    st.error(f"Firebase initialization error: {e}")
    st.info("Make sure 'firebase-service-key.json' is in your project's root directory.")
    st.stop()

db = firestore.client()
BASE_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Firestore logging
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

# Pro user check
def is_pro_user(email):
    try:
        doc_ref = firestore.client().collection("pro_users").document(email.lower())
        doc = doc_ref.get()
        if doc.exists and doc.to_dict().get("pro", False):
            return doc.to_dict().get("tier", "monthly")  # default to monthly if missing
        else:
            return "free"
    except Exception as e:
        st.warning(f"Error checking pro status.")
        return False
    
# Main ui funtion
def run_ui():

    if 'user_info' not in st.session_state:
        st.error("You must be logged in to access this page.")
        st.stop()

    user_email = st.session_state.user_info['email']
    user_tier = is_pro_user(user_email)
    st.session_state.user_tier = user_tier

    today_usage = get_today_usage(user_email)

    
    st.title("🎯 AI-Powered Interview Question Generator")
    if user_tier == "free":
        remaining = 3 - today_usage
        st.info(f"🧮 You have {remaining} free generations left today.")
    elif user_tier == "monthly":
        st.success("💎 Monthly Pro user — unlimited generations.")
    elif user_tier == "yearly":
        st.success("💎 Yearly Pro user — unlimited generations + early feature access.")
    elif user_tier == "lifetime":
        st.success("🔓 Lifetime user — all current & future features unlocked.")


    # JD Input
    jd_input = st.text_area("📄 Paste Job Description", height=200)

    # Resume Input
    st.markdown("**Resume Input**(choose one)")

    resume_text = ""

    resume_files = st.file_uploader(
        "Upload Resume (PDF or Docx)",
        type=["pdf", "docx"],
        accept_multiple_files=True
        )
    
    all_resumes_texts = []

    if resume_files:
        for resume_file in resume_files:
            file_bytes = BytesIO(resume_file.read())
            text = ""
            if resume_file.name.endswith(".pdf"):
                text = extract_text_from_pdf(file_bytes)
                st.success("Resume text extracted successfully!")
            elif resume_file.name.endswith(".docx"):
                text = extract_text_from_docx(file_bytes)
                st.success("Resume text extracted successfully!")

            if text:
                all_resumes_texts.append((resume_file.name, text))
        
        if all_resumes_texts:
            resume_text = all_resumes_texts[0][1]

            if len(all_resumes_texts)>1:
                st.text_area(
                    f"Extracted Resume Text (Showing 1 of {len(all_resumes_texts)} files)",
                    value=resume_text,
                    height=200,
                    disabled=True
                )
            else:
                st.text_area(
                "Extracted Resume Text (read-only)", 
                value=resume_text, 
                height=200, 
                disabled=True
                )
            
            # Check user tier for batch parsing
            if st.session_state.user_tier!= "free":
                if len(all_resumes_texts)>1:
                    if st.button(f"Parse All {len(all_resumes_texts)} Resumes & Add to Database"):
                        with st.spinner(f"Batch processing {len(all_resumes_texts)} resumes... This may take a moment."):
                            parsed_count = 0
                            for name, text in all_resumes_texts:
                                try:
                                    id_token = st.session_state.id_token
                                    headers = {"Authorization": f"Bearer {id_token}"}
                                    response = requests.post(
                                        f"{BASE_BACKEND_URL}/parse-resume",
                                        json={"resume_text": text},
                                        headers=headers,
                                        timeout=60
                                    )
                                    response.raise_for_status()
                                    parsed_count += 1
                                except Exception as e:
                                    st.error(f"Failed to parse {name}: {e}")
                            st.success(f"Successfully parsed and saved {parsed_count} / {len(all_resumes_texts)} resumes to your database.")
                else:
                    if st.button("Parse & Save Resume to Database"):
                        with st.spinner("Parsing and saving resume..."):
                            try:
                                id_token = st.session_state.id_token
                                headers = {"Authorization": f"Bearer {id_token}"}
                                response = requests.post(
                                    f"{BASE_BACKEND_URL}/parse-resume",
                                    json={"resume_text": resume_text},
                                    headers=headers,
                                    timeout=60
                                )
                                response.raise_for_status()
                                st.success("Resume parsed and saved to your candidate database!")
                            except Exception as e:
                                st.error(f"Failed to parse resume: {e}")
            else:
                # If user is "free", show a disabled button and an upsell link
                st.button("Parse & Save Resumes to Database", disabled=True)
                st.page_link("app_pages/Pricing.py", label="💎 Upgrade to Pro to save resumes to your database.", icon="💎")

    if not resume_files:
        resume_text = st.text_area("Or Paste Resume Text below", height=200)
    #     if 'parsed_resume' not in st.session_state or st.session_state.get('parsed_file_name')!= resume_file.name:
    #         with st.spinner("Parsing resume..."):
    #             try:
    #                 # --- ADD THIS API CALL ---
    #                 id_token = st.session_state.id_token
    #                 headers = {"Authorization": f"Bearer {id_token}"}
    #                 response = requests.post(
    #                     f"{BASE_BACKEND_URL}/parse-resume",
    #                     json={"resume_text": resume_text},
    #                     headers=headers,
    #                     timeout=60
    #                 )
    #                 response.raise_for_status()
    #                 st.session_state.parsed_resume = response.json()
    #                 st.session_state.parsed_file_name = resume_file.name
    #                 st.success("Resume parsed and saved to your candidate database!")
    #                 # --- END ADD ---
    #             except Exception as e:
    #                 st.error(f"Failed to parse resume: {e}")
        
    #     st.text_area("Extracted Resume Text(read-only)", value=resume_text, height=200, disabled=True)
    # else:
    #     resume_text = st.text_area("Or Paste Resume Text below", height=200)

    # Generate Button
    if user_tier == "free" and today_usage >= 3:
        st.error("🚫 You’ve hit your free tier limit of 3 generations today.")
        st.markdown(
            "**💎 Upgrade to Pro for unlimited access →** "
            "[View Pricing](app_pages/Pricing.py)", unsafe_allow_html=True
        )
        st.stop()

    skill_gaps = None
    summary = None
    if st.button("🚀 Generate Questions"):
        if jd_input.strip() == "" or resume_text.strip() == "":
            st.warning("Please provide both Job Description and at least one Resume.")
        else:
            with st.spinner("Generating questions..."):
                # Run the prompt chain
                results = run_prompt_chain(jd_input, resume_text)
                #st.text_area("🧪 Raw Model Output", value="\n".join(results['technical'] + results['behavioral'] + results['followup']), height=250)

                if results.get("technical"):
                    st.subheader("🔧 Technical Questions")
                    for q in results['technical']:
                        st.markdown(f"{q}")

                    st.subheader("💬 Behavioral Questions")
                    for q in results['behavioral']:
                        st.markdown(f"{q}")

                    st.subheader("⚠️ Red Flag / Follow-up Questions")
                    for q in results['followup']:
                        st.markdown(f"{q}")

                    # Check if Pro content exists in response
                    if results.get("insight_summary"):
                        st.markdown("---")
                        st.subheader("📊 Resume & JD Insight Summary")
                        st.markdown(results["insight_summary"])
                    
                    if results.get("skill_gaps"):
                        st.subheader("⚡ Skill Gap Highlights")
                        st.markdown(results["skill_gaps"])

                    if user_tier == "free" and not results.get("insight_summary"):
                        st.info("💎 Want deeper insights? Upgrade to Pro for AI-powered resume analysis!")
                        st.markdown("[View Pricing →](https://saimquadri.gumroad.com/l/scoutiq-pro-monthly)")
            
                    # Download PDF
                    pdf_bytes = generate_pdf(results['technical'], results['behavioral'], results['followup'])
                    st.download_button(
                        label="Download PDF",
                        data=pdf_bytes,
                        file_name="interview_questions.pdf",
                        mime="application/pdf"
                    )
                    # Logging
                    increment_today_usage(user_email)
                    log_usage_to_firestore(user_email)

                    log_entry = {
                        "email": user_email,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "pro": user_tier,
                        "technical_qs": len(results['technical']),
                        "behavioral_qs": len(results['behavioral']),
                        "followup_qs": len(results['followup']),
                        "total_qs": len(results['technical']) + len(results['behavioral']) + len(results['followup']),
                        "has_insights": results.get("insight_summary") is not None,
                        "has_skill_gaps": results.get("skill_gaps") is not None,
                    }

                    db.collection("usage_logs").add(log_entry)
                else:
                    st.error("Error generating questions. Please try again.")
                    if results:
                        st.json(results)


