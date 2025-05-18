import streamlit as st
from app.generator import run_prompt_chain, extract_text_from_pdf, extract_text_from_docx, generate_pdf
from io import BytesIO

def run_ui():
    st.set_page_config(page_title="AI Interview Q Generator", layout="centered")
    st.title("🎯 AI-Powered Interview Question Generator")

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
