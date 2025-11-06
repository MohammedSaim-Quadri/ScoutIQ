# pages/3_Candidate_Database.py
import streamlit as st
import requests
import os

st.set_page_config(page_title="Candidate Database", layout="centered")
st.title("🗂️ Candidate Database & Ranking")

# Check for login
if 'user_info' not in st.session_state or 'id_token' not in st.session_state:
    st.error("You must be logged in to access this page.")
    st.page_link("pages/App.py", label="Log in", icon="🔐")
    st.stop()

# Get auth token and backend URL
id_token = st.session_state.id_token
headers = {"Authorization": f"Bearer {id_token}"}
BASE_BACKEND_URL = os.getenv("BACKEND_URL", "[http://127.0.0.1:8000](http://127.0.0.1:8000)")

jd_input = st.text_area("Paste Job Description to rank your candidates", height=200)

if st.button("🏆 Rank Candidates"):
    if not jd_input.strip():
        st.warning("Please paste a Job Description.")
    else:
        with st.spinner("Ranking candidates from your database..."):
            try:
                response = requests.post(
                    f"{BASE_BACKEND_URL}/rank-candidates",
                    json={"jd": jd_input},
                    headers=headers,
                    timeout=60
                )
                response.raise_for_status()
                candidates = response.json()

                if not candidates:
                    st.info("No matching candidates found in your database.")
                else:
                    st.subheader(f"Top {len(candidates)} Matches:")
                    # Sort candidates by relevance (order returned by backend)
                    # We need to re-match with the search results order,
                    # as firestore's get_all doesn't guarantee order.

                    # A simple display for now:
                    for i, candidate in enumerate(candidates):
                        with st.expander(f"**#{i+1} - {candidate.get('full_name')}**"):
                            st.write(f"**Email:** {candidate.get('email', 'N/A')}")
                            st.write(f"**Summary:** {candidate.get('summary', 'N/A')}")
                            skills_list = [s.get('name') for s in candidate.get('skills',) if s.get('name')]
                            st.write(f"**Skills:** {', '.join(skills_list)}")

            except Exception as e:
                st.error(f"Failed to rank candidates: {e}")

st.markdown("---")
st.markdown("Upload new resumes in the `App` page to add them to your database.")