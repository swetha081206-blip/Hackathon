"""Repository Provenance and Code/Documentation Similarity Analysis.

Distinguishes repository ownership from source-code authorship:
- Inspects fork status, parent/source repositories, and creation/update timelines.
- Analyzes commit history, author distribution, and single-commit bulk imports.
- Evaluates code/documentation similarity to upstream repositories and common templates.
- Generates an explainable Project Ownership Evidence Score and findings report.
"""

import difflib
import os
import re
from datetime import datetime, timezone
import requests
from security_utils import SAFE_USER_AGENT

GITHUB_API = "https://api.github.com"

# Known common boilerplate/template signatures
COMMON_TEMPLATE_SIGNATURES = [
    {
        "name": "Create React App Starter",
        "keywords": ["getting started with create react app", "this project was bootstrapped with create react app", "npm start", "npm test", "npm run build"],
        "category": "Frontend Boilerplate",
    },
    {
        "name": "Vite + React / Vue Starter",
        "keywords": ["vite + react", "vite + vue", "currently, two official plugins are available", "npm run dev", "vitejs/vite"],
        "category": "Frontend Boilerplate",
    },
    {
        "name": "Next.js Starter Template",
        "keywords": ["create-next-app", "the easiest way to get started with next.js", "nextjs.org/docs", "deploy on vercel"],
        "category": "Fullstack Boilerplate",
    },
    {
        "name": "Django Default Scaffolding",
        "keywords": ["django project", "manage.py runserver", "django-admin startproject", "settings.py"],
        "category": "Backend Boilerplate",
    },
    {
        "name": "Flask Starter Template",
        "keywords": ["flask run", "export flask_app", "flask_sqlalchemy", "basic flask app"],
        "category": "Backend Boilerplate",
    },
    {
        "name": "FreeCodeCamp / 100DaysOfCode Exercise",
        "keywords": ["freecodecamp", "100-days-of-code", "100daysofcode", "fcc-", "curriculum exercise"],
        "category": "Course Exercise",
    },
]


def _get_github_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": SAFE_USER_AGENT,
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def normalize_text_for_comparison(text: str) -> str:
    """Normalize code or markdown text by stripping whitespace, comments, and punctuation for similarity comparison."""
    if not text:
        return ""
    # Remove single-line comments (# or //)
    text = re.sub(r"(?m)^\s*(?:#|//).*$", "", text)
    # Remove markdown link syntax [label](url) -> label
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Lowercase and collapse all whitespace
    text = re.sub(r"\s+", " ", text.lower()).strip()
    # Strip common punctuation
    text = re.sub(r"[^\w\s]", "", text)
    return text


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate normalized similarity ratio (0.0 to 1.0) between two text/code snippets, ignoring formatting and whitespace."""
    norm1 = normalize_text_for_comparison(text1)
    norm2 = normalize_text_for_comparison(text2)

    if not norm1 and not norm2:
        return 1.0
    if not norm1 or not norm2:
        return 0.0

    # Quick token overlap (Jaccard) first for efficiency
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0.0

    jaccard = len(words1.intersection(words2)) / len(words1.union(words2))

    # Difflib SequenceMatcher on sample for structural order
    sample1 = norm1[:2000]
    sample2 = norm2[:2000]
    seq_ratio = difflib.SequenceMatcher(None, sample1, sample2).ratio()

    # Blended score: 50% sequence order + 50% lexical overlap
    return round((0.5 * seq_ratio + 0.5 * jaccard), 3)


def detect_template_signatures(readme_text: str, file_names: list[str]) -> list[dict]:
    """Detect common boilerplate, starter templates, or tutorial scaffolding."""
    detected = []
    norm_readme = normalize_text_for_comparison(readme_text)

    for tmpl in COMMON_TEMPLATE_SIGNATURES:
        matches = 0
        for kw in tmpl["keywords"]:
            if normalize_text_for_comparison(kw) in norm_readme:
                matches += 1

        # Check if 2 or more template keywords match
        if matches >= 2:
            confidence = "High" if matches >= 3 else "Medium"
            detected.append({
                "template_name": tmpl["name"],
                "category": tmpl["category"],
                "confidence": confidence,
                "matches_count": matches,
            })

    return detected


def analyze_repository_provenance(
    owner: str,
    repo_name: str,
    candidate_username: str,
    candidate_name: str = "",
) -> dict:
    """Analyze complete provenance for a public GitHub repository.
    
    Examines:
    - Fork status, parent repository, and upstream details.
    - Commits authored by the candidate vs other contributors.
    - Single-commit bulk import detection.
    - Template similarity and README documentation originality.
    - Meaningful modification indicators.
    """
    headers = _get_github_headers()
    repo_full_name = f"{owner}/{repo_name}"
    repo_url = f"https://github.com/{repo_full_name}"

    provenance = {
        "repository_name": repo_name,
        "full_name": repo_full_name,
        "repo_url": repo_url,
        "owner": owner,
        "is_fork": False,
        "parent_repo": None,
        "source_repo": None,
        "created_at": None,
        "updated_at": None,
        "pushed_at": None,
        "stars": 0,
        "forks_count": 0,
        "total_commits_inspected": 0,
        "candidate_authored_commits": 0,
        "candidate_commit_ratio": 0.0,
        "commit_authors_breakdown": {},
        "is_single_commit_import": False,
        "template_matches": [],
        "upstream_similarity": None,
        "evidence_of_custom_work": True,
        "ownership_status": "Requires manual review",
        "potential_concerns": [],
        "supporting_evidence": [],
        "limitations": [
            "Evaluates public GitHub metadata and visible commit author logins.",
            "Git commits made with unlinked email addresses may not reflect candidate login.",
        ],
    }

    try:
        # 1. Fetch detailed repository metadata (includes fork parent/source if forked)
        repo_resp = requests.get(f"{GITHUB_API}/repos/{repo_full_name}", headers=headers, timeout=8)
        if repo_resp.status_code == 404:
            provenance["ownership_status"] = "Insufficient evidence"
            provenance["potential_concerns"].append("Repository not found or is private.")
            return provenance
        elif repo_resp.status_code in (403, 429):
            provenance["ownership_status"] = "Requires manual review"
            provenance["potential_concerns"].append("GitHub API rate limit reached during provenance check.")
            return provenance

        repo_data = repo_resp.json()
        provenance["is_fork"] = bool(repo_data.get("fork"))
        provenance["created_at"] = repo_data.get("created_at")
        provenance["updated_at"] = repo_data.get("updated_at")
        provenance["pushed_at"] = repo_data.get("pushed_at")
        provenance["stars"] = repo_data.get("stargazers_count", 0)
        provenance["forks_count"] = repo_data.get("forks_count", 0)

        # 2. If it is a fork, extract parent and source
        parent_readme_text = ""
        if provenance["is_fork"]:
            parent = repo_data.get("parent")
            source = repo_data.get("source")
            if parent:
                provenance["parent_repo"] = {
                    "full_name": parent.get("full_name"),
                    "owner": parent.get("owner", {}).get("login"),
                    "html_url": parent.get("html_url"),
                    "stars": parent.get("stargazers_count", 0),
                }
            if source:
                provenance["source_repo"] = {
                    "full_name": source.get("full_name"),
                    "owner": source.get("owner", {}).get("login"),
                    "html_url": source.get("html_url"),
                }
            provenance["potential_concerns"].append(
                f"Repository is a GitHub fork of '{provenance['parent_repo']['full_name'] if provenance.get('parent_repo') else 'an upstream project'}'."
            )

        # 3. Fetch candidate's README
        candidate_readme = ""
        try:
            r_resp = requests.get(
                f"{GITHUB_API}/repos/{repo_full_name}/readme",
                headers={**headers, "Accept": "application/vnd.github.raw+json"},
                timeout=6,
            )
            if r_resp.status_code == 200:
                candidate_readme = r_resp.text
        except Exception:
            pass

        # 4. Check for template signatures in candidate's README
        templates = detect_template_signatures(candidate_readme, [])
        provenance["template_matches"] = templates
        if templates:
            for t in templates:
                provenance["potential_concerns"].append(
                    f"Detected boilerplate/template pattern: {t['template_name']} ({t['confidence']} confidence)."
                )

        # 5. If fork and parent is accessible, compare README with upstream
        if provenance["is_fork"] and provenance.get("parent_repo"):
            parent_full = provenance["parent_repo"]["full_name"]
            try:
                p_resp = requests.get(
                    f"{GITHUB_API}/repos/{parent_full}/readme",
                    headers={**headers, "Accept": "application/vnd.github.raw+json"},
                    timeout=6,
                )
                if p_resp.status_code == 200:
                    parent_readme_text = p_resp.text
                    sim = calculate_text_similarity(candidate_readme, parent_readme_text)
                    provenance["upstream_similarity"] = sim
                    if sim > 0.85:
                        provenance["potential_concerns"].append(
                            f"README is {int(sim * 100)}% identical to upstream parent repository."
                        )
                    elif sim < 0.50 and len(candidate_readme) > 200:
                        provenance["supporting_evidence"].append(
                            f"Candidate significantly modified documentation compared to upstream parent ({int((1 - sim) * 100)}% custom content)."
                        )
            except Exception:
                pass

        # 6. Fetch recent commits to analyze author breakdown
        commits_resp = requests.get(
            f"{GITHUB_API}/repos/{repo_full_name}/commits",
            headers=headers,
            params={"per_page": 30},
            timeout=8,
        )

        authors_count = {}
        candidate_lower = candidate_username.lower()
        cand_name_lower = candidate_name.lower().strip() if candidate_name else ""

        if commits_resp.status_code == 200:
            commits_list = commits_resp.json()
            provenance["total_commits_inspected"] = len(commits_list)

            # Check if this repository has only 1 commit total ("Initial commit" bulk import)
            if len(commits_list) == 1:
                commit_msg = commits_list[0].get("commit", {}).get("message", "").lower()
                provenance["is_single_commit_import"] = True
                provenance["potential_concerns"].append(
                    f"Repository history contains only 1 commit ('{commit_msg[:40]}'), typical of code imported or copied in a single upload."
                )

            cand_commits = 0
            for c in commits_list:
                author_login = (c.get("author") or {}).get("login") or ""
                committer_login = (c.get("committer") or {}).get("login") or ""
                git_author_name = (c.get("commit", {}).get("author") or {}).get("name") or ""

                author_key = author_login or git_author_name or "Unknown Author"
                authors_count[author_key] = authors_count.get(author_key, 0) + 1

                # Check if matches candidate username or name
                is_candidate = False
                if author_login and author_login.lower() == candidate_lower:
                    is_candidate = True
                elif committer_login and committer_login.lower() == candidate_lower:
                    is_candidate = True
                elif cand_name_lower and git_author_name and cand_name_lower in git_author_name.lower():
                    is_candidate = True

                if is_candidate:
                    cand_commits += 1

            provenance["candidate_authored_commits"] = cand_commits
            provenance["commit_authors_breakdown"] = authors_count

            if provenance["total_commits_inspected"] > 0:
                provenance["candidate_commit_ratio"] = round(
                    cand_commits / provenance["total_commits_inspected"], 2
                )

            if cand_commits > 0:
                provenance["supporting_evidence"].append(
                    f"{cand_commits} of {provenance['total_commits_inspected']} inspected commits were directly authored by candidate '{candidate_username}'."
                )
            else:
                provenance["potential_concerns"].append(
                    f"None of the inspected {provenance['total_commits_inspected']} commits matched candidate '{candidate_username}' (authors found: {', '.join(list(authors_count.keys())[:3])})."
                )

        # 7. Synthesize Ownership Status (4 transparent categories)
        ratio = provenance["candidate_commit_ratio"]
        is_fork = provenance["is_fork"]
        is_single = provenance["is_single_commit_import"]

        if not is_fork and ratio >= 0.70 and not is_single:
            provenance["ownership_status"] = "Strong supporting evidence"
            provenance["supporting_evidence"].append(
                "Original repository with continuous, iterative commit history authored by candidate."
            )
        elif is_fork and ratio >= 0.40:
            provenance["ownership_status"] = "Some supporting evidence"
            provenance["supporting_evidence"].append(
                "Fork repository with verified active contributions and customizations by candidate."
            )
        elif not is_fork and (ratio >= 0.40 or (ratio == 0 and len(authors_count) == 1 and owner.lower() == candidate_lower)):
            provenance["ownership_status"] = "Some supporting evidence"
        elif is_fork and ratio == 0.0:
            provenance["ownership_status"] = "Insufficient evidence"
            provenance["potential_concerns"].append(
                "Fork repository with zero commits authored by candidate in available history."
            )
        elif is_single:
            provenance["ownership_status"] = "Requires manual review"
        else:
            provenance["ownership_status"] = "Requires manual review"

    except Exception as exc:
        provenance["ownership_status"] = "Requires manual review"
        provenance["potential_concerns"].append(f"Provenance inspection encountered an error: {type(exc).__name__}")

    return provenance


def calculate_project_ownership_score(provenance_list: list[dict]) -> dict:
    """Calculate overall Project Ownership Evidence Score (0-100) across all inspected repositories.
    
    Transparent Formula:
    - Authorship Ratio (35%): Proportion of commits authored by candidate across repositories.
    - Iterative History (25%): Multi-commit iterative evolution vs single bulk import.
    - Originality / Non-Clone (25%): Non-fork original repositories, or forks with substantial customizations.
    - Custom Documentation (15%): Meaningful custom README vs default starter boilerplate.
    """
    if not provenance_list:
        return {
            "score": 0,
            "status_label": "No Repositories Inspected",
            "authorship_score": 0.0,
            "iteration_score": 0.0,
            "originality_score": 0.0,
            "documentation_score": 0.0,
            "total_repositories": 0,
            "strong_count": 0,
            "some_count": 0,
            "insufficient_count": 0,
            "manual_review_count": 0,
            "summary_findings": "No GitHub repositories were provided or accessible for provenance analysis.",
            "formula_explanation": "Evaluates commit authorship ratio (35%), commit iteration (25%), originality/non-fork status (25%), and documentation customization (15%).",
        }

    total_repos = len(provenance_list)
    total_commits = sum(p.get("total_commits_inspected", 0) for p in provenance_list)
    total_cand_commits = sum(p.get("candidate_authored_commits", 0) for p in provenance_list)

    # 1. Authorship Score (35%)
    if total_commits > 0:
        authorship_ratio = total_cand_commits / total_commits
        authorship_pts = round(authorship_ratio * 100, 1)
    else:
        authorship_pts = 50.0  # neutral if commit list restricted

    # 2. Iteration Score (25%)
    single_commit_repos = sum(1 for p in provenance_list if p.get("is_single_commit_import"))
    multi_commit_repos = total_repos - single_commit_repos
    iteration_pts = round((multi_commit_repos / total_repos) * 100, 1)

    # 3. Originality / Upstream Differentiation (25%)
    fork_count = sum(1 for p in provenance_list if p.get("is_fork"))
    active_fork_count = sum(1 for p in provenance_list if p.get("is_fork") and p.get("candidate_authored_commits", 0) > 0)
    original_count = total_repos - fork_count

    # Full points for originals; partial points for forks with contributions; 0 for untouched forks
    originality_pts = round(((original_count * 1.0 + active_fork_count * 0.6) / total_repos) * 100, 1)

    # 4. Custom Documentation Score (15%)
    template_flagged = sum(1 for p in provenance_list if p.get("template_matches"))
    custom_doc_count = max(0, total_repos - template_flagged)
    documentation_pts = round((custom_doc_count / total_repos) * 100, 1)

    # Weighted Overall Ownership Score
    ownership_score = round(
        (0.35 * authorship_pts)
        + (0.25 * iteration_pts)
        + (0.25 * originality_pts)
        + (0.15 * documentation_pts)
    )
    ownership_score = max(0, min(100, ownership_score))

    # Categorize counts
    strong_count = sum(1 for p in provenance_list if p.get("ownership_status") == "Strong supporting evidence")
    some_count = sum(1 for p in provenance_list if p.get("ownership_status") == "Some supporting evidence")
    insufficient_count = sum(1 for p in provenance_list if p.get("ownership_status") == "Insufficient evidence")
    manual_review_count = sum(1 for p in provenance_list if p.get("ownership_status") == "Requires manual review")

    if ownership_score >= 75:
        status_label = "Strong Ownership Evidence"
    elif ownership_score >= 50:
        status_label = "Moderate Ownership Evidence"
    elif ownership_score >= 30:
        status_label = "Partial Ownership Evidence"
    else:
        status_label = "Limited Ownership Evidence"

    summary_findings = (
        f"Inspected {total_repos} repositories ({original_count} original, {fork_count} forks). "
        f"{strong_count} repositories exhibit strong ownership signals, {some_count} have partial evidence, "
        f"and {manual_review_count + insufficient_count} require manual review or show limited commit history."
    )

    return {
        "score": ownership_score,
        "status_label": status_label,
        "authorship_score": authorship_pts,
        "iteration_score": iteration_pts,
        "originality_score": originality_pts,
        "documentation_score": documentation_pts,
        "total_repositories": total_repos,
        "strong_count": strong_count,
        "some_count": some_count,
        "insufficient_count": insufficient_count,
        "manual_review_count": manual_review_count,
        "summary_findings": summary_findings,
        "formula_explanation": "Weighted composite: 35% commit authorship ratio + 25% iterative commit history + 25% non-fork/modified originality + 15% custom documentation.",
    }
