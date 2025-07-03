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
