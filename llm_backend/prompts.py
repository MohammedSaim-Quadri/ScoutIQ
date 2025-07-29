def question_prompt(jd_text:str, resume_text:str) -> str:
    return f"""
You are an expert technical recruiter.

Given the following job description:
{jd_text}

And the following candidate resume:
{resume_text}

Generate:
- 5 **Technical Interview Questions**
- 3 **Behavioral Interview Questions**
- 2 **Red Flag or Follow-Up Questions** based on mismatches or missing info

⚠️ Format requirements:
- Start each section with these exact labels:
  - Technical Questions:
  - Behavioral Questions:
  - Red Flag / Follow-Up Questions:
- Each question should start with a dash (-) or bullet (•), one per line.
- Do not include explanations or guidance — just the questions in the correct sections.
- ⚠️ Do not repeat any section. Stop after generating these 10 questions.
"""

def insight_summary_prompt(jd_text: str, resume_text: str) -> str:
    return f"""
You are a senior technical recruiter.

Given the following **Job Description**:
{jd_text}

And the following **Candidate Resume**:
{resume_text}

Write a concise insight summary that answers:
1. How well does the resume match the JD?
2. What are the candidate's strengths for this role?
3. What skills or qualifications seem missing or weak?

Use simple language. Keep it brief — ideally 3 short paragraphs.
Do not repeat the JD or resume. Just the insights.
"""

def build_skill_gap_prompt(jd_text: str, resume_text: str) -> str:
    return f"""
You're an expert technical hiring analyst.

Given the following **Job Description**:
{jd_text}

And the following **Candidate Resume**:
{resume_text}

Identify and list key **skill gaps or mismatches** between the job requirements and the resume.

Respond with bullet points that highlight:
- Missing technical or domain-specific skills
- Outdated tools or experience
- Lack of required certifications, experience level, or methodologies

🛑 DO NOT include skills the candidate already has. Only include CRITICAL mismatches.

Respond in this format:
Skill Gap Highlights:
- ...
- ...
- ...

Avoid long paragraphs. Use concise bullets.
"""