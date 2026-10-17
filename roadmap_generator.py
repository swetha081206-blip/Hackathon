"""Personalized learning roadmap generation targeting candidate skill gaps and career roles.
"""

import json
from gemini_service import call_gemini, clean_json_response


def generate_learning_roadmap(
    target_role: str,
    skill_gaps: list[str],
    verified_skills: list[str],
    weeks_count: int = 4,
) -> list[dict]:
    """Generate a step-by-step learning roadmap targeting identified skill gaps."""
    gaps_str = ", ".join(skill_gaps[:5]) if skill_gaps else "advanced software architecture, automated testing, and CI/CD"
    verified_str = ", ".join(verified_skills[:5]) if verified_skills else "general programming fundamentals"

    prompt = f"""You are an encouraging and practical senior engineering mentor.
Create a step-by-step {weeks_count}-week learning roadmap for a student aiming to become a "{target_role}".

TARGET ROLE: {target_role}
CURRENT STRENGTHS: {verified_str}
KEY SKILL GAPS TO BRIDGE: {gaps_str}

REQUIREMENTS:
1. Make tasks realistic and achievable for a motivated beginner or early-career developer.
2. Focus on practical hands-on building, clean documentation, and demonstrable proof.
3. Include real, free learning resources (official docs, free tutorials).
4. Do NOT make unrealistic promises or guarantee employment.

Return ONLY a valid JSON object with a single key "weeks", containing a list of {weeks_count} week objects:
{{
  "weeks": [
    {{
      "week_number": 1,
      "topic": "Core Topic Title",
      "learning_objectives": ["Specific concept 1", "Specific concept 2"],
      "practice_activities": ["Coding exercise 1", "Coding exercise 2"],
      "deliverable_project": "Concrete mini-project or GitHub artifact to build and publish",
      "expected_outcome": "Clear skill gained",
      "free_resources": ["Official Documentation", "FreeCodeCamp tutorial", "MDN Web Docs"]
    }}
  ]
}}
"""
    success, response_text, _ = call_gemini(prompt)
    if success:
        try:
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            if isinstance(data.get("weeks"), list) and len(data["weeks"]) > 0:
                return data["weeks"][:weeks_count]
        except Exception:
            pass

    # Deterministic fallback roadmap tailored to the target role and gaps
    primary_gap = skill_gaps[0] if skill_gaps else "System Architecture"
    secondary_gap = skill_gaps[1] if len(skill_gaps) > 1 else "Testing & CI/CD"
    tertiary_gap = skill_gaps[2] if len(skill_gaps) > 2 else "Database Optimization"

    return [
        {
            "week_number": 1,
            "topic": f"Foundations of {primary_gap} for {target_role}",
            "learning_objectives": [
                f"Master core concepts, syntax, and architectural patterns of {primary_gap}.",
                "Understand common pitfalls, debugging techniques, and best practices.",
            ],
            "practice_activities": [
                f"Complete 5 targeted practice exercises focused on {primary_gap}.",
                "Review open-source codebases demonstrating production patterns.",
            ],
            "deliverable_project": f"Create a GitHub repository with clean code examples demonstrating {primary_gap}.",
            "expected_outcome": f"Confidence explaining and implementing {primary_gap} from scratch.",
            "free_resources": ["Official Documentation", "freeCodeCamp", "roadmap.sh"],
        },
        {
            "week_number": 2,
            "topic": f"Practical Integration: {secondary_gap}",
            "learning_objectives": [
                f"Learn how {secondary_gap} integrates into modern {target_role} workflows.",
                "Build end-to-end data flows with validation and error handling.",
            ],
            "practice_activities": [
                "Implement robust input validation and defensive error handlers.",
                "Set up modular folder structure following industry standards.",
            ],
            "deliverable_project": f"Build a working prototype integrating {primary_gap} and {secondary_gap} with automated tests.",
            "expected_outcome": "Demonstrable capability connecting multiple components into a cohesive application.",
            "free_resources": ["MDN Web Docs", "GitHub Skills", "YouTube Project Tutorials"],
        },
        {
            "week_number": 3,
            "topic": f"Quality, Reliability & {tertiary_gap}",
            "learning_objectives": [
                f"Incorporate {tertiary_gap} into project development.",
                "Write comprehensive unit tests with at least 80% coverage.",
            ],
            "practice_activities": [
                "Write unit tests using PyTest or appropriate framework.",
                "Set up automated GitHub Actions workflow to run linting and tests on every commit.",
            ],
            "deliverable_project": "Publish tested release with GitHub Actions CI badge displayed in the README.",
            "expected_outcome": "Understanding of production code quality and continuous integration.",
            "free_resources": ["Real Python Testing Guide", "GitHub Actions Docs"],
        },
        {
            "week_number": 4,
            "topic": f"Portfolio Polish, Deployment & Interview Readiness",
            "learning_objectives": [
                "Deploy project to a live public URL (Vercel, Render, or Streamlit Cloud).",
                "Craft an engaging README with architecture diagrams and setup instructions.",
                "Prepare concise explanations of technical trade-offs for recruiter conversations.",
            ],
            "practice_activities": [
                "Perform live deployment and verify SSL and responsive layout.",
                "Record a 2-minute video walkthrough or create a visual demo GIF.",
                "Update resume bullet points to showcase measurable outcomes and technologies used.",
            ],
            "deliverable_project": "Live deployed showcase project pinned to GitHub profile and linked on resume.",
            "expected_outcome": "Interview-ready portfolio piece that provides verifiable evidence to hiring teams.",
            "free_resources": ["Render Free Tier Docs", "Vercel Deployment Docs", "STAR Method Interview Guides"],
        },
    ]
