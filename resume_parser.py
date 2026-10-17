"""Resume PDF text extraction, validation, and structured candidate profile parsing.
"""

from io import BytesIO
import re
from pypdf import PdfReader
from security_utils import validate_pdf_file
from url_detector import extract_urls_from_text
from gemini_service import extract_resume_with_ai


EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}\b")

# Common skill keywords for deterministic fallback
COMMON_TECHNICAL_SKILLS = [
    "Python", "Java", "C++", "C", "C#", "JavaScript", "TypeScript", "Go", "Rust", "Kotlin", "Swift", "PHP", "Ruby", "SQL",
    "HTML", "CSS", "React", "Next.js", "Vue", "Angular", "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring Boot",
    "PostgreSQL", "MySQL", "MongoDB", "SQLite", "Redis", "Firebase",
    "Git", "GitHub", "Docker", "Kubernetes", "Linux", "Bash", "CI/CD", "AWS", "Google Cloud", "GCP", "Azure",
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-Learn",
    "Data Structures", "Algorithms", "OOP", "System Design", "REST API", "GraphQL", "Microservices",
    "Figma", "Excel", "Data Visualization", "Power BI", "Tableau", "Unit Testing", "PyTest"
]


def extract_pdf_raw_text(uploaded_file) -> str:
    """Extract raw text from a PDF file using PyPDF with strict validation and scanned PDF detection."""
    is_valid, msg = validate_pdf_file(uploaded_file)
    if not is_valid:
        raise ValueError(msg)

    try:
        # Seek to start
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        reader = PdfReader(BytesIO(uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("The uploaded PDF is password-protected and cannot be analyzed.")

        pages_text = []
        for page_idx, page in enumerate(reader.pages):
            page_content = page.extract_text() or ""
            pages_text.append(page_content)

        full_text = "\n".join(pages_text).strip()

        # Check for scanned PDF / empty text
        if not full_text or len(re.sub(r"\s+", "", full_text)) < 40:
            raise ValueError(
                "No selectable text was found in this PDF. It appears to be an image-only or scanned document. "
                "Please run Optical Character Recognition (OCR) or upload a text-selectable PDF."
            )

        return full_text

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read the PDF file: {type(exc).__name__} - {exc}")


def rule_based_extract(resume_text: str) -> dict:
    """Deterministic regex-based fallback extractor when AI is unavailable."""
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]

    # Candidate Name heuristic (usually first prominent non-header line without special characters)
    candidate_name = "Candidate"
    for line in lines[:5]:
        if len(line) < 40 and not any(char in line for char in ["@", "http", "www.", "+", "|", ":"]):
            words = line.split()
            if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                candidate_name = line
                break

    # Email
    emails = EMAIL_REGEX.findall(resume_text)
    email = emails[0] if emails else None

    # Phone
    phones = PHONE_REGEX.findall(resume_text)
    phone = phones[0] if phones else None

    # Skills detection
    text_lower = resume_text.lower()
    detected_skills = []
    for skill in COMMON_TECHNICAL_SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"
        if re.search(pattern, text_lower):
            detected_skills.append(skill)

    # Education heuristic
    education = []
    edu_keywords = ["bachelor", "master", "b.tech", "b.e", "b.s", "m.tech", "m.s", "computer science", "engineering", "university", "college", "institute"]
    for line in lines:
        if any(kw in line.lower() for kw in edu_keywords):
            if len(line) < 120:
                education.append({"degree": line, "institution": "", "graduation_year": None})

    # Projects heuristic (lines following "Project" or "Projects")
    projects = []
    in_project_section = False
    for line in lines:
        if re.search(r"^(?:projects?|academic projects?)\b", line, re.IGNORECASE):
            in_project_section = True
            continue
        elif in_project_section and re.search(r"^(?:skills?|education|experience|certifications?|achievements?)\b", line, re.IGNORECASE):
            in_project_section = False
        elif in_project_section and len(line) > 10 and not line.startswith("http"):
            if len(projects) < 5:
                projects.append({"title": line[:50], "description": line, "technologies": []})

    return {
        "candidate_name": candidate_name,
        "email": email,
        "phone": phone,
        "skills": detected_skills,
        "programming_languages": [s for s in detected_skills if s in ["Python", "Java", "C++", "C", "C#", "JavaScript", "TypeScript", "Go", "Rust", "SQL"]],
        "frameworks_and_tools": [s for s in detected_skills if s not in ["Python", "Java", "C++", "C", "C#", "JavaScript", "TypeScript", "Go", "Rust", "SQL"]],
        "education": education[:3],
        "experience": [],
        "projects": projects[:4],
        "certifications": [],
        "achievements": [],
    }


def parse_resume(uploaded_file) -> dict:
    """Parse resume PDF into raw text, detected URLs, and structured candidate profile."""
    raw_text = extract_pdf_raw_text(uploaded_file)
    detected_urls = extract_urls_from_text(raw_text)

    # Attempt AI structured extraction
    ai_profile, extraction_method = extract_resume_with_ai(raw_text)

    if ai_profile and ai_profile.get("skills"):
        profile = ai_profile
    else:
        # Fall back to deterministic extraction
        profile = rule_based_extract(raw_text)
        extraction_method = "Deterministic Rules (Keyword & Pattern Parser)"

    # Ensure all skills are deduplicated and merged with languages & frameworks
    all_skills = list(profile.get("skills", []))
    for s in profile.get("programming_languages", []) + profile.get("frameworks_and_tools", []):
        if s not in all_skills:
            all_skills.append(s)
    profile["skills"] = all_skills

    return {
        "raw_text": raw_text,
        "detected_urls": detected_urls,
        "profile": profile,
        "extraction_method": extraction_method,
    }
