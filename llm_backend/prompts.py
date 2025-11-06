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

def parse_resume_prompt(resume_text: str) -> str:
    return f"""
    You are an expert resume parsing system.
    Analyze the following resume text:
    ---
    {resume_text}
    ---
    Extract the following information and structure it as a JSON object:
    - full_name: The candidate's full name.
    - email: The candidate's email address.
    - phone: The candidate's phone number.
    - summary: A brief 2-3 sentence summary of the candidate's professional profile.
    - skills: A list of key technical skills, with an optional level (e.g., "Python", "React").
    - experience: A list of the candidate's most recent job experiences, including title, company, duration, and a summary.

    Return ONLY the JSON object.
    """

def job_seeker_prompt(jd_text: str, resume_text: str) -> str:
    return f"""
    You are an expert career coach and professional resume writer.
    Given the following **Target Job Description**:
    ---
    {jd_text}
    ---
    And the following **Candidate Resume**:
    ---
    {resume_text}
    ---
    Provide actionable, specific advice on how to improve the resume to
    better match this job. Focus on:
    1.  **Keyword Gaps:** What keywords from the JD are missing in the resume?
    2.  **Framing Experience:** How can the existing experience be re-phrased
        to highlight alignment with the JD's responsibilities?
    3.  **Skills to Add:** What skills are implied by the JD that
        the candidate might have but hasn't listed?

    Give your feedback in helpful, encouraging markdown format.
    """