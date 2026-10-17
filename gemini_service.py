"""Gemini AI integration service with multi-model fallback, structured JSON parsing,
and deterministic offline failovers.
"""

import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

# Candidate models in preferred order
SUPPORTED_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]



def get_gemini_client():
    """Safely initialize and return Google GenAI Client if API key is present."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def clean_json_response(raw_text: str) -> str:
    """Extract clean JSON text from possible Markdown formatting."""
    cleaned = raw_text.strip()
    # Strip markdown code fences like ```json ... ```
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()
    return cleaned


def call_gemini(prompt: str, preferred_model: str | None = None) -> tuple[bool, str, str]:
    """Call Gemini with model fallback and error handling.
    
    Returns:
        (success, text_response, model_used_or_error_message)
    """
    client = get_gemini_client()
    if not client:
        return False, "", "GEMINI_API_KEY is not configured or client initialization failed."

    models_to_try = []
    if preferred_model and preferred_model not in models_to_try:
        models_to_try.append(preferred_model)
    for m in SUPPORTED_MODELS:
        if m and m not in models_to_try:
            models_to_try.append(m)

    last_error = ""
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                return True, response.text, model_name
        except Exception as exc:
            last_error = f"{model_name}: {type(exc).__name__} - {str(exc)[:120]}"
            continue

    return False, "", f"All Gemini model attempts failed. Last error: {last_error}"


def extract_resume_with_ai(resume_text: str) -> tuple[dict, str]:
    """Extract structured candidate profile from resume text using Gemini AI."""
    prompt = f"""You are an expert HR and career data extraction specialist.
Analyze the provided resume text and extract only information that is explicitly stated or directly supported.
Do NOT invent candidate details, companies, projects, or statistics.

Return a valid, parseable JSON object with EXACTLY this structure:
{{
  "candidate_name": "Full name or unknown",
  "email": "Email address or null",
  "phone": "Phone number or null",
  "education": [
    {{
      "institution": "University/College name",
      "degree": "Degree name (e.g. B.Tech Computer Science)",
      "graduation_year": "Year or null",
      "gpa_or_percentage": "GPA or null"
    }}
  ],
  "experience": [
    {{
      "role": "Job/Internship Title",
      "company": "Organization name",
      "duration": "Dates or duration",
      "description": "Short factual summary"
    }}
  ],
  "skills": ["List of all technical skills"],
  "programming_languages": ["Languages such as Python, Java, C++, JavaScript"],
  "frameworks_and_tools": ["Frameworks, libraries, and tools such as React, Django, Git, Docker"],
  "projects": [
    {{
      "title": "Project Title",
      "description": "Factual summary of what was built based solely on the resume",
      "technologies": ["List of technologies used"]
    }}
  ],
  "certifications": ["List of certifications or courses mentioned"],
  "achievements": ["List of notable achievements or awards"]
}}

RESUME TEXT:
---BEGIN RESUME---
{resume_text[:18000]}
---END RESUME---
"""
    success, response_text, model_or_err = call_gemini(prompt)
    if success:
        try:
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            # Normalize fields
            data.setdefault("candidate_name", "Unknown Candidate")
            data.setdefault("skills", [])
            data.setdefault("programming_languages", [])
            data.setdefault("frameworks_and_tools", [])
            data.setdefault("projects", [])
            data.setdefault("experience", [])
            data.setdefault("education", [])
            data.setdefault("certifications", [])
            data.setdefault("achievements", [])
            return data, f"Gemini AI ({model_or_err})"
        except Exception as parse_err:
            pass

    return {}, f"Extraction fallback (Gemini unavailable: {model_or_err})"


def generate_recommendations_with_ai(
    target_role: str,
    extracted_data: dict,
    scores: dict,
    gaps: list[str],
    evidence_summary: str,
) -> dict:
    """Generate resume bullet improvements, project suggestions, and career advice."""
    prompt = f"""You are a senior tech career coach. Provide specific, actionable, and truthful career recommendations.
Base your advice directly on the candidate's real claims and evidence provided below. Do not fabricate experience.

TARGET ROLE: {target_role}
READINESS SCORE: {scores.get('overall', 0)}%
SKILL GAPS IDENTIFIED: {json.dumps(gaps)}
CANDIDATE SKILLS: {json.dumps(extracted_data.get('skills', []))}
ONLINE EVIDENCE SUMMARY:
{evidence_summary[:3000]}

Return a valid JSON object with EXACTLY this structure:
{{
  "executive_summary": "2-3 sentences summarizing the candidate's current career readiness and best strengths.",
  "bullet_point_improvements": [
    {{
      "current_or_weak_point": "An example of a generic bullet point typical of this profile",
      "improved_bullet_point": "Stronger action-oriented bullet with measurable impact and context"
    }}
  ],
  "recommended_projects": [
    {{
      "title": "Concrete Project Idea",
      "description": "Specific project to build that addresses one of the key skill gaps",
      "technologies": ["Tech 1", "Tech 2"],
      "learning_outcome": "What recruiters will look for in this project"
    }}
  ],
  "interview_prep_topics": ["Key technical topic 1", "Key technical topic 2", "Key technical topic 3"]
}}
"""
    success, response_text, _ = call_gemini(prompt)
    if success:
        try:
            cleaned = clean_json_response(response_text)
            return json.loads(cleaned)
        except Exception:
            pass

    # Deterministic fallback recommendations
    return {
        "executive_summary": f"Candidate demonstrates foundational competency for {target_role}. Focusing on demonstrating practical implementations of missing role skills ({', '.join(gaps[:3]) if gaps else 'core architecture'}) will significantly enhance recruiter confidence.",
        "bullet_point_improvements": [
            {
                "current_or_weak_point": "Worked on web application using Python and database.",
                "improved_bullet_point": f"Architected scalable REST APIs in Python/SQL, implementing validation, unit tests, and CI/CD pipelines to ensure 99.9% reliability.",
            },
            {
                "current_or_weak_point": "Helped team build frontend features and fixed bugs.",
                "improved_bullet_point": "Engineered responsive, accessible UI components in React/TypeScript, optimizing bundle size and reducing page load latency by 25%.",
            },
        ],
        "recommended_projects": [
            {
                "title": f"Production-Ready {target_role} Showcase",
                "description": f"Build an end-to-end application highlighting {', '.join(gaps[:2]) if gaps else 'API design and testing'}, accompanied by a comprehensive README, live deployment demo, and automated test suite.",
                "technologies": gaps[:3] if gaps else ["Python", "SQL", "Docker"],
                "learning_outcome": "Demonstrates independent engineering rigor, clean documentation, and production readiness.",
            }
        ],
        "interview_prep_topics": [
            "Data structures & algorithmic problem solving",
            "System design basics and RESTful API architecture",
            "Debugging, code quality, and testing methodologies",
        ],
    }
