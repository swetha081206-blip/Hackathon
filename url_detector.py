"""URL detection, cross-line reconstruction, normalization, classification, and safe accessibility probing.
"""

import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from security_utils import safe_fetch, is_safe_url

# Regex to match URLs in free text (including schemes or common domain beginnings)
URL_PATTERN = re.compile(
    r"""(?xi)
    \b
    (?:
        # Explicit scheme
        (?:https?://)
        # Optional credentials
        (?:[^\s:@]+(?::[^\s:@]*)?@)?
        # Domain name / IP
        (?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}
        |
        # Domain starting with common platform prefixes or www
        (?:www\.|github\.com/|linkedin\.com/|leetcode\.com/|codeforces\.com/|hackerrank\.com/|codechef\.com/|geeksforgeeks\.org/|kaggle\.com/|gitlab\.com/|bitbucket\.org/)
        [a-z0-9\./~_%+-]+
    )
    # Optional port
    (?::\d{1,5})?
    # Path, query, fragment
    (?:/[a-z0-9\./~_%+\-?#=&;:,!*'$()]*)*
    """
)


PLATFORM_RULES = [
    # (Platform Name, Category, Regex Pattern)
    ("GitHub", "Profile", re.compile(r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/?$")),
    ("GitHub", "Repository", re.compile(r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)")),
    ("LeetCode", "Profile", re.compile(r"^https?://(?:www\.)?leetcode\.com/(?:u/)?([a-zA-Z0-9_-]+)/?$")),
    ("LinkedIn", "Profile", re.compile(r"^https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/([a-zA-Z0-9_.-]+)/?$")),
    ("Codeforces", "Profile", re.compile(r"^https?://(?:www\.)?codeforces\.com/profile/([a-zA-Z0-9_.-]+)/?$")),
    ("HackerRank", "Profile", re.compile(r"^https?://(?:www\.)?hackerrank\.com/profile/([a-zA-Z0-9_.-]+)/?$")),
    ("HackerRank", "Profile", re.compile(r"^https?://(?:www\.)?hackerrank\.com/([a-zA-Z0-9_.-]+)/?$")),
    ("CodeChef", "Profile", re.compile(r"^https?://(?:www\.)?codechef\.com/users/([a-zA-Z0-9_.-]+)/?$")),
    ("GeeksforGeeks", "Profile", re.compile(r"^https?://(?:www\.)?geeksforgeeks\.org/user/([a-zA-Z0-9_.-]+)/?$")),
    ("Kaggle", "Profile", re.compile(r"^https?://(?:www\.)?kaggle\.com/([a-zA-Z0-9_.-]+)/?$")),
    ("Kaggle", "Notebook / Dataset", re.compile(r"^https?://(?:www\.)?kaggle\.com/code/|kaggle\.com/datasets/")),
    ("GitLab", "Repository / Profile", re.compile(r"^https?://(?:www\.)?gitlab\.com/([a-zA-Z0-9_.-]+)")),
    ("Bitbucket", "Repository / Profile", re.compile(r"^https?://(?:www\.)?bitbucket\.org/([a-zA-Z0-9_.-]+)")),
    ("Credly", "Certification", re.compile(r"^https?://(?:www\.)?credly\.com/badges/([a-zA-Z0-9_.-]+)")),
    ("Coursera", "Certification / Course", re.compile(r"^https?://(?:www\.)?coursera\.org/account/accomplishments/|coursera\.org/verify/")),
    ("Udemy", "Certification / Course", re.compile(r"^https?://(?:www\.)?udemy\.com/certificate/")),
    ("Research / Publication", "Publication", re.compile(r"arxiv\.org/|doi\.org/|scholar\.google\.|researchgate\.net|ieeexplore\.ieee\.org")),
    ("Project Demo", "Live Demonstration", re.compile(r"\.(?:vercel\.app|netlify\.app|render\.com|streamlit\.app|hf\.space|onrender\.com|herokuapp\.com|railway\.app)")),
]


def reconstruct_cross_line_urls(text: str) -> str:
    """Safely rejoin URLs that have been broken across newlines in PDF extraction."""
    # Pattern: text ending with slash or hyphen or url characters followed by newline and path continuation
    # e.g., "https://github.com/\nusername" or "linkedin.com/in/\nusername"
    text = re.sub(
        r"(https?://[^\s]+|www\.[^\s]+|[a-z0-9.-]+\.(?:com|org|io|dev|in|ai|app)/[^\s]*)[ \t]*\n[ \t]*([a-z0-9_~?#=%&/-]+)",
        r"\1\2",
        text,
        flags=re.IGNORECASE,
    )
    # Also handle hyphens at line breaks in URLs
    text = re.sub(
        r"(https?://[^\s]+|www\.[^\s]+)-[ \t]*\n[ \t]*([a-z0-9_~?#=%&/-]+)",
        r"\1\2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def clean_trailing_punctuation(url: str) -> str:
    """Strip common trailing punctuation that might get attached to URLs in resume text."""
    url = url.strip()
    while url and url[-1] in ('.', ',', ';', ':', ')', ']', '}', '>', '"', "'"):
        # Special check: keep closing paren if opening paren is inside URL
        if url[-1] == ')' and '(' in url and url.count('(') >= url.count(')'):
            break
        url = url[:-1]
    return url


def normalize_url(raw_url: str) -> str:
    """Normalize URL by ensuring scheme, lowercasing domain, removing tracking params, and stripping trailing slashes."""
    url = clean_trailing_punctuation(raw_url)
    if not url:
        return ""

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www.") and netloc not in ("www.linkedin.com", "www.github.com"):
            # Normalize www where standard
            pass

        path = parsed.path
        # Normalize double slashes in path
        path = re.sub(r"/{2,}", "/", path)
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        # Remove common analytics / tracking query parameters
        tracking_keys = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "source"}
        if parsed.query:
            query_dict = parse_qs(parsed.query, keep_blank_values=True)
            filtered_query = {k: v for k, v in query_dict.items() if k.lower() not in tracking_keys}
            new_query = urlencode(filtered_query, doseq=True)
        else:
            new_query = ""

        normalized = urlunparse((scheme, netloc, path, parsed.params, new_query, parsed.fragment))
        return normalized
    except Exception:
        return url


def classify_url(url: str) -> tuple[str, str, str]:
    """Classify a URL into (platform_name, detected_type, entity_identifier).
    
    Returns:
        (platform, category, identifier)
    """
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    domain = parsed.netloc.lower()

    for platform_name, category, regex in PLATFORM_RULES:
        match = regex.search(normalized)
        if match:
            identifier = match.group(1) if match.groups() else ""
            return platform_name, category, identifier

    # Generic checks
    if any(keyword in domain for keyword in ["portfolio", "about", "bio", "me."]) or domain.endswith(".dev") or domain.endswith(".me"):
        return "Personal Portfolio", "Portfolio Website", domain

    return "Web Link", "General Project / Website", domain


def extract_urls_from_text(text: str) -> list[dict]:
    """Extract, reconstruct, normalize, deduplicate, and classify all URLs found in resume text."""
    if not text:
        return []

    # Rejoin broken URLs across linebreaks
    reconstructed = reconstruct_cross_line_urls(text)

    raw_matches = URL_PATTERN.findall(reconstructed)
    # Also find loose patterns like github.com/user, linkedin.com/in/user, leetcode.com/user
    extra_patterns = [
        r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)?",
        r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_.-]+",
        r"(?:https?://)?(?:www\.)?leetcode\.com/(?:u/)?[a-zA-Z0-9_.-]+",
        r"(?:https?://)?(?:www\.)?hackerrank\.com/(?:profile/)?[a-zA-Z0-9_.-]+",
        r"(?:https?://)?(?:www\.)?codechef\.com/users/[a-zA-Z0-9_.-]+",
        r"(?:https?://)?(?:www\.)?codeforces\.com/profile/[a-zA-Z0-9_.-]+",
        r"(?:https?://)?(?:www\.)?geeksforgeeks\.org/user/[a-zA-Z0-9_.-]+",
        r"(?:https?://)?(?:www\.)?kaggle\.com/[a-zA-Z0-9_.-]+",
    ]
    for pat in extra_patterns:
        for m in re.finditer(pat, reconstructed, re.IGNORECASE):
            raw_matches.append(m.group(0))

    seen_urls = set()
    results = []

    for raw in raw_matches:
        cleaned = clean_trailing_punctuation(raw)
        norm = normalize_url(cleaned)
        if not norm or norm in seen_urls:
            continue

        # Ignore typical email addresses or file extensions that matched loosely
        if "@" in norm and not norm.startswith("http"):
            continue

        # Check if URL looks syntactically plausible
        parsed = urlparse(norm)
        if not parsed.netloc or "." not in parsed.netloc:
            continue

        seen_urls.add(norm)
        platform, category, identifier = classify_url(norm)

        results.append({
            "url": norm,
            "raw_match": raw,
            "platform": platform,
            "type": category,
            "identifier": identifier,
            "status": "Pending Verification",
            "accessible": None,
            "http_status": None,
            "error": None,
        })

    return results


def probe_url_accessibility(url: str) -> tuple[bool, int | None, str]:
    """Safely probe if a URL is publicly accessible without downloading large payloads.
    
    Returns:
        (is_accessible, http_status_code, status_summary)
    """
    safe, reason = is_safe_url(url)
    if not safe:
        return False, None, f"Blocked unsafe URL: {reason}"

    # Try safe fetch with HEAD or GET (limited to 16KB)
    success, status_code, content, msg = safe_fetch(
        url,
        method="GET",
        max_bytes=16 * 1024,
        timeout=5,
    )

    if not success:
        return False, status_code, msg

    if status_code in (200, 201, 202, 204, 304):
        return True, status_code, "Publicly Accessible (HTTP 200 OK)"
    elif status_code in (401, 403):
        return False, status_code, f"Restricted Access / Authentication Required (HTTP {status_code})"
    elif status_code == 404:
        return False, status_code, "Not Found (HTTP 404)"
    elif status_code == 429:
        return False, status_code, "Rate Limited (HTTP 429)"
    elif status_code and status_code >= 500:
        return False, status_code, f"Server Error (HTTP {status_code})"
    else:
        return False, status_code, f"HTTP Status {status_code}"
