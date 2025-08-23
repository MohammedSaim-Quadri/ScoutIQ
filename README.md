# 🚀 ScoutIQ
**Recruiter-Focused AI Tool – Work in Progress**

ScoutIQ is an AI-powered SaaS platform that helps **recruiters, founders, and job seekers** generate high-quality, role-specific interview questions, analyze resumes against job descriptions, and uncover candidate insights in seconds.  

Built with **Python, FastAPI, Streamlit, Firebase, and LLMs**, ScoutIQ is designed to save time in candidate evaluation and improve hiring decisions.

---

## ✨ Features

- **AI-Generated Interview Questions**
  - Technical, behavioral, and follow-up/red-flag questions.
  - Role-specific and resume-tailored.

- **Candidate Insights (Pro Feature)**
  - Resume & Job Description (JD) summary.
  - Strengths and weaknesses analysis.
  - Skill gap highlights.

- **Tier-Based Access**
  - Free: 3 generations/month + PDF export.
  - Pro Monthly: Unlimited generations.
  - Pro Yearly: Unlimited + early feature access.
  - Lifetime: All features unlocked forever.

- **PDF Export**
  - Download generated questions as a structured PDF.

- **Secure Authentication**
  - Firebase-based login, signup, and password reset.

- **Scalable Architecture**
  - Streamlit frontend for recruiters.
  - FastAPI backend with structured logging.
  - LLM-powered question generation via Together API/Ollama.
  - Firebase for user management & usage tracking.
  - Qdrant for vector search (future extension).

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit  
- **Backend:** FastAPI, Uvicorn  
- **Database & Auth:** Firebase Firestore & Firebase Auth  
- **LLM Integration:** Together API (Llama 3.3) / Ollama (private service)  
- **Vector Search:** Qdrant (planned)  
- **Payments:** Gumroad integration (via webhook)  
- **Deployment:** Render, Docker  

---

## 📂 Project Structure
```
scoutiq/
├── Home.py # Landing page (Streamlit)
|
├── pages/ # Streamlit multi-page setup
│ ├── App.py # Main recruiter app (interview generator)
│ ├── Pricing.py # Pricing & plans
|
├── app/ # Core app logic
│ ├── generator.py # LLM request handling
│ ├── ui.py # Streamlit UI logic
│ ├── usage_tracker.py # Daily usage tracking
│ └── auth/ # Firebase authentication
|
├── llm_backend/ # FastAPI backend for LLM integration
│ ├── main.py # API routes (/generate, /insight-summary, /skill-gap)
│ └── prompts.py # Prompt templates
|
├── webhook.py # Gumroad webhook for payment integration
├── requirements.txt # Python dependencies
├── render.yaml # Render.com deployment config
└── README.md # Project documentation
```

---

## Getting Started

### Clone the Repository
```bash
git clone https://github.com/your-username/scoutiq.git
cd scoutiq
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Set Environment Variables
```bash
Create a .env file with:

FIREBASE_WEB_API_KEY=your_firebase_web_key
TOGETHER_API_KEY=your_together_api_key
EMAIL_PASSWORD=your_email_password
GMAIL_USER=your_email@gmail.com
GUMROAD_SECRET=your_gumroad_webhook_secret
```

Also add your firebase-service-key.json for Firebase Admin SDK.

### Run the Backend
```bash
uvicorn llm_backend.main:app --reload --port 8000
```

### Run the Frontend
```bash
streamlit run Home.py
```

---
## Example Usage

- Paste a Job Description.
- Upload or paste a Candidate Resume.
- Click Generate Questions.
- Get tailored technical, behavioral, and follow-up questions.
- (Pro users) View insight summaries & skill gap analysis.
- Export results as a PDF.

---
## Pricing (via Gumroad)

- Free: 3 generations/month.
- Pro Monthly: $12/month → Subscribe
- Pro Yearly: $120/year → Subscribe
- Lifetime: $250 one-time → Buy Lifetime Access
---

## Roadmap

- [x] AI-powered interview question generator  
- [x] Firebase auth & Pro tiering  
- [x] Gumroad payment integration  
- [x] Streamlit multi-page app  
- [ ] Vector search with Qdrant for candidate ranking  
- [ ] Admin dashboard for recruiters  
- [ ] Multi-language support  
- [ ] Resume parsing & scoring engine  

---
🤝 Contributing

Contributions are welcome! Please fork the repo and submit a pull request.
If you have ideas, feature requests, or bug reports, open an issue.

---
📜 License

This project is licensed under the MIT License – see the LICENSE
 file for details.
