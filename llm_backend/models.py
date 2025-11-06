from pydantic import BaseModel
from typing import List, Optional

class Skill(BaseModel):
    name: str
    level: Optional[str] = "Not specified"

class Experience(BaseModel):
    job_title: str
    company: str
    duration: Optional[str] = "Not specified"
    summary: str

class ParsedResume(BaseModel):
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    summary: str
    skills: List
    experience: List[Experience]

class Input(BaseModel):
    jd: str
    resume: str

class ResumeInput(BaseModel):
    resume_text: str

class JDInput(BaseModel):
    jd: str