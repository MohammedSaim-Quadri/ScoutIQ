"""
Utility functions for response parsing and LLM interactions
"""
import re
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from groq import RateLimitError

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, ConnectionError, TimeoutError)),
    reraise=True
)
async def call_llm_with_retry(llm, prompt: str):
    """
    Wrapper function that retries LLM calls on failure.
    
    Retry strategy:
    - Retries 3 times
    - Exponential backoff: 2s, 4s, 8s
    - Only retries on rate limits, connection errors, timeouts
    
    Args:
        llm: LLM client (ChatGroq or structured LLM)
        prompt: The prompt to send
        
    Returns:
        LLM response object
    """
    logger.info("Calling LLM...")
    response = await llm.ainvoke(prompt)
    logger.info("LLM response received")
    return response


def parse_pro_response(raw_output: str) -> dict:
    """
    Parses the combined Pro response into structured sections
    
    Extracts:
    - Interview questions (technical, behavioral, followup)
    - Insight summary
    - Skill gaps
    
    Args:
        raw_output: Raw LLM response text
        
    Returns:
        Dict with parsed sections
    """
    # Extract questions
    questions = clean_response(raw_output)
    
    # Extract insight summary
    insight_match = re.search(
        r"===INSIGHT SUMMARY===(.*?)(?:===SKILL GAPS===|$)", 
        raw_output, 
        re.DOTALL
    )
    insight_summary = insight_match.group(1).strip() if insight_match else None
    
    # Extract skill gaps
    skill_gaps_match = re.search(
        r"===SKILL GAPS===(.*?)$", 
        raw_output, 
        re.DOTALL
    )
    skill_gaps = skill_gaps_match.group(1).strip() if skill_gaps_match else None
    
    return {
        "technical": questions["technical"],
        "behavioral": questions["behavioral"],
        "followup": questions["followup"],
        "insight_summary": insight_summary,
        "skill_gaps": skill_gaps
    }


def extract_section(text: str, section_type: str) -> list:
    """
    Extract specific question section from LLM response
    
    Args:
        text: Raw LLM response
        section_type: Type of section ('technical', 'behavioral', 'followup')
        
    Returns:
        List of questions
    """
    cleaned = clean_response(text)
    return cleaned.get(section_type, [])


def clean_response(raw_output: str) -> dict:
    """
    Parse LLM response into structured question sections
    
    Handles various formatting quirks:
    - Removes markdown code blocks
    - Handles different section label formats
    - Extracts bulleted/numbered lists
    
    Args:
        raw_output: Raw LLM response text
        
    Returns:
        Dict with technical, behavioral, and followup questions
    """
    raw_output = raw_output.replace("\\n", "\n").replace("```", "").strip()
    
    sections = re.split(
        r"(?i)^\s*(technical questions|behavioral questions|red flag\s*/\s*follow[- ]?up questions)[::]\s*$", 
        raw_output, 
        flags=re.MULTILINE
    )
    
    result = {"technical": [], "behavioral": [], "followup": []}
    
    if len(sections) < 2:
        logger.warning("Could not parse LLM response sections")
        return result

    label_map = {
        "technical questions": "technical",
        "behavioral questions": "behavioral",
        "red flag / follow-up questions": "followup",
        "red flag/ follow-up questions": "followup",
        "red flag/follow-up questions": "followup",
        "red flag-follow-up questions": "followup",
    }

    for i in range(1, len(sections), 2):
        label = sections[i].strip().lower()
        questions_block = sections[i + 1].strip()
        key = label_map.get(label)
        
        if not key:
            logger.warning(f"Unknown section label: {label}")
            continue
            
        questions = re.findall(r"[-•]\s+(.*)", questions_block)
        result[key] = questions

    return result