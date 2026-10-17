"""Skill normalization, claim verification against gathered evidence, role matching,
and explainable career readiness scoring.
"""

import json
import os
import re

# Comprehensive skill aliases mapping variant terms to canonical skill names
SKILL_ALIASES = {
    "py": "Python",
    "python3": "Python",
    "python 3": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "html5": "HTML",
    "css3": "CSS",
    "react.js": "React",
    "reactjs": "React",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "node": "Node.js",
    "nodejs": "Node.js",
    "postgresql": "SQL",
    "postgres": "SQL",
    "mysql": "SQL",
    "sqlite": "SQL",
    "sql server": "SQL",
    "nosql": "NoSQL",
    "mongodb": "MongoDB",
    "scikit-learn": "Machine Learning",
    "sklearn": "Machine Learning",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "deep-learning": "Deep Learning",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "figma": "Figma",
    "restful api": "REST API",
    "rest apis": "REST API",
    "rest": "REST API",
    "data structures and algorithms": "Data Structures",
    "dsa": "Data Structures",
    "algorithms": "Algorithms",
    "algo": "Algorithms",
    "object oriented programming": "OOP",
    "object-oriented programming": "OOP",
    "oops": "OOP",
    "ms excel": "Excel",
    "excel": "Excel",
    "docker container": "Docker",
    "k8s": "Kubernetes",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "aws cloud": "AWS",
    "amazon web services": "AWS",
    "google cloud platform": "GCP",
    "spring": "Spring Boot",
    "springboot": "Spring Boot",
}


def normalize_skill_name(skill: str) -> str:
    """Normalize skill name to standard canonical format."""
    if not skill:
        return ""
    clean = re.sub(r"\s+", " ", str(skill)).strip()
    key = clean.lower()
    return SKILL_ALIASES.get(key, clean)


def load_roles() -> dict:
    """Load target career roles from roles.json with fallback."""
    roles_file = os.path.join(os.path.dirname(__file__), "roles.json")
    if os.path.exists(roles_file):
        try:
            with open(roles_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "Software Engineer": ["Data Structures", "Algorithms", "OOP", "Git", "SQL", "Testing", "REST API"],
        "Python Developer": ["Python", "OOP", "Git", "SQL", "Testing", "REST API", "Data Structures"],
        "Java Developer": ["Java", "OOP", "Data Structures", "SQL", "Git", "Testing", "Spring Boot"],
        "Frontend Developer": ["HTML", "CSS", "JavaScript", "React", "TypeScript", "Git", "REST API"],
        "Backend Developer": ["Python", "Java", "SQL", "REST API", "Git", "Data Structures", "Docker"],
        "Full-Stack Developer": ["HTML", "CSS", "JavaScript", "React", "Node.js", "SQL", "Git", "REST API"],
        "Data Analyst": ["Python", "SQL", "Excel", "Pandas", "Data Visualization", "Statistics"],
        "Data Scientist": ["Python", "Pandas", "Machine Learning", "SQL", "Statistics", "Data Visualization"],
        "Machine Learning Engineer": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Git"],
        "DevOps Engineer": ["Linux", "Docker", "Kubernetes", "CI/CD", "Git", "AWS", "Python"],
        "UI/UX Designer": ["Figma", "Wireframing", "Prototyping", "User Research", "Accessibility"],
    }


def verify_resume_claims(claimed_skills: list[str], platform_evidence: list[dict]) -> list[dict]:
    """Compare resume skill claims against evidence gathered across all platforms."""
    # Build searchable indices from evidence
    github_languages = set()
    github_repos = []
    github_status = "Not Checked"
    github_url = ""

    leetcode_data = None
    codeforces_data = None
    hackerrank_data = None
    live_demo_tech = set()
    portfolio_url = ""

    for item in platform_evidence:
        plat = item.get("platform")
        status = item.get("status")

        if plat == "GitHub":
            github_status = status
            github_url = item.get("url", "")
            for lang in item.get("languages", []):
                github_languages.add(normalize_skill_name(lang).lower())
            github_repos = item.get("repositories", [])
        elif plat == "LeetCode":
            leetcode_data = item
        elif plat == "Codeforces":
            codeforces_data = item
        elif plat == "HackerRank":
            hackerrank_data = item
        elif plat == "Web Project / Verification" or item.get("type") in ("Live Demonstration", "Portfolio Website"):
            for t in item.get("technologies_detected", []):
                live_demo_tech.add(normalize_skill_name(t).lower())
            if not portfolio_url and item.get("url"):
                portfolio_url = item.get("url")

    # Coding platforms solved counts
    total_dsa_problems = 0
    if leetcode_data and leetcode_data.get("status") == "Verified":
        total_dsa_problems += leetcode_data.get("total_solved", 0)
    if codeforces_data and codeforces_data.get("status") == "Verified":
        total_dsa_problems += codeforces_data.get("problems_solved", 0)

    verification_table = []

    for raw_skill in claimed_skills:
        skill = normalize_skill_name(raw_skill)
        skill_lower = skill.lower()

        matched_sources = []
        source_urls = []
        evidence_snippets = []

        # 1. Check GitHub language list
        is_gh_lang = skill_lower in github_languages

        # 2. Check GitHub repository names, descriptions, topics, and READMEs
        matched_repos = []
        for repo in github_repos:
            searchable = " ".join([
                repo.get("name", ""),
                repo.get("description", ""),
                " ".join(repo.get("topics", [])),
                " ".join(repo.get("languages", [])),
                repo.get("readme", "")[:1000],
            ]).lower()

            if skill_lower in searchable:
                matched_repos.append(repo)
            elif skill_lower == "javascript" and "js" in searchable:
                matched_repos.append(repo)
            elif skill_lower == "machine learning" and ("ml" in searchable or "scikit" in searchable):
                matched_repos.append(repo)

        if is_gh_lang:
            matched_sources.append("GitHub Languages")
            if github_url and github_url not in source_urls:
                source_urls.append(github_url)
            evidence_snippets.append(f"Official language detected across candidate's public repositories.")

        if matched_repos:
            matched_sources.append(f"{len(matched_repos)} GitHub Repositories")
            repo_names = [r["name"] for r in matched_repos[:3]]
            evidence_snippets.append(f"Demonstrated in repository code & documentation: {', '.join(repo_names)}.")
            for r in matched_repos[:2]:
                if r.get("url") and r["url"] not in source_urls:
                    source_urls.append(r["url"])

        # 3. Check DSA / Problem Solving claims against LeetCode/Codeforces
        is_dsa_skill = skill_lower in ("data structures", "algorithms", "dsa", "problem solving", "competitive programming")
        if is_dsa_skill:
            if total_dsa_problems > 0:
                matched_sources.append("Coding Platform Evidence")
                evidence_snippets.append(f"Verified {total_dsa_problems} problem solutions recorded on LeetCode/Codeforces.")
                if leetcode_data and leetcode_data.get("url"):
                    source_urls.append(leetcode_data["url"])
                if codeforces_data and codeforces_data.get("url"):
                    source_urls.append(codeforces_data["url"])

        # 4. Check Web / Live Project Demos
        if skill_lower in live_demo_tech:
            matched_sources.append("Live Web Application")
            evidence_snippets.append(f"Detected running in deployed project demonstration.")
            if portfolio_url and portfolio_url not in source_urls:
                source_urls.append(portfolio_url)

        # Determine Verification Status & Confidence
        if matched_sources and len(matched_sources) >= 2:
            status = "Supported"
            confidence = "High"
            explanation = "Direct evidence found across multiple public repositories, languages, or deployed projects."
            next_action = "Maintain code documentation and highlight key achievements in resume bullets."
        elif matched_sources:
            status = "Partially Supported"
            confidence = "Medium"
            explanation = f"Found relevant evidence in: {', '.join(matched_sources)}, but repository depth or documentation is limited."
            next_action = "Add unit tests, detailed README setup steps, or publish a live demo link."
        elif github_status in ("Rate Limited", "Timeout", "Restricted"):
            status = "Unable to Check"
            confidence = "Low"
            explanation = f"Could not verify claim due to external platform restrictions ({github_status})."
            next_action = "Verify public profile settings or provide an optional personal access token."
        else:
            status = "Not Verified"
            confidence = "Low"
            explanation = "No public repository, platform stats, or project evidence was found matching this skill."
            next_action = f"Build and publish a small open-source project or notebook demonstrating practical use of {skill}."

        verification_table.append({
            "skill": skill,
            "resume_source": "Resume Skills Section",
            "evidence_sources": matched_sources,
            "evidence_snippet": " ".join(evidence_snippets) if evidence_snippets else "No matching public evidence retrieved.",
            "source_urls": source_urls,
            "status": status,
            "confidence": confidence,
            "explanation": explanation,
            "suggested_next_action": next_action,
        })

    return verification_table


def calculate_career_readiness(
    verification_rows: list[dict],
    target_role: str,
    role_skills: list[str],
    platform_evidence: list[dict],
    profile_data: dict,
    practical_result: dict | None = None,
    **kwargs,
) -> dict:


    """Calculate reproducible, explainable career readiness score with transparent weights."""
    norm_role_skills = [normalize_skill_name(s) for s in role_skills]
    claimed_skills = [r["skill"] for r in verification_rows]
    claimed_set = {s.lower() for s in claimed_skills}

    # 1. Verified Evidence Score (40% Weight)
    # Supported = 1.0, Partially Supported = 0.5
    total_claims = len(verification_rows)
    supported_count = sum(1 for r in verification_rows if r["status"] == "Supported")
    partial_count = sum(1 for r in verification_rows if r["status"] == "Partially Supported")
    not_verified_count = sum(1 for r in verification_rows if r["status"] == "Not Verified")
    unable_count = sum(1 for r in verification_rows if r["status"] == "Unable to Check")

    if total_claims > 0:
        verified_evidence_score = ((supported_count * 1.0 + partial_count * 0.5) / total_claims) * 100
    else:
        verified_evidence_score = 0.0

    # 2. Target Role Fit Score (30% Weight)
    matched_role_skills = []
    missing_role_skills = []
    for req in norm_role_skills:
        req_lower = req.lower()
        if req_lower in claimed_set:
            matched_role_skills.append(req)
        else:
            missing_role_skills.append(req)

    role_fit_score = (len(matched_role_skills) / len(norm_role_skills) * 100) if norm_role_skills else 0.0

    # 3. Project Evidence Score (15% Weight)
    # Measures active repositories, descriptions, and recency
    github_item = next((item for item in platform_evidence if item.get("platform") == "GitHub"), {})
    repos = github_item.get("repositories", [])
    recent_activity = github_item.get("recent_activity_count", 0)

    repo_count_pts = min(40, len(repos) * 10)  # up to 4 repos
    recent_pts = min(40, recent_activity * 20)  # up to 2 active recently
    readme_pts = min(20, sum(5 for r in repos if len(r.get("readme", "")) > 100))  # documentation depth
    project_score = min(100, repo_count_pts + recent_pts + readme_pts)

    # 4. Coding Practice & Problem Solving (10% Weight)
    leetcode_item = next((item for item in platform_evidence if item.get("platform") == "LeetCode"), {})
    codeforces_item = next((item for item in platform_evidence if item.get("platform") == "Codeforces"), {})
    hackerrank_item = next((item for item in platform_evidence if item.get("platform") == "HackerRank"), {})

    solved = leetcode_item.get("total_solved", 0) + codeforces_item.get("problems_solved", 0)
    badges = len(hackerrank_item.get("badges", []))
    coding_score = min(100, (solved * 2) + (badges * 15))
    if coding_score == 0 and ("Data Structures" in claimed_set or "Algorithms" in claimed_set):
        # Baseline if DSA is claimed but external platforms are restricted
        coding_score = 25.0

    # 5. Profile & Portfolio Completeness (5% Weight)
    completeness_pts = 0
    if github_item.get("status") == "Verified":
        completeness_pts += 30
    if leetcode_item.get("status") == "Verified" or codeforces_item.get("status") == "Verified":
        completeness_pts += 20
    if any(item.get("type") in ("Portfolio Website", "Live Demonstration") for item in platform_evidence):
        completeness_pts += 30
    if profile_data.get("education"):
        completeness_pts += 10
    if profile_data.get("projects"):
        completeness_pts += 10
    profile_completeness_score = min(100, completeness_pts)

    # Weighted Overall Calculation
    overall = round(
        (0.40 * verified_evidence_score)
        + (0.30 * role_fit_score)
        + (0.15 * project_score)
        + (0.10 * coding_score)
        + (0.05 * profile_completeness_score)
    )

    # Extract Project Ownership Evidence from platform evidence
    github_ownership = github_item.get("project_ownership", {})

    if not github_ownership and github_item.get("provenance_list"):
        from project_provenance import calculate_project_ownership_score
        github_ownership = calculate_project_ownership_score(github_item.get("provenance_list", []))
    elif not github_ownership:
        github_ownership = {
            "score": 50,
            "status_label": "Neutral / Unverified",
            "summary_findings": "No public GitHub repositories were available for commit-level provenance inspection.",
            "formula_explanation": "Evaluates commit authorship ratio (35%), commit iteration (25%), originality/non-fork status (25%), and documentation customization (15%).",
        }

    # Extract Practical Skill Verification Result
    if practical_result and practical_result.get("completed"):
        practical_score_val = practical_result.get("practical_score", 0)
        practical_status_val = practical_result.get("status_summary", "Completed Assessment")
        # Sub-scores for project understanding and practical coding
        proj_understanding_val = practical_result.get(
            "project_understanding_score",
            practical_result.get("question_avg_score", practical_score_val),
        )
        coding_perf_val = practical_result.get(
            "coding_performance_score",
            practical_result.get("coding_challenge_evaluation", {}).get("logic_score", practical_score_val),
        )
    else:
        practical_score_val = "Not tested"
        practical_status_val = "Candidate has not completed timed project verification or coding challenge."
        proj_understanding_val = "Not tested"
        coding_perf_val = "Not tested"

    resume_role_match_val = round(role_fit_score, 1)
    ownership_score_val = github_ownership.get("score", 50)

    # 5 Separate Categories Summary (Requirement 6)
    five_categories = {
        "career_readiness": {
            "score": overall,
            "label": "1. Career Readiness Score",
            "status": "Ready for Market" if overall >= 75 else "Developing" if overall >= 55 else "Needs Growth",
            "explanation": "Evaluates overall profile strength: verified skill claims (40%), target role fit (30%), project recency (15%), problem solving (10%), and profile completeness (5%).",
        },
        "role_skill_match": {
            "score": resume_role_match_val,
            "label": "2. Resume-to-Role Skill Match Score",
            "status": f"{len(matched_role_skills)} of {len(norm_role_skills)} skills matched",
            "explanation": f"Measures percentage of required technical competencies for '{target_role}' matched from resume and verified online evidence.",
        },
        "project_understanding": {
            "score": proj_understanding_val,
            "label": "3. GitHub Project Understanding Score",
            "status": "Evaluated" if proj_understanding_val != "Not tested" else "Not tested",
            "explanation": "Measures candidate's written explanations to code-grounded questions about architecture, algorithms, trade-offs, debugging, and commits.",
        },
        "practical_coding": {
            "score": coding_perf_val,
            "label": "4. Practical Coding / Debugging Performance",
            "status": "Evaluated" if coding_perf_val != "Not tested" else "Not tested",
            "explanation": "Evaluates live code challenge submission: static AST syntax safety, logic structure, defensive input validation, and edge case coverage without executing untrusted code.",
        },
        "project_ownership": {
            "score": ownership_score_val,
            "label": "5. Project Ownership Evidence & Confidence",
            "status": github_ownership.get("status_label", "Moderate Ownership Evidence"),
            "confidence": github_ownership.get("confidence_rating", "Moderate Confidence"),
            "explanation": "Analyzes commit authorship ratio, repository history iteration, non-fork originality, and documentation customization. Does not penalize forks or lack of commits as dishonest.",
        },
    }

    return {
        "overall": overall,
        "career_readiness_score": overall,
        "resume_to_role_skill_match_score": resume_role_match_val,
        "github_project_understanding_score": proj_understanding_val,
        "practical_coding_performance_score": coding_perf_val,
        "project_ownership_evidence_score": ownership_score_val,
        "ownership_evidence_score": ownership_score_val,
        "ownership_data": github_ownership,
        "practical_verification_score": practical_score_val,
        "practical_status": practical_status_val,
        "verified_evidence_score": round(verified_evidence_score, 1),
        "role_fit_score": resume_role_match_val,
        "project_score": round(project_score, 1),
        "coding_score": round(coding_score, 1),
        "profile_completeness_score": round(profile_completeness_score, 1),
        "supported_count": supported_count,
        "partial_count": partial_count,
        "not_verified_count": not_verified_count,
        "unable_count": unable_count,
        "total_claims": total_claims,
        "matched_role_skills": matched_role_skills,
        "missing_role_skills": missing_role_skills,
        "active_repos_count": len(repos),
        "recent_activity_count": recent_activity,
        "coding_problems_solved": solved,
        "five_categories_summary": five_categories,
        "three_scores_summary": {
            "career_readiness": five_categories["career_readiness"],
            "project_ownership": five_categories["project_ownership"],
            "practical_skill": {
                "score": practical_score_val,
                "label": "Practical Skill Verification Score",
                "status_label": practical_status_val,
                "explanation": "Evaluates project understanding Q&A and safe coding challenge submission. Displays 'Not tested' if not taken.",
            },
        },
        "scoring_weights": {
            "Verified Evidence Coverage": "40%",
            "Target Role Skill Fit": "30%",
            "Project Quality & Recency": "15%",
            "Coding & Problem Solving Practice": "10%",
            "Profile & Portfolio Completeness": "5%",
        },
    }


def check_assessment_eligibility(
    readiness_score: float | int,
    skill_match_score: float | int,
    readiness_threshold: float | int = 60.0,
    skill_threshold: float | int = 50.0,
    admin_override: bool = False,
) -> dict:
    """Evaluate whether candidate is eligible for the timed GitHub technical verification round.
    
    Eligibility criteria:
    - Candidate readiness score >= configurable readiness threshold (default 60%).
    - Candidate resume-to-role skill match >= configurable skill threshold (default 50%).
    - OR administrator override enabled manually.
    """
    is_readiness_met = readiness_score >= readiness_threshold
    is_skill_met = skill_match_score >= skill_threshold
    eligible = bool((is_readiness_met and is_skill_met) or admin_override)

    reasons = []
    if is_readiness_met:
        reasons.append(f"Career readiness score ({readiness_score}%) meets requirement (>= {readiness_threshold}%).")
    else:
        reasons.append(f"Career readiness score ({readiness_score}%) is below requirement (>= {readiness_threshold}%).")

    if is_skill_met:
        reasons.append(f"Role skill match ({skill_match_score}%) meets requirement (>= {skill_threshold}%).")
    else:
        reasons.append(f"Role skill match ({skill_match_score}%) is below requirement (>= {skill_threshold}%).")

    if admin_override:
        reasons.append("Administrator override enabled — verification round unlocked manually by reviewer.")

    return {
        "eligible": eligible,
        "is_readiness_met": is_readiness_met,
        "is_skill_met": is_skill_met,
        "admin_override": admin_override,
        "readiness_threshold": readiness_threshold,
        "skill_threshold": skill_threshold,
        "readiness_score": readiness_score,
        "skill_match_score": skill_match_score,
        "reasons": reasons,
        "status_label": "Unlocked / Eligible" if eligible else "Locked (Thresholds Not Met)",
    }


def calculate_combined_summary(
    scores: dict,
    weights: dict | None = None,
) -> dict:
    """Calculate transparent, configurable combined summary without modifying original readiness score."""
    default_weights = {
        "career_readiness": 0.25,
        "role_skill_match": 0.25,
        "project_understanding": 0.20,
        "practical_coding": 0.15,
        "project_ownership": 0.15,
    }
    w = weights or default_weights

    # Normalize weights so they sum to 1.0
    tot_w = sum(w.values()) or 1.0
    w_norm = {k: v / tot_w for k, v in w.items()}

    s_readiness = scores.get("career_readiness_score", scores.get("overall", 0))
    s_skill = scores.get("resume_to_role_skill_match_score", scores.get("role_fit_score", 0))
    s_own = scores.get("project_ownership_evidence_score", scores.get("ownership_evidence_score", 50))

    pu_val = scores.get("github_project_understanding_score")
    s_pu = float(pu_val) if isinstance(pu_val, (int, float)) else 50.0

    pc_val = scores.get("practical_coding_performance_score")
    s_pc = float(pc_val) if isinstance(pc_val, (int, float)) else 50.0

    combined = round(
        (w_norm.get("career_readiness", 0.25) * s_readiness)
        + (w_norm.get("role_skill_match", 0.25) * s_skill)
        + (w_norm.get("project_understanding", 0.20) * s_pu)
        + (w_norm.get("practical_coding", 0.15) * s_pc)
        + (w_norm.get("project_ownership", 0.15) * s_own)
    )

    return {
        "combined_score": combined,
        "weights_used": {k: f"{int(v * 100)}%" for k, v in w_norm.items()},
        "is_custom_weighted": bool(weights),
        "explanation": "Transparent weighted combination of all 5 distinct categories. Does not alter original readiness score.",
    }

