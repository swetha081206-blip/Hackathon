"""Platform-specific evidence retrieval and analysis.

Supports GitHub, LeetCode, Codeforces, HackerRank, CodeChef, GeeksforGeeks,
Kaggle, live project demonstrations, portfolios, and certification URLs.
"""

import os
import re
import json
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from security_utils import safe_fetch, is_safe_url, SAFE_USER_AGENT

GITHUB_API = "https://api.github.com"
CODEFORCES_API = "https://codeforces.com/api"


def _get_github_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "CareerReadinessAnalyzer/2.0",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def analyze_github(profile_or_repo_url: str, max_repos: int = 20) -> dict:
    """Analyze a public GitHub profile or repository."""
    result = {
        "platform": "GitHub",
        "url": profile_or_repo_url,
        "status": "Pending",
        "profile": {},
        "repositories": [],
        "languages": [],
        "recent_activity_count": 0,
        "latest_commit_dates": [],
        "notes": "",
    }

    # Extract username or repo from URL
    match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)(?:/([a-zA-Z0-9_.-]+))?", profile_or_repo_url)
    if not match:
        result["status"] = "Invalid URL"
        result["notes"] = "Could not parse GitHub username from URL."
        return result

    username = match.group(1)
    specific_repo = match.group(2)

    headers = _get_github_headers()

    try:
        # Check user profile
        user_resp = requests.get(f"{GITHUB_API}/users/{username}", headers=headers, timeout=8)
        if user_resp.status_code == 404:
            result["status"] = "Not Found"
            result["notes"] = f"GitHub user '{username}' was not found."
            return result
        elif user_resp.status_code == 403:
            result["status"] = "Rate Limited"
            result["notes"] = "GitHub API rate limit exceeded. Add GITHUB_TOKEN to .env for higher limits."
            return result
        user_resp.raise_for_status()
        profile_data = user_resp.json()

        result["profile"] = {
            "login": profile_data.get("login"),
            "name": profile_data.get("name") or profile_data.get("login"),
            "bio": profile_data.get("bio") or "",
            "public_repos": profile_data.get("public_repos", 0),
            "followers": profile_data.get("followers", 0),
            "html_url": profile_data.get("html_url"),
            "created_at": profile_data.get("created_at"),
        }

        # Fetch repositories
        repos_url = f"{GITHUB_API}/users/{username}/repos"
        repos_resp = requests.get(
            repos_url,
            headers=headers,
            params={"sort": "updated", "direction": "desc", "per_page": min(max_repos, 30), "type": "owner"},
            timeout=8,
        )

        all_languages = set()
        recent_commit_dates = []
        now = datetime.now(timezone.utc)
        recent_activity_count = 0

        provenance_list = []
        if repos_resp.status_code == 200:
            repos_list = repos_resp.json()
            for r in repos_list:
                full_name = r.get("full_name")
                repo_name = r.get("name")
                is_fork = bool(r.get("fork"))

                # Get languages for repo
                repo_languages = []
                try:
                    lang_resp = requests.get(f"{GITHUB_API}/repos/{full_name}/languages", headers=headers, timeout=5)
                    if lang_resp.status_code == 200:
                        repo_languages = list(lang_resp.json().keys())
                        for l in repo_languages:
                            all_languages.add(l)
                except Exception:
                    pass

                # Get README snippet
                readme_text = ""
                try:
                    readme_resp = requests.get(
                        f"{GITHUB_API}/repos/{full_name}/readme",
                        headers={**headers, "Accept": "application/vnd.github.raw+json"},
                        timeout=5,
                    )
                    if readme_resp.status_code == 200:
                        readme_text = readme_resp.text[:3000]
                except Exception:
                    pass

                # Latest commit
                latest_commit = None
                try:
                    commits_resp = requests.get(
                        f"{GITHUB_API}/repos/{full_name}/commits",
                        headers=headers,
                        params={"per_page": 1},
                        timeout=5,
                    )
                    if commits_resp.status_code == 200 and commits_resp.json():
                        first_commit = commits_resp.json()[0]
                        latest_commit = (
                            first_commit.get("commit", {}).get("committer", {}).get("date")
                            or first_commit.get("commit", {}).get("author", {}).get("date")
                        )
                        if latest_commit:
                            dt = datetime.fromisoformat(latest_commit.replace("Z", "+00:00"))
                            recent_commit_dates.append(dt.isoformat())
                            if (now - dt).days <= 180:
                                recent_activity_count += 1
                except Exception:
                    pass

                result["repositories"].append({
                    "name": repo_name,
                    "full_name": full_name,
                    "url": r.get("html_url"),
                    "description": r.get("description") or "",
                    "stars": r.get("stargazers_count", 0),
                    "forks": r.get("forks_count", 0),
                    "is_fork": is_fork,
                    "topics": r.get("topics", []),
                    "languages": repo_languages,
                    "readme": readme_text,
                    "latest_commit": latest_commit,
                    "updated_at": r.get("updated_at"),
                    "size_kb": r.get("size", 0),
                })

            # Perform repository provenance and ownership analysis
            try:
                from project_provenance import analyze_repository_provenance, calculate_project_ownership_score
                for repo_item in result["repositories"][:6]:
                    owner_part = repo_item["full_name"].split("/")[0] if "/" in repo_item["full_name"] else username
                    prov = analyze_repository_provenance(owner_part, repo_item["name"], username, profile_data.get("name") or "")
                    repo_item["provenance"] = prov
                    provenance_list.append(prov)

                result["provenance_list"] = provenance_list
                result["project_ownership"] = calculate_project_ownership_score(provenance_list)
            except Exception:
                result["provenance_list"] = []
                result["project_ownership"] = {"score": 50, "status_label": "Not Evaluated", "summary_findings": "Provenance check bypassed."}

        result["languages"] = sorted(list(all_languages))
        result["recent_activity_count"] = recent_activity_count
        result["latest_commit_dates"] = recent_commit_dates
        result["status"] = "Verified"
        result["notes"] = f"Successfully analyzed {len(result['repositories'])} public repositories ({len([r for r in result['repositories'] if r.get('is_fork')])} forks) and {len(result['languages'])} languages."


    except requests.exceptions.Timeout:
        result["status"] = "Timeout"
        result["notes"] = "GitHub API request timed out."
    except Exception as exc:
        result["status"] = "Error"
        result["notes"] = f"Error inspecting GitHub profile: {type(exc).__name__}"

    return result


def analyze_leetcode(profile_url: str) -> dict:
    """Analyze a public LeetCode profile using LeetCode's public GraphQL endpoint."""
    result = {
        "platform": "LeetCode",
        "url": profile_url,
        "status": "Pending",
        "username": "",
        "total_solved": 0,
        "easy_solved": 0,
        "medium_solved": 0,
        "hard_solved": 0,
        "ranking": None,
        "contest_rating": None,
        "contests_attended": 0,
        "notes": "",
    }

    match = re.search(r"(?:https?://)?(?:www\.)?leetcode\.com/(?:u/)?([a-zA-Z0-9_-]+)", profile_url)
    if not match:
        result["status"] = "Invalid URL"
        result["notes"] = "Could not parse LeetCode username."
        return result

    username = match.group(1)
    result["username"] = username

    graphql_query = {
        "query": """
        query getUserProfile($username: String!) {
            matchedUser(username: $username) {
                username
                profile {
                    ranking
                    reputation
                }
                submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
            }
            userContestRanking(username: $username) {
                attendedContestsCount
                rating
                globalRanking
                topPercentage
            }
        }
        """,
        "variables": {"username": username},
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": SAFE_USER_AGENT,
        "Referer": f"https://leetcode.com/{username}/",
    }

    try:
        resp = requests.post("https://leetcode.com/graphql", json=graphql_query, headers=headers, timeout=7)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            user_data = data.get("matchedUser")
            if not user_data:
                result["status"] = "Not Found"
                result["notes"] = f"LeetCode user '{username}' was not found or has a private profile."
                return result

            # Parse submission stats
            submit_stats = user_data.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
            for item in submit_stats:
                diff = item.get("difficulty")
                count = item.get("count", 0)
                if diff == "All":
                    result["total_solved"] = count
                elif diff == "Easy":
                    result["easy_solved"] = count
                elif diff == "Medium":
                    result["medium_solved"] = count
                elif diff == "Hard":
                    result["hard_solved"] = count

            profile_obj = user_data.get("profile", {})
            result["ranking"] = profile_obj.get("ranking")

            contest_data = data.get("userContestRanking")
            if contest_data:
                result["contest_rating"] = round(contest_data.get("rating", 0))
                result["contests_attended"] = contest_data.get("attendedContestsCount", 0)

            result["status"] = "Verified"
            result["notes"] = f"Solved: {result['total_solved']} (Easy: {result['easy_solved']}, Med: {result['medium_solved']}, Hard: {result['hard_solved']})"
        elif resp.status_code in (403, 429):
            result["status"] = "Restricted"
            result["notes"] = "LeetCode anti-bot protection active. You can enter your LeetCode statistics manually in the review panel."
        else:
            result["status"] = "Unavailable"
            result["notes"] = f"LeetCode service returned HTTP status {resp.status_code}."
    except Exception as exc:
        result["status"] = "Unavailable"
        result["notes"] = f"Could not connect to LeetCode API ({type(exc).__name__}). Manual input supported."

    return result


def analyze_codeforces(profile_url: str) -> dict:
    """Analyze a public Codeforces profile using official Codeforces API."""
    result = {
        "platform": "Codeforces",
        "url": profile_url,
        "status": "Pending",
        "handle": "",
        "rating": None,
        "max_rating": None,
        "rank": "",
        "max_rank": "",
        "problems_solved": 0,
        "top_tags": [],
        "notes": "",
    }

    match = re.search(r"(?:https?://)?(?:www\.)?codeforces\.com/profile/([a-zA-Z0-9_.-]+)", profile_url)
    if not match:
        result["status"] = "Invalid URL"
        result["notes"] = "Could not parse Codeforces handle."
        return result

    handle = match.group(1)
    result["handle"] = handle

    headers = {"User-Agent": SAFE_USER_AGENT}

    try:
        # Fetch user info
        info_resp = requests.get(f"{CODEFORCES_API}/user.info", params={"handles": handle}, headers=headers, timeout=7)
        if info_resp.status_code == 200 and info_resp.json().get("status") == "OK":
            user_info = info_resp.json()["result"][0]
            result["rating"] = user_info.get("rating")
            result["max_rating"] = user_info.get("maxRating")
            result["rank"] = user_info.get("rank", "unrated")
            result["max_rank"] = user_info.get("maxRank", "unrated")
        else:
            result["status"] = "Not Found"
            result["notes"] = f"Codeforces handle '{handle}' not found."
            return result

        # Fetch recent submissions to count solved problems
        status_resp = requests.get(
            f"{CODEFORCES_API}/user.status",
            params={"handle": handle, "from": 1, "count": 100},
            headers=headers,
            timeout=7,
        )
        if status_resp.status_code == 200 and status_resp.json().get("status") == "OK":
            submissions = status_resp.json()["result"]
            solved_problem_ids = set()
            tags_count = {}
            for sub in submissions:
                if sub.get("verdict") == "OK":
                    prob = sub.get("problem", {})
                    prob_id = f"{prob.get('contestId')}_{prob.get('index')}"
                    solved_problem_ids.add(prob_id)
                    for t in prob.get("tags", []):
                        tags_count[t] = tags_count.get(t, 0) + 1

            result["problems_solved"] = len(solved_problem_ids)
            result["top_tags"] = sorted(tags_count.keys(), key=lambda k: tags_count[k], reverse=True)[:5]

        result["status"] = "Verified"
        result["notes"] = f"Rank: {result['rank']}, Rating: {result['rating'] or 'Unrated'}, Recent solved: {result['problems_solved']}"
    except Exception as exc:
        result["status"] = "Unavailable"
        result["notes"] = f"Codeforces API error: {type(exc).__name__}"

    return result


def analyze_hackerrank(profile_url: str) -> dict:
    """Analyze a public HackerRank profile."""
    result = {
        "platform": "HackerRank",
        "url": profile_url,
        "status": "Pending",
        "username": "",
        "badges": [],
        "certificates": [],
        "notes": "",
    }

    match = re.search(r"(?:https?://)?(?:www\.)?hackerrank\.com/(?:profile/)?([a-zA-Z0-9_.-]+)", profile_url)
    if not match:
        result["status"] = "Invalid URL"
        result["notes"] = "Could not parse HackerRank username."
        return result

    username = match.group(1)
    result["username"] = username

    headers = {"User-Agent": SAFE_USER_AGENT, "Accept": "application/json"}
    try:
        resp = requests.get(f"https://www.hackerrank.com/rest/hackers/{username}/badges", headers=headers, timeout=6)
        if resp.status_code == 200:
            badges_data = resp.json().get("models", [])
            badges = []
            for b in badges_data:
                name = b.get("badge_name")
                stars = b.get("stars", 0)
                if name:
                    badges.append(f"{name} ({stars}★)")
            result["badges"] = badges
            result["status"] = "Verified" if badges else "Accessible"
            result["notes"] = f"Badges found: {', '.join(badges) if badges else 'No public badges displayed'}"
        elif resp.status_code == 404:
            result["status"] = "Not Found"
            result["notes"] = f"HackerRank profile '{username}' not found."
        else:
            result["status"] = "Accessible"
            result["notes"] = f"HackerRank profile exists (HTTP {resp.status_code}), automated badge inspection restricted."
    except Exception as exc:
        result["status"] = "Unavailable"
        result["notes"] = f"HackerRank check unavailable: {type(exc).__name__}"

    return result


def analyze_codechef(profile_url: str) -> dict:
    """Analyze a public CodeChef profile."""
    result = {
        "platform": "CodeChef",
        "url": profile_url,
        "status": "Pending",
        "username": "",
        "rating": None,
        "stars": None,
        "notes": "",
    }

    match = re.search(r"(?:https?://)?(?:www\.)?codechef\.com/users/([a-zA-Z0-9_.-]+)", profile_url)
    if not match:
        result["status"] = "Invalid URL"
        result["notes"] = "Could not parse CodeChef username."
        return result

    username = match.group(1)
    result["username"] = username

    # Use safe_fetch to inspect HTML
    success, status_code, content, msg = safe_fetch(profile_url, max_bytes=128 * 1024, timeout=6)
    if success and status_code == 200:
        # Regex to find rating in page HTML
        rating_match = re.search(r'class="rating-number">(\d+)<', content)
        stars_match = re.search(r'class="rating-star">\s*<span>([^<]+)</span>', content)
        if rating_match:
            result["rating"] = int(rating_match.group(1))
        if stars_match:
            result["stars"] = stars_match.group(1).strip()

        result["status"] = "Verified" if result["rating"] else "Accessible"
        result["notes"] = f"CodeChef Rating: {result['rating'] or 'Public profile verified'}, Stars: {result['stars'] or 'Unrated'}"
    else:
        result["status"] = "Accessible" if status_code == 200 else "Unavailable"
        result["notes"] = msg

    return result


def analyze_geeksforgeeks(profile_url: str) -> dict:
    """Analyze a public GeeksforGeeks profile."""
    result = {
        "platform": "GeeksforGeeks",
        "url": profile_url,
        "status": "Pending",
        "username": "",
        "coding_score": None,
        "problems_solved": None,
        "notes": "",
    }

    match = re.search(r"(?:https?://)?(?:www\.)?geeksforgeeks\.org/user/([a-zA-Z0-9_.-]+)", profile_url)
    if not match:
        result["status"] = "Invalid URL"
        result["notes"] = "Could not parse GeeksforGeeks username."
        return result

    username = match.group(1)
    result["username"] = username

    success, status_code, content, msg = safe_fetch(profile_url, max_bytes=128 * 1024, timeout=6)
    if success and status_code == 200:
        # Extract problem count or score
        score_match = re.search(r'Overall Coding Score.*?(\d+)', content, re.DOTALL)
        prob_match = re.search(r'Total Problems Solved.*?(\d+)', content, re.DOTALL)

        if score_match:
            result["coding_score"] = int(score_match.group(1))
        if prob_match:
            result["problems_solved"] = int(prob_match.group(1))

        result["status"] = "Verified" if (result["coding_score"] or result["problems_solved"]) else "Accessible"
        result["notes"] = f"GfG Score: {result['coding_score'] or 'N/A'}, Problems Solved: {result['problems_solved'] or 'N/A'}"
    else:
        result["status"] = "Unavailable"
        result["notes"] = msg

    return result


def analyze_kaggle(profile_url: str) -> dict:
    """Analyze a public Kaggle profile."""
    result = {
        "platform": "Kaggle",
        "url": profile_url,
        "status": "Pending",
        "username": "",
        "notes": "",
    }

    match = re.search(r"(?:https?://)?(?:www\.)?kaggle\.com/([a-zA-Z0-9_.-]+)", profile_url)
    if not match:
        result["status"] = "Invalid URL"
        result["notes"] = "Could not parse Kaggle username."
        return result

    username = match.group(1)
    result["username"] = username

    success, status_code, content, msg = safe_fetch(profile_url, max_bytes=64 * 1024, timeout=6)
    if success and status_code == 200:
        result["status"] = "Accessible"
        result["notes"] = f"Public Kaggle profile verified: https://kaggle.com/{username}"
    else:
        result["status"] = "Unavailable"
        result["notes"] = msg

    return result


def analyze_web_or_project(url: str, detected_type: str = "Web Link") -> dict:
    """Safely analyze a generic website, project demonstration, portfolio, or certificate verification page."""
    result = {
        "platform": "Web Project / Verification",
        "url": url,
        "type": detected_type,
        "status": "Pending",
        "title": "",
        "description": "",
        "technologies_detected": [],
        "http_status": None,
        "notes": "",
    }

    safe, reason = is_safe_url(url)
    if not safe:
        result["status"] = "Blocked Unsafe"
        result["notes"] = reason
        return result

    success, status_code, content, msg = safe_fetch(url, max_bytes=256 * 1024, timeout=6)
    result["http_status"] = status_code

    if not success:
        result["status"] = "Inaccessible"
        result["notes"] = f"Could not access site: {msg}"
        return result

    if status_code != 200:
        result["status"] = f"HTTP {status_code}"
        result["notes"] = f"Server returned status {status_code}"
        return result

    # Extract HTML title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    if title_match:
        result["title"] = re.sub(r"\s+", " ", title_match.group(1)).strip()[:100]

    # Extract meta description
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', content, re.IGNORECASE | re.DOTALL)
    if desc_match:
        result["description"] = re.sub(r"\s+", " ", desc_match.group(1)).strip()[:200]

    # Detect common web technologies mentioned in content
    tech_keywords = [
        "React", "Vue", "Angular", "Next.js", "Django", "Flask", "FastAPI",
        "Node.js", "Express", "Tailwind", "Bootstrap", "TypeScript", "Python",
        "Streamlit", "PostgreSQL", "MongoDB", "TensorFlow", "PyTorch", "AWS"
    ]
    detected_tech = []
    content_lower = content.lower()
    for tech in tech_keywords:
        if re.search(r"\b" + re.escape(tech.lower()) + r"\b", content_lower):
            detected_tech.append(tech)

    result["technologies_detected"] = detected_tech
    result["status"] = "Verified Accessible"
    result["notes"] = f"Live site accessible. Title: '{result['title'] or 'No title'}'. Tech detected: {', '.join(detected_tech) if detected_tech else 'None'}"

    return result


def dispatch_analyzer(url_item: dict) -> dict:
    """Route a detected URL dictionary to its appropriate platform analyzer."""
    platform = url_item.get("platform")
    url = url_item.get("url")

    if platform == "GitHub":
        return analyze_github(url)
    elif platform == "LeetCode":
        return analyze_leetcode(url)
    elif platform == "Codeforces":
        return analyze_codeforces(url)
    elif platform == "HackerRank":
        return analyze_hackerrank(url)
    elif platform == "CodeChef":
        return analyze_codechef(url)
    elif platform == "GeeksforGeeks":
        return analyze_geeksforgeeks(url)
    elif platform == "Kaggle":
        return analyze_kaggle(url)
    elif platform == "LinkedIn":
        # Public LinkedIn scraping is restricted; explain limitation and verify URL syntax
        return {
            "platform": "LinkedIn",
            "url": url,
            "status": "Restricted Access",
            "notes": "LinkedIn profiles require direct user authentication. Profile URL syntax is valid; manual profile data can be reviewed in the editor.",
        }
    else:
        return analyze_web_or_project(url, detected_type=url_item.get("type", "Web Link"))
