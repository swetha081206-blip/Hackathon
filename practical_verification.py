"""Practical Skill Verification & Gemini-Based Project Understanding Assessment.

Generates project-specific architectural and algorithmic questions and safe coding challenges
by inspecting actual repository source code.
Evaluates candidate answers and code submissions safely via AST static analysis and Gemini AI reasoning
WITHOUT executing untrusted code on the host server.

Exports: fetch_repository_source_files, fetch_repository_details,
         generate_project_understanding_assessment, validate_python_code_statically,
         evaluate_practical_verification, validate_question_schema
"""

import ast
import json
import os
import random
import re
import requests
from gemini_service import call_gemini, clean_json_response
from security_utils import SAFE_USER_AGENT

GITHUB_API = "https://api.github.com"

# Maximum source file content size to fetch per file (30 KB)
MAX_FILE_CONTENT_BYTES = 30 * 1024

# Maximum total source content to send to Gemini
MAX_TOTAL_CODE_CONTEXT = 10_000


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


def _handle_rate_limit_response(resp: requests.Response) -> str:
    """Return a human-readable message for rate-limit and error responses."""
    if resp.status_code == 403:
        reset_ts = resp.headers.get("X-RateLimit-Reset", "")
        if reset_ts:
            try:
                from datetime import datetime, timezone
                reset_time = datetime.fromtimestamp(int(reset_ts), tz=timezone.utc).strftime("%H:%M UTC")
                return f"GitHub API rate limit reached; resets at {reset_time}. Add GITHUB_TOKEN to .env for higher limits."
            except Exception:
                pass
        return "GitHub API forbidden (403). Add GITHUB_TOKEN to .env for higher rate limits."
    if resp.status_code == 429:
        return "GitHub API rate limited (429). Please wait a moment and retry."
    if resp.status_code == 404:
        return "Repository not found or is private. Only public repositories are accessible."
    return f"GitHub API error (HTTP {resp.status_code})."


def fetch_repository_source_files(owner: str, repo_name: str, max_files: int = 3) -> list[dict]:
    """Fetch up to max_files prominent source files from the repository.

    - Targets main code files like app.py, main.py, index.js, or core classes.
    - Hard-capped at MAX_FILE_CONTENT_BYTES (30 KB) per file.
    - Handles rate limits, missing files, and inaccessible repos gracefully.
    - Never executes fetched code.
    """
    headers = _get_github_headers()
    repo_full = f"{owner}/{repo_name}"
    source_files = []

    preferred_extensions = (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".cpp", ".cs")
    skip_patterns = ("package-lock.json", "yarn.lock", ".min.js", "setup.py", ".test.", ".spec.")

    def _is_skippable(name: str) -> bool:
        nl = name.lower()
        return any(s in nl for s in skip_patterns)

    def _collect_from_dir(path: str) -> list[dict]:
        """Recursively collect eligible files from a directory path (1 level deep)."""
        items = []
        try:
            r = requests.get(
                f"{GITHUB_API}/repos/{repo_full}/contents/{path}",
                headers=headers,
                timeout=7,
            )
            if r.status_code in (403, 429, 404):
                return items
            if r.status_code == 200 and isinstance(r.json(), list):
                for entry in r.json():
                    n = entry.get("name", "")
                    if entry.get("type") == "file" and any(n.endswith(ext) for ext in preferred_extensions):
                        if not _is_skippable(n):
                            items.append(entry)
        except Exception:
            pass
        return items

    try:
        # Fetch repository root contents
        resp = requests.get(f"{GITHUB_API}/repos/{repo_full}/contents", headers=headers, timeout=8)
        if resp.status_code != 200:
            return []

        entries = resp.json()
        if not isinstance(entries, list):
            return []

        candidate_items: list[dict] = []
        for item in entries:
            name = item.get("name", "")
            if item.get("type") == "file" and any(name.endswith(ext) for ext in preferred_extensions):
                if not _is_skippable(name):
                    candidate_items.append(item)
            elif item.get("type") == "dir" and name.lower() in ("src", "app", "lib", "core", "api"):
                candidate_items.extend(_collect_from_dir(name))

        # Prioritize entry-point files
        def priority_key(item: dict) -> int:
            n = item.get("name", "").lower()
            return 0 if any(k in n for k in ("main", "app", "server", "index")) else 1

        candidate_items.sort(key=priority_key)

        for item in candidate_items[:max_files]:
            # Respect file size: skip files > 500 KB (GitHub reports size in bytes)
            file_size = item.get("size", 0)
            if file_size > 500_000:
                continue

            download_url = item.get("download_url")
            file_name = item.get("name", "source_file")
            file_path = item.get("path", file_name)

            if not download_url:
                continue
            try:
                f_resp = requests.get(
                    download_url,
                    headers={"User-Agent": SAFE_USER_AGENT},
                    timeout=8,
                    stream=True,
                )
                if f_resp.status_code == 200:
                    # Stream and cap at MAX_FILE_CONTENT_BYTES
                    chunks = []
                    total = 0
                    for chunk in f_resp.iter_content(chunk_size=4096):
                        if not chunk:
                            break
                        total += len(chunk)
                        chunks.append(chunk)
                        if total >= MAX_FILE_CONTENT_BYTES:
                            break
                    raw = b"".join(chunks)
                    content_text = raw.decode("utf-8", errors="replace")
                    source_files.append({
                        "name": file_name,
                        "path": file_path,
                        "content": content_text,
                        "size_bytes": total,
                    })
            except Exception:
                pass

    except Exception:
        pass

    return source_files


def fetch_repository_details(owner: str, repo_name: str) -> dict:
    """Fetch public repository metadata, languages, recent commits, and source files safely.

    Handles pagination (up to 30 commits), rate limits, missing files, and API errors.
    Never accesses private repositories without authorization.
    """
    headers = _get_github_headers()
    repo_full = f"{owner}/{repo_name}"
    details = {
        "owner": owner,
        "repo_name": repo_name,
        "full_name": repo_full,
        "description": "",
        "stars": 0,
        "forks": 0,
        "default_branch": "main",
        "is_fork": False,
        "languages": [],
        "recent_commits": [],
        "source_files": [],
        "readme": "",
        "rate_limited": False,
        "error_message": None,
    }

    try:
        # 1. Fetch metadata with timeout
        meta_resp = requests.get(f"{GITHUB_API}/repos/{repo_full}", headers=headers, timeout=8)
        if meta_resp.status_code in (403, 429):
            details["rate_limited"] = True
            details["error_message"] = _handle_rate_limit_response(meta_resp)
            return details
        elif meta_resp.status_code == 404:
            details["error_message"] = f"Repository '{repo_full}' not found or is private. Only public repositories can be inspected."
            return details
        elif meta_resp.status_code == 200:
            data = meta_resp.json()
            details["description"] = data.get("description") or "No description provided."
            details["stars"] = data.get("stargazers_count", 0)
            details["forks"] = data.get("forks_count", 0)
            details["default_branch"] = data.get("default_branch", "main")
            details["is_fork"] = data.get("fork", False)

        # 2. Fetch languages
        lang_resp = requests.get(f"{GITHUB_API}/repos/{repo_full}/languages", headers=headers, timeout=6)
        if lang_resp.status_code == 200:
            details["languages"] = list(lang_resp.json().keys())

        # 3. Fetch recent commits (up to 30, first page — no deeper pagination needed for questions)
        com_resp = requests.get(
            f"{GITHUB_API}/repos/{repo_full}/commits",
            headers=headers,
            params={"per_page": 30},
            timeout=8,
        )
        if com_resp.status_code in (403, 409):
            # 409 = empty repo; graceful skip
            pass
        elif com_resp.status_code == 200 and isinstance(com_resp.json(), list):
            for c in com_resp.json():
                commit_info = c.get("commit", {})
                author_info = commit_info.get("author", {})
                details["recent_commits"].append({
                    "sha": c.get("sha", "")[:7],
                    "author_name": author_info.get("name", ""),
                    "date": author_info.get("date", "")[:10],
                    "message": commit_info.get("message", "").split("\n")[0][:100],
                })

        # 4. Fetch prominent source code files (capped at 30 KB each)
        details["source_files"] = fetch_repository_source_files(owner, repo_name, max_files=3)

    except requests.exceptions.Timeout:
        details["error_message"] = "GitHub API request timed out. Please retry."
    except Exception as exc:
        details["error_message"] = f"Error connecting to GitHub: {type(exc).__name__}"

    return details


def validate_question_schema(q: dict, fallback_idx: int = 1, repo_name: str = "project") -> dict:
    """Validate and sanitize a generated question against strict schema requirements."""
    q_id = int(q.get("id", fallback_idx))
    category = str(q.get("category", "Architecture & Functions")).strip()
    q_type = "coding" if q.get("type") == "coding" or "coding" in category.lower() else "conceptual"
    question_text = str(q.get("question", "")).strip()

    if len(question_text) < 15:
        question_text = f"Explain the architectural decisions, data flow, and error handling patterns implemented in '{repo_name}'."

    expected_concepts = q.get("expected_concepts") or q.get("expected_key_points") or []
    if not isinstance(expected_concepts, list) or not expected_concepts:
        expected_concepts = ["Clear understanding of code components", "Awareness of edge cases and trade-offs"]

    difficulty = str(q.get("difficulty", "Intermediate")).strip().capitalize()
    if difficulty not in ("Beginner", "Intermediate", "Advanced"):
        difficulty = "Intermediate"

    time_limit = int(q.get("time_limit_seconds", 120))
    time_limit = max(45, min(300, time_limit))

    source_file_ref = str(q.get("source_file_ref", "main codebase")).strip()
    is_general_fallback = bool(q.get("is_general_fallback", False))

    return {
        "id": q_id,
        "category": category,
        "type": q_type,
        "question": question_text,
        "expected_concepts": [str(c).strip() for c in expected_concepts if str(c).strip()],
        "difficulty": difficulty,
        "time_limit_seconds": time_limit,
        "source_file_ref": source_file_ref,
        "is_general_fallback": is_general_fallback,
    }


def generate_project_understanding_assessment(
    repo_name: str,
    readme_text: str,
    source_files: list[dict],
    commits_data: list[dict] | None = None,
    shuffle_questions: bool = True,
) -> dict:
    """Generate repository-grounded technical questions and a practical coding challenge.

    Questions are validated against a strict schema before being returned.
    If shuffle_questions is True, questions are randomly shuffled to reduce ordering effects.
    """
    # Build context from actual source code files
    code_snippets = []
    has_real_files = bool(source_files)

    for sf in source_files:
        snippet = sf["content"][:2500]
        code_snippets.append(f"--- FILE: {sf['path']} ---\n{snippet}\n")

    code_context = "\n".join(code_snippets) if code_snippets else f"README:\n{readme_text[:2000]}"
    commits_context = ""
    if commits_data:
        commits_context = "RECENT COMMITS IN REPO:\n" + "\n".join(
            [f"- {c.get('sha')}: {c.get('message')} by {c.get('author_name')}" for c in commits_data[:5]]
        )

    prompt = f"""You are a senior technical interviewer. Inspect the actual source code, commits, and documentation
of the GitHub project "{repo_name}" provided below.

Generate a realistic, deep Project Understanding Assessment that tests whether a candidate truly wrote,
designed, or thoroughly understands this codebase.

SOURCE CODE CONTEXT:
{code_context[:9000]}

{commits_context}

REQUIREMENTS:
1. Base every question on specific functions, classes, data flow, or commits present in the source code.
2. Generate exactly 5 technical understanding questions:
   - Question 1 (Architecture & Functions): Explain specific functions, classes, and algorithms (cite exact file & function).
   - Question 2 (Data Structures & Design Choices): Why a particular data structure, library, or pattern was chosen.
   - Question 3 (Debugging & Realistic Bug Scenario): A realistic bug or debugging scenario in this codebase and how to fix it.
   - Question 4 (Edge Cases & Complexity): Edge cases, time/space complexity, and alternative implementations.
   - Question 5 (Contributions & Project Commits): Documented contributions, commits, or feature integration in this project.
3. For each question specify:
   - "difficulty": "Beginner", "Intermediate", or "Advanced"
   - "time_limit_seconds": Integer between 60 and 180 seconds
   - "source_file_ref": File path and function name (e.g. "app/main.py:process_data")
   - "expected_concepts": List of 2-3 key technical points expected in a strong answer
4. Generate 1 practical coding challenge:
   - Realistic task (e.g. adding input validation, optimizing a loop, implementing an edge case handler, or writing a unit test).
   - Provide clean starter code and step-by-step instructions.

Return ONLY a valid JSON object with EXACTLY this structure:
{{
  "project_name": "{repo_name}",
  "questions": [
    {{
      "id": 1,
      "category": "Architecture & Functions",
      "question": "Question text citing specific file/function",
      "source_file_ref": "path/to/file.py:function_name",
      "difficulty": "Intermediate",
      "time_limit_seconds": 120,
      "expected_concepts": ["Concept 1", "Concept 2"]
    }},
    {{
      "id": 2,
      "category": "Data Structures & Design Choices",
      "question": "Question text citing specific data structure/pattern",
      "source_file_ref": "path/to/file.py",
      "difficulty": "Intermediate",
      "time_limit_seconds": 120,
      "expected_concepts": ["Concept 1", "Concept 2"]
    }},
    {{
      "id": 3,
      "category": "Debugging & Realistic Bug Scenario",
      "question": "Question text describing a realistic bug scenario in this codebase",
      "source_file_ref": "path/to/file.py",
      "difficulty": "Advanced",
      "time_limit_seconds": 150,
      "expected_concepts": ["Concept 1", "Concept 2"]
    }},
    {{
      "id": 4,
      "category": "Edge Cases & Complexity",
      "question": "Question text analyzing asymptotic complexity and edge case handling",
      "source_file_ref": "path/to/file.py",
      "difficulty": "Intermediate",
      "time_limit_seconds": 120,
      "expected_concepts": ["Concept 1", "Concept 2"]
    }},
    {{
      "id": 5,
      "category": "Contributions & Project Commits",
      "question": "Question about candidate's documented contributions, commits, or feature integration",
      "source_file_ref": "repository history",
      "difficulty": "Intermediate",
      "time_limit_seconds": 90,
      "expected_concepts": ["Concept 1", "Concept 2"]
    }}
  ],
  "coding_challenge": {{
    "title": "Short title of coding challenge",
    "instructions": "Clear step-by-step instructions on what to write or modify",
    "starter_code": "def example_function():\\n    # Your implementation here\\n    pass",
    "time_limit_seconds": 180,
    "difficulty": "Intermediate",
    "source_file_ref": "path/to/file.py",
    "evaluation_criteria": ["Handles empty input", "Returns expected data type", "Proper error handling"]
  }}
}}
"""
    success, response_text, _ = call_gemini(prompt)
    if success:
        try:
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            if "questions" in data and isinstance(data["questions"], list) and len(data["questions"]) >= 3:
                validated_questions = []
                for idx, q in enumerate(data["questions"], start=1):
                    vq = validate_question_schema(q, fallback_idx=idx, repo_name=repo_name)
                    if not has_real_files:
                        vq["is_general_fallback"] = True
                        if "[General Fallback Question]" not in vq["question"]:
                            vq["question"] = f"[General Fallback Question: Limited Code Context] {vq['question']}"
                    validated_questions.append(vq)
                if shuffle_questions and len(validated_questions) > 1:
                    # Shuffle conceptual questions but keep coding challenge separate
                    random.shuffle(validated_questions)
                    # Re-number after shuffle to maintain sequential display IDs
                    for new_idx, vq in enumerate(validated_questions, start=1):
                        vq["display_order"] = new_idx
                data["questions"] = validated_questions
                return data
        except Exception:
            pass

    # Deterministic fallback assessment tailored to project
    first_file = source_files[0]["name"] if source_files else "main module"
    first_path = source_files[0]["path"] if source_files else "app/main.py"
    prefix = "" if has_real_files else "[General Fallback Question: Limited Code Context] "

    fallback_questions = [
        {
            "id": 1,
            "category": "Architecture & Functions",
            "type": "conceptual",
            "question": f"{prefix}Explain the high-level architecture of '{repo_name}'. How does data or control flow into `{first_path}` and how are states or outputs managed?",
            "source_file_ref": f"{first_path}:main_controller",
            "difficulty": "Intermediate",
            "time_limit_seconds": 120,
            "is_general_fallback": not has_real_files,
            "expected_concepts": [
                "Identifies entry point and main controller/service flow",
                "Explains how external inputs are validated and processed",
            ],
        },
        {
            "id": 2,
            "category": "Data Structures & Design Choices",
            "type": "conceptual",
            "question": f"{prefix}What core data structures or third-party libraries did you choose in '{repo_name}', and what technical trade-offs influenced your decision over alternatives?",
            "source_file_ref": f"{first_path}:data_models",
            "difficulty": "Intermediate",
            "time_limit_seconds": 120,
            "is_general_fallback": not has_real_files,
            "expected_concepts": [
                "Discusses time/space complexity or library trade-offs",
                "Explains why alternatives were rejected",
            ],
        },
        {
            "id": 3,
            "category": "Debugging & Realistic Bug Scenario",
            "type": "conceptual",
            "question": f"{prefix}Describe a realistic bug scenario in '{repo_name}' (e.g. concurrent state modification, database timeout, or unhandled null reference). How would you diagnose and resolve it?",
            "source_file_ref": f"{first_path}:error_handler",
            "difficulty": "Advanced",
            "time_limit_seconds": 150,
            "is_general_fallback": not has_real_files,
            "expected_concepts": [
                "Identifies failure point and logging/telemetry tools",
                "Proposes defensive fix with boundary validation",
            ],
        },
        {
            "id": 4,
            "category": "Edge Cases & Complexity",
            "type": "conceptual",
            "question": f"{prefix}How does '{repo_name}' handle extreme edge cases such as empty input arrays, unexpected unicode characters, or high-volume traffic spikes? What is the asymptotic time complexity?",
            "source_file_ref": f"{first_path}:boundary_checks",
            "difficulty": "Intermediate",
            "time_limit_seconds": 120,
            "is_general_fallback": not has_real_files,
            "expected_concepts": [
                "Evaluates boundary limits and sanitize routines",
                "States asymptotic time and space complexity",
            ],
        },
        {
            "id": 5,
            "category": "Contributions & Project Commits",
            "type": "conceptual",
            "question": f"{prefix}What specific features, pull requests, or commits did you personally author in '{repo_name}'? Describe a challenging implementation detail you resolved.",
            "source_file_ref": "repository commit log",
            "difficulty": "Intermediate",
            "time_limit_seconds": 90,
            "is_general_fallback": not has_real_files,
            "expected_concepts": [
                "Articulates personal engineering contribution",
                "Explains problem-solving process and commit rationale",
            ],
        },
    ]

    validated_fallback = [validate_question_schema(q, fallback_idx=q["id"], repo_name=repo_name) for q in fallback_questions]
    if shuffle_questions and len(validated_fallback) > 1:
        random.shuffle(validated_fallback)
        for new_idx, vq in enumerate(validated_fallback, start=1):
            vq["display_order"] = new_idx
    return {
        "project_name": repo_name,
        "questions": validated_fallback,
        "coding_challenge": {
            "title": f"Defensive Input Sanitizer & Validation for {repo_name}",
            "instructions": "Implement a defensive validation helper function that sanitizes input parameters, checks boundary conditions, and raises a ValueError with an informative message if validation fails.",
            "starter_code": "def validate_input_payload(data: dict) -> bool:\n    \"\"\"Validate that data contains required non-empty fields and valid values.\"\"\"\n    if not isinstance(data, dict) or not data:\n        raise ValueError(\"Payload must be a non-empty dictionary\")\n    \n    # Implement additional field checks below\n    return True\n",
            "time_limit_seconds": 180,
            "difficulty": "Intermediate",
            "source_file_ref": f"{first_path}:validation",
            "evaluation_criteria": [
                "Handles None and non-dict inputs",
                "Validates data types and ranges",
                "Clean, readable syntax without dangerous constructs",
            ],
        },
    }


def validate_python_code_statically(code_str: str) -> tuple[bool, str]:
    """Safely validate submitted Python code via static AST analysis without executing it.
    
    Checks:
    - Syntax validity.
    - Rejects dangerous / malicious constructs (os.system, subprocess, eval, exec, __import__, socket).
    """
    if not code_str or not code_str.strip():
        return False, "Code submission is empty."

    # Security check: disallow system command execution and arbitrary code execution builtins
    disallowed_terms = ["os.system", "subprocess", "eval(", "exec(", "__import__", "importlib", "shutil.rmtree"]
    for term in disallowed_terms:
        if term in code_str:
            return False, f"Code contains disallowed unsafe construct: '{term}'."

    try:
        parsed = ast.parse(code_str)
        # Verify AST has at least one function or assignment
        nodes = list(ast.walk(parsed))
        has_logic = any(isinstance(n, (ast.FunctionDef, ast.Assign, ast.If, ast.Return, ast.For, ast.While)) for n in nodes)
        if not has_logic:
            return False, "Code must contain at least one function, assignment, or control structure."
        return True, "Syntax is valid and safe."
    except SyntaxError as syn_err:
        return False, f"Python SyntaxError at line {syn_err.lineno}: {syn_err.msg}"
    except Exception as exc:
        return False, f"Static analysis error: {exc}"


def evaluate_practical_verification(
    assessment: dict,
    candidate_answers: dict[int, str],
    submitted_code: str,
    source_files: list[dict],
    time_records: dict[int, dict] | None = None,
) -> dict:
    """Evaluate candidate's written technical answers and practical coding challenge submission.
    
    Produces separate project understanding and coding performance scores,
    and clearly separates factual repository signals from AI inferences.
    """
    # 1. Static validation of code
    is_valid_syntax, static_feedback = validate_python_code_statically(submitted_code)

    # 2. Prepare prompt for Gemini evaluation
    q_and_a = []
    questions_list = assessment.get("questions", [])
    t_records = time_records or {}

    for q in questions_list:
        q_id = q["id"]
        ans = candidate_answers.get(q_id, "").strip() or "No answer provided"
        time_spent = t_records.get(q_id, {}).get("time_spent_seconds", 0)
        timed_out = t_records.get(q_id, {}).get("timed_out", False)
        timeout_note = " [AUTO-SUBMITTED ON TIMER EXPIRY]" if timed_out else ""
        q_and_a.append(
            f"QUESTION {q_id} ({q['category']}) [Ref: {q.get('source_file_ref', 'N/A')}] [Time spent: {time_spent}s{timeout_note}]:\n"
            f"Question Text: {q['question']}\n"
            f"Expected Concepts: {', '.join(q.get('expected_concepts', []))}\n"
            f"Candidate Answer: {ans}\n"
        )

    qa_text = "\n".join(q_and_a)
    challenge = assessment.get("coding_challenge", {})

    prompt = f"""You are an objective technical interviewer evaluating a candidate's project understanding
and practical coding challenge for the project "{assessment.get('project_name')}".

CANDIDATE'S ANSWERS TO TECHNICAL UNDERSTANDING QUESTIONS:
{qa_text}

PRACTICAL CODING CHALLENGE:
Title: {challenge.get('title')}
Instructions: {challenge.get('instructions')}
Evaluation Criteria: {', '.join(challenge.get('evaluation_criteria', []))}

CANDIDATE'S CODE SUBMISSION:
```python
{submitted_code[:4000]}
```

STATIC SYNTAX CHECK RESULT: {static_feedback}

EVALUATION RULES:
1. Objectively evaluate whether the candidate's answers demonstrate genuine familiarity with the codebase.
2. Separate FACTUAL signals (syntax valid, questions answered within deadline, lines of code) from AI INFERENCES (understanding depth, confidence).
3. Compute two separate scores from 0 to 100:
   - "project_understanding_score": 0-100 based on the 5 technical understanding questions.
   - "coding_performance_score": 0-100 based on coding challenge correctness, defensive validation, and style.
4. "practical_score": Weighted combination (60% understanding + 40% coding).

Return ONLY a valid JSON object with EXACTLY this structure:
{{
  "project_understanding_score": 85,
  "coding_performance_score": 80,
  "practical_score": 83,
  "status_summary": "Strong Practical Competency",
  "question_evaluations": [
    {{
      "question_id": 1,
      "score": 90,
      "source_file_ref": "path/file.py",
      "correct_aspects": "Accurately identified data flow and entry point.",
      "incomplete_aspects": "Did not specify how error states are serialized."
    }}
  ],
  "coding_challenge_evaluation": {{
    "syntax_valid": {str(is_valid_syntax).lower()},
    "logic_score": 80,
    "strengths": ["Clean input validation", "Proper exception raising"],
    "areas_for_improvement": ["Consider handling whitespace-only strings"]
  }},
  "factual_signals": [
    "Code AST parsed with 0 syntax errors.",
    "Candidate submitted responses for all assessment questions.",
    "Static code avoids all prohibited system call operations."
  ],
  "ai_inferences": [
    "Candidate demonstrates strong architectural familiarity with the repository.",
    "Explanations align with source file implementation details."
  ],
  "overall_feedback": "Candidate demonstrates authentic familiarity with the architecture and writes clean, safe code.",
  "limitations": "Evaluates submitted text and static AST code quality without runtime execution on the host server."
}}
"""
    success, response_text, _ = call_gemini(prompt)
    if success:
        try:
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            pu_score = max(0, min(100, int(data.get("project_understanding_score", 75))))
            cp_score = max(0, min(100, int(data.get("coding_performance_score", 75))))
            data["project_understanding_score"] = pu_score
            data["coding_performance_score"] = cp_score
            data["practical_score"] = max(0, min(100, int(data.get("practical_score", round(0.6 * pu_score + 0.4 * cp_score)))))
            
            # Enrich question evaluations with time records
            for qe in data.get("question_evaluations", []):
                qid = qe.get("question_id")
                if qid in t_records:
                    qe["time_spent_seconds"] = t_records[qid].get("time_spent_seconds", 0)
                    qe["timed_out"] = t_records[qid].get("timed_out", False)
                qe["answer_text"] = candidate_answers.get(qid, "")

            return data
        except Exception:
            pass

    # Deterministic fallback evaluation if Gemini is unavailable
    ans_lens = [len(ans.strip()) for ans in candidate_answers.values()]
    avg_len = sum(ans_lens) / len(ans_lens) if ans_lens else 0

    pu_score = min(85, max(30, int(avg_len / 3.5)))
    cp_score = 75 if is_valid_syntax else 30
    overall = round(0.6 * pu_score + 0.4 * cp_score)

    q_evals = []
    for q in questions_list:
        qid = q["id"]
        q_ans = candidate_answers.get(qid, "").strip()
        t_info = t_records.get(qid, {})
        q_evals.append({
            "question_id": qid,
            "score": pu_score if q_ans else 20,
            "source_file_ref": q.get("source_file_ref", "codebase"),
            "time_spent_seconds": t_info.get("time_spent_seconds", 0),
            "timed_out": t_info.get("timed_out", False),
            "answer_text": q_ans,
            "correct_aspects": "Addressed core technical question points." if q_ans else "No response provided.",
            "incomplete_aspects": "Deterministic baseline evaluation; reviewer manual audit recommended.",
        })

    return {
        "project_understanding_score": pu_score,
        "coding_performance_score": cp_score,
        "practical_score": overall,
        "status_summary": "Evaluated via Rule-Based Benchmark",
        "question_evaluations": q_evals,
        "coding_challenge_evaluation": {
            "syntax_valid": is_valid_syntax,
            "logic_score": cp_score,
            "strengths": ["Static syntax validation passed" if is_valid_syntax else "Attempted submission"],
            "areas_for_improvement": [static_feedback if not is_valid_syntax else "Add automated unit test suite"],
        },
        "factual_signals": [
            f"Static Python AST validation: {'Passed' if is_valid_syntax else 'Failed'}.",
            f"Questions answered: {sum(1 for a in candidate_answers.values() if a.strip())} / {len(questions_list)}.",
            f"Source files inspected: {len(source_files)} files.",
        ],
        "ai_inferences": [
            "Candidate responses evaluated under deterministic fallback rule engine.",
        ],
        "overall_feedback": "Candidate answers and code passed baseline static structure checks.",
        "limitations": "Deterministic baseline evaluation; AI reasoning service was temporarily offline.",
    }

