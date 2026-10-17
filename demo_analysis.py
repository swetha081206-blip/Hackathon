"""End-to-end demonstration showing complete analyzer output:
- Extracted Resume Profile
- Detected Online Profiles
- Repository Provenance & Anti-Clone Findings
- Tri-Factor Separate Scores
- Resume Claim Verification Table
- Practical Skill Verification & Code Review
- Personalized 4-Week Learning Roadmap
- Generated PDF Report file
"""

import json
import os
from datetime import datetime, timezone
from skill_matcher import verify_resume_claims, calculate_career_readiness
from project_provenance import calculate_project_ownership_score
from report_generator import generate_pdf_report

print("=" * 70)
print("DEMONSTRATION RUN: CAREER READINESS & PROVENANCE ANALYZER")
print("=" * 70)

# Sample candidate data
candidate_name = "Sarah Chen"
target_role = "Python Developer"
role_skills = ["Python", "OOP", "Git", "SQL", "Testing", "REST API", "Data Structures"]

claimed_skills = [
    "Python", "OOP", "FastAPI", "SQL", "PostgreSQL", "Git",
    "Data Structures", "Docker", "PyTest", "REST API", "JavaScript"
]

detected_urls = [
    {"platform": "GitHub", "type": "Profile", "url": "https://github.com/sarah-chen", "status": "Verified (HTTP 200 OK)"},
    {"platform": "GitHub", "type": "Repository", "url": "https://github.com/sarah-chen/ecommerce-api", "status": "Verified (HTTP 200 OK)"},
    {"platform": "LeetCode", "type": "Profile", "url": "https://leetcode.com/u/sarah_codes", "status": "Verified (HTTP 200 OK)"},
    {"platform": "Codeforces", "type": "Profile", "url": "https://codeforces.com/profile/sarah_c", "status": "Verified (HTTP 200 OK)"},
    {"platform": "Personal Portfolio", "type": "Portfolio Website", "url": "https://sarahchen.dev", "status": "Verified (HTTP 200 OK)"},
]

# Provenance analysis on candidate's repositories
provenance_list = [
    {
        "repository_name": "ecommerce-api",
        "repo_url": "https://github.com/sarah-chen/ecommerce-api",
        "is_fork": False,
        "created_at": "2025-08-10T14:30:00Z",
        "updated_at": "2026-03-12T09:15:00Z",
        "total_commits_inspected": 30,
        "candidate_authored_commits": 28,
        "candidate_commit_ratio": 0.93,
        "is_single_commit_import": False,
        "template_matches": [],
        "ownership_status": "Strong supporting evidence",
        "supporting_evidence": ["Original repository with 28 iterative commits authored by candidate."],
        "potential_concerns": [],
    },
    {
        "repository_name": "distributed-task-worker",
        "repo_url": "https://github.com/sarah-chen/distributed-task-worker",
        "is_fork": False,
        "created_at": "2025-11-04T18:20:00Z",
        "updated_at": "2026-02-28T16:40:00Z",
        "total_commits_inspected": 18,
        "candidate_authored_commits": 16,
        "candidate_commit_ratio": 0.89,
        "is_single_commit_import": False,
        "template_matches": [],
        "ownership_status": "Strong supporting evidence",
        "supporting_evidence": ["Iterative multi-commit history with comprehensive README."],
        "potential_concerns": [],
    },
    {
        "repository_name": "react-admin-dashboard",
        "repo_url": "https://github.com/sarah-chen/react-admin-dashboard",
        "is_fork": True,
        "parent_repo": {"full_name": "themefisher/react-dashboard-free"},
        "created_at": "2026-01-15T11:00:00Z",
        "updated_at": "2026-01-20T10:00:00Z",
        "total_commits_inspected": 5,
        "candidate_authored_commits": 3,
        "candidate_commit_ratio": 0.60,
        "is_single_commit_import": False,
        "template_matches": [{"template_name": "Vite + React Starter"}],
        "ownership_status": "Some supporting evidence",
        "supporting_evidence": ["Candidate added 3 custom commits over upstream parent."],
        "potential_concerns": ["Forked from themefisher/react-dashboard-free."],
    },
]

ownership_score_data = calculate_project_ownership_score(provenance_list)

# Mock platform evidence
mock_evidence = [
    {
        "platform": "GitHub",
        "status": "Verified",
        "url": "https://github.com/sarah-chen",
        "languages": ["Python", "SQL", "JavaScript", "HTML", "Docker"],
        "recent_activity_count": 3,
        "repositories": [
            {
                "name": "ecommerce-api",
                "description": "Production REST API with FastAPI, PostgreSQL, and PyTest.",
                "languages": ["Python", "SQL"],
                "topics": ["fastapi", "postgresql", "docker", "testing"],
                "readme": "Production eCommerce REST API architecture with JWT authentication and Docker setup.",
                "url": "https://github.com/sarah-chen/ecommerce-api",
                "latest_commit": "2026-03-12T09:15:00Z",
            },
            {
                "name": "distributed-task-worker",
                "description": "Celery and Redis task queue with OOP patterns.",
                "languages": ["Python"],
                "topics": ["redis", "celery", "python"],
                "readme": "Background job queue processor demonstrating OOP abstractions.",
                "url": "https://github.com/sarah-chen/distributed-task-worker",
                "latest_commit": "2026-02-28T16:40:00Z",
            },
        ],
        "project_ownership": ownership_score_data,
        "provenance_list": provenance_list,
    },
    {
        "platform": "LeetCode",
        "status": "Verified",
        "url": "https://leetcode.com/u/sarah_codes",
        "total_solved": 142,
        "easy_solved": 60,
        "medium_solved": 72,
        "hard_solved": 10,
    },
    {
        "platform": "Codeforces",
        "status": "Verified",
        "url": "https://codeforces.com/profile/sarah_c",
        "rating": 1450,
        "rank": "specialist",
        "problems_solved": 85,
    },
]

vrows = verify_resume_claims(claimed_skills, mock_evidence)

practical_eval = {
    "completed": True,
    "practical_score": 88,
    "status_summary": "Strong Practical Competency",
    "overall_feedback": "Candidate accurately described the JWT auth flow and wrote clean, defensive input validation with exception handling.",
}

scores = calculate_career_readiness(
    verification_rows=vrows,
    target_role=target_role,
    role_skills=role_skills,
    platform_evidence=mock_evidence,
    profile_data={
        "candidate_name": candidate_name,
        "education": [{"degree": "B.S. in Computer Science"}],
        "projects": [{"title": "eCommerce API"}],
    },
    practical_result=practical_eval,
)

print(f"\nCandidate: {candidate_name}")
print(f"Target Role: {target_role}")
print("-" * 70)
print(f"TRI-FACTOR SEPARATE SCORES:")
print(f"  [A] Career Readiness Score:        {scores['career_readiness_score']}% (Target role match & verified skills)")
print(f"  [B] Project Ownership Evidence:    {scores['ownership_evidence_score']}% ({scores['ownership_data']['status_label']})")
print(f"  [C] Practical Skill Verification:  {scores['practical_verification_score']}% ({practical_eval['status_summary']})")
print("-" * 70)

print("\nREPOSITORY PROVENANCE FINDINGS:")
for p in provenance_list:
    fork_lbl = f"Fork of {p['parent_repo']['full_name']}" if p['is_fork'] else "Original (Non-fork)"
    print(f"  • {p['repository_name']:<25} | {fork_lbl:<30} | Commits: {p['candidate_authored_commits']}/{p['total_commits_inspected']} ({int(p['candidate_commit_ratio']*100)}%) | Status: {p['ownership_status']}")

print("\nRESUME CLAIM VERIFICATION SUMMARY:")
for r in vrows[:6]:
    print(f"  • {r['skill']:<18} | Status: {r['status']:<20} | Evidence: {r['evidence_snippet'][:45]}...")

# Generate PDF report
full_result = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "target_role": target_role,
    "role_required_skills": role_skills,
    "candidate_profile": {
        "candidate_name": candidate_name,
        "skills": claimed_skills,
        "education": [{"degree": "B.S. Computer Science"}],
    },
    "detected_urls": detected_urls,
    "platform_evidence": mock_evidence,
    "provenance_list": provenance_list,
    "verification": vrows,
    "scores": scores,
    "recommendations": {
        "executive_summary": "Strong candidate with demonstrable Python and SQL experience. High project authenticity verified.",
        "recommended_projects": [
            {"title": "Production Microservice", "technologies": ["Python", "Docker"], "description": "Add automated CI/CD and metrics."}
        ],
        "bullet_point_improvements": [
            {"current_or_weak_point": "Built an API with FastAPI", "improved_bullet_point": "Engineered asynchronous REST API in FastAPI with PostgreSQL, achieving 99.8% uptime."}
        ],
    },
    "roadmap": [
        {"week_number": 1, "topic": "Advanced PyTest & Mocks", "deliverable_project": "Test suite with 90% coverage"},
        {"week_number": 2, "topic": "Docker Multi-stage Builds", "deliverable_project": "Optimized container image"},
        {"week_number": 3, "topic": "Database Indexing & Query Tuning", "deliverable_project": "Benchmarked SQL queries"},
        {"week_number": 4, "topic": "CI/CD & Live Deployment", "deliverable_project": "GitHub Actions pipeline on Render"},
    ],
}

pdf_bytes = generate_pdf_report(full_result)
output_pdf_path = os.path.join(os.path.dirname(__file__), "demo_career_readiness_report.pdf")
with open(output_pdf_path, "wb") as f:
    f.write(pdf_bytes)

print(f"\nPDF Report Generated Successfully: {output_pdf_path} ({len(pdf_bytes)} bytes)")
print("=" * 70)
