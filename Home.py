import streamlit as st

st.set_page_config(page_title="ScoutIQ - AI Interview Questions", layout ="centered")

st.title("Welcome to ScoutIQ!")
st.subheader("AI-powered Interview Question Generator")

st.markdown("""
ScoutIQ helps **founders**, **recruiters**, and **job seekers** instantly generate high-quality, role-specific interview questions using AI.

### 🚀 How It Works:
1. Paste a **Job Description**
2. Upload or paste a **Candidate Resume**
3. Get **tailored technical, behavioral, and red flag questions** in seconds!

---

### 💎 Pricing
| Tier       | Features                                    |
|------------|---------------------------------------------|
| **Free**   | 3 generations/month, PDF export             |
| **Pro**    | Unlimited generations, priority support     |

---

### 🔐 Ready to get started?

Click below to log in and launch the app.
""")

st.page_link("pages/Recruiter_Mode.py", label="Launch ScoutIQ App", icon="💻")
with st.sidebar:
    st.markdown("👋 Not a Pro user yet?")
    st.page_link("pages/Pricing.py", label="💎 Upgrade to Pro")
