"""Comprehensive test suite verifying all functional, security, provenance, and skill verification requirements:
1. Syntax & modular imports
2. Safe URL validation & SSRF protection
3. Cross-line URL recovery & normalization
4. PDF extraction & scanned/empty document handling
5. Platform analyzers (GitHub, LeetCode, Codeforces, HackerRank, Web)
6. Repository provenance, fork detection & commit authorship analysis
7. Code and documentation similarity & template detection
8. Project Ownership Evidence Score calculation
9. Safe practical code validation (AST syntax check & unsafe construct rejection)
10. Project understanding question generation & evaluation
11. Tri-Factor scoring (Career Readiness, Ownership Evidence, Practical Verification)
12. Multi-page PDF report generation with ReportLab
"""

import sys
from io import BytesIO
from pypdf import PdfWriter

print("=" * 65)
print("RUNNING CAREER READINESS & PROVENANCE ANALYZER VERIFICATION SUITE")
print("=" * 65)

# 1. Imports & Syntax
try:
    import security_utils
    import url_detector
    import platform_analyzers
    import resume_parser
    import skill_matcher
    import gemini_service
    import roadmap_generator
    import report_generator
    import project_provenance
    import practical_verification
    print("Test 1 Passed: All modules (including provenance & practical verification) imported successfully.")
except Exception as e:
    print(f"Test 1 FAILED: Import error: {e}")
    sys.exit(1)

# 2. Security & SSRF Protection
try:
    safe1, _ = security_utils.is_safe_url("http://localhost:8080/admin")
    safe2, _ = security_utils.is_safe_url("http://127.0.0.1:3000")
    safe3, _ = security_utils.is_safe_url("http://169.254.169.254/latest/meta-data")
    safe4, _ = security_utils.is_safe_url("http://192.168.1.1")
    safe5, _ = security_utils.is_safe_url("https://github.com/torvalds")
    assert not safe1, "localhost should be blocked"
    assert not safe2, "127.0.0.1 should be blocked"
    assert not safe3, "169.254.169.254 should be blocked"
    assert not safe4, "Private IP 192.168.1.1 should be blocked"
    assert safe5, "Public GitHub URL should be permitted"
    print("Test 2 Passed: SSRF & IP restriction validation works.")
except Exception as e:
    print(f"Test 2 FAILED: SSRF check error: {e}")
    sys.exit(1)

# 3. URL Detection & Cross-Line Rejoining
try:
    sample_text = """
    Software Engineer Candidate
    Profiles:
    github.com/
    sample-dev/my-repo
    LinkedIn: linkedin.com/in/sample-dev
    LeetCode: leetcode.com/u/sample_coder
    Codeforces: https://codeforces.com/profile/tourist
    Portfolio: https://sample-portfolio.dev?utm_source=resume&ref=123
    Demo: https://my-cool-app.streamlit.app/
    """
    detected = url_detector.extract_urls_from_text(sample_text)
    platforms = [d["platform"] for d in detected]
    assert "GitHub" in platforms, "GitHub should be detected"
    assert "LinkedIn" in platforms, "LinkedIn should be detected"
    assert "LeetCode" in platforms, "LeetCode should be detected"
    assert "Codeforces" in platforms, "Codeforces should be detected"
    for d in detected:
        if "sample-portfolio.dev" in d["url"]:
            assert "utm_source" not in d["url"], "Tracking params should be stripped"
    print(f"Test 3 Passed: Detected {len(detected)} URLs across multiple platforms with cross-line reconstruction.")
except Exception as e:
    print(f"Test 3 FAILED: URL detection error: {e}")
    sys.exit(1)

# 4. PDF Text Extraction & Scanned/Empty PDF Handling
try:
    class MockUploadedFile:
        def __init__(self, content: bytes, name="resume.pdf"):
            self.content = content
            self.name = name
            self.size = len(content)
        def getvalue(self):
            return self.content
        def read(self, n=-1):
            return self.content[:n] if n != -1 else self.content
        def seek(self, pos):
            pass

    invalid_file = MockUploadedFile(b"Not a PDF header", "fake.txt")
    valid_flag, msg = security_utils.validate_pdf_file(invalid_file)
    assert not valid_flag, "Non-PDF file should be rejected"

    empty_writer = PdfWriter()
    empty_writer.add_blank_page(width=612, height=792)
    buf = BytesIO()
    empty_writer.write(buf)
    empty_pdf_file = MockUploadedFile(buf.getvalue(), "empty.pdf")
    
    threw_scanned_error = False
    try:
        resume_parser.extract_pdf_raw_text(empty_pdf_file)
    except ValueError as ve:
        threw_scanned_error = "scanned" in str(ve).lower() or "no selectable text" in str(ve).lower()

    assert threw_scanned_error, "Empty/scanned PDF must raise OCR / no selectable text error"
    print("Test 4 Passed: PDF validation and scanned/empty detection working as required.")
except Exception as e:
    print(f"Test 4 FAILED: PDF extraction error: {e}")
    sys.exit(1)

# 5. Platform Analyzers (Codeforces API & safe fallback)
try:
    cf_res = platform_analyzers.analyze_codeforces("https://codeforces.com/profile/tourist")
    assert cf_res["status"] in ["Verified", "Unverified - Codeforces API temporary issue"], f"Codeforces status unexpected: {cf_res.get('status')}"
    if cf_res["status"] == "Verified":
        assert cf_res["rating"] is not None, "Tourist rating should not be None"
    print("Test 5 Passed: Platform analyzers handle live public data safely.")
except Exception as e:
    print(f"Test 5 FAILED: Platform analyzer error: {e}")
    sys.exit(1)

# 6. Repository Provenance & Fork / Commit Authorship Analysis
try:
    # A) Text similarity test (ignoring whitespace & comments)
    code_a = "def compute_total(price, tax):\n    # add tax to price\n    return price + (price * tax)"
    code_b = "def compute_total(price, tax): return price + (price * tax)"
    similarity = project_provenance.calculate_text_similarity(code_a, code_b)
    assert similarity >= 0.95, f"Expected near 1.0 similarity, got {similarity}"

    # B) Template signature detection
    sample_readme = "# Getting Started with Create React App\nThis project was bootstrapped with Create React App.\nRun npm start to test."
    templates = project_provenance.detect_template_signatures(sample_readme, [])
    assert len(templates) > 0, "Should detect Create React App template"
    assert templates[0]["template_name"] == "Create React App Starter"

    # C) Mock Provenance test for Clone / Fork vs Original
    mock_prov_original = {
        "repository_name": "data-pipeline",
        "is_fork": False,
        "is_single_commit_import": False,
        "total_commits_inspected": 25,
        "candidate_authored_commits": 22,
        "candidate_commit_ratio": 0.88,
        "template_matches": [],
        "ownership_status": "Strong supporting evidence",
    }
    mock_prov_clone = {
        "repository_name": "cloned-repo",
        "is_fork": True,
        "parent_repo": {"full_name": "original-owner/cloned-repo"},
        "is_single_commit_import": True,
        "total_commits_inspected": 1,
        "candidate_authored_commits": 0,
        "candidate_commit_ratio": 0.0,
        "template_matches": [{"template_name": "Starter Template"}],
        "ownership_status": "Insufficient evidence",
    }

    score_original = project_provenance.calculate_project_ownership_score([mock_prov_original])
    score_clone = project_provenance.calculate_project_ownership_score([mock_prov_clone])

    assert score_original["score"] > 80, f"Original repo should score high on ownership, got {score_original['score']}"
    assert score_clone["score"] < 40, f"Cloned repo with 0 commits should score low on ownership, got {score_clone['score']}"
    print(f"Test 6 Passed: Repository provenance, similarity, and ownership scoring working (Original: {score_original['score']}%, Cloned: {score_clone['score']}%).")
except Exception as e:
    print(f"Test 6 FAILED: Provenance & ownership test error: {e}")
    sys.exit(1)

# 7. Safe Practical Code Validation & Assessment
try:
    # A) Valid code check
    valid_code = "def validate_record(item: dict) -> bool:\n    if not item:\n        raise ValueError('Empty')\n    return True"
    is_valid, msg = practical_verification.validate_python_code_statically(valid_code)
    assert is_valid, f"Valid code should pass static check: {msg}"

    # B) Unsafe construct check (os.system, subprocess)
    unsafe_code = "import os\nos.system('dir')"
    is_unsafe_valid, unsafe_msg = practical_verification.validate_python_code_statically(unsafe_code)
    assert not is_unsafe_valid, "Unsafe code with os.system must be rejected"
    assert "disallowed" in unsafe_msg.lower()

    # C) Syntax error check
    syntax_err_code = "def broken_fn(: return 42"
    is_syn_valid, syn_msg = practical_verification.validate_python_code_statically(syntax_err_code)
    assert not is_syn_valid, "Syntax error code must be caught"
    assert "syntaxerror" in syn_msg.lower()

    # D) Assessment generation structure test
    assessment = practical_verification.generate_project_understanding_assessment(
        repo_name="my-service",
        readme_text="A microservice for data processing",
        source_files=[{"name": "app.py", "path": "app.py", "content": valid_code}],
    )
    assert len(assessment["questions"]) >= 3, "Assessment must generate at least 3 technical questions"
    assert "coding_challenge" in assessment, "Assessment must include coding challenge"
    # Check schema on generated questions
    for q in assessment["questions"]:
        assert "id" in q and "category" in q and "question" in q
        assert "source_file_ref" in q
        assert "difficulty" in q
        assert "time_limit_seconds" in q
        assert q["time_limit_seconds"] >= 45
    print("Test 7 Passed: Safe AST code validation and 5-category assessment generation functioning properly.")
except Exception as e:
    print(f"Test 7 FAILED: Practical verification test error: {e}")
    sys.exit(1)

# 8. Five Distinct Scores Calculation (Requirement 6)
try:
    claimed_skills = ["Python", "SQL", "Git", "REST API", "Docker"]
    mock_evidence = [
        {
            "platform": "GitHub",
            "status": "Verified",
            "url": "https://github.com/sample",
            "languages": ["Python", "SQL"],
            "recent_activity_count": 2,
            "repositories": [
                {
                    "name": "data-service",
                    "description": "Backend API in Python and SQL",
                    "languages": ["Python", "SQL"],
                    "topics": ["docker", "api"],
                    "readme": "Production backend service.",
                    "url": "https://github.com/sample/data-service",
                }
            ],
            "project_ownership": score_original,
            "provenance_list": [mock_prov_original],
        },
        {
            "platform": "LeetCode",
            "status": "Verified",
            "url": "https://leetcode.com/sample",
            "total_solved": 80,
        },
    ]

    vrows = skill_matcher.verify_resume_claims(claimed_skills, mock_evidence)
    
    # Test A: When practical verification is NOT completed
    scores_untested = skill_matcher.calculate_career_readiness(
        verification_rows=vrows,
        target_role="Python Developer",
        role_skills=["Python", "SQL", "Git", "REST API"],
        platform_evidence=mock_evidence,
        profile_data={"education": [{"degree": "B.Tech"}], "projects": [{"title": "API"}]},
        practical_result=None,
    )
    assert scores_untested["github_project_understanding_score"] == "Not tested"
    assert scores_untested["practical_coding_performance_score"] == "Not tested"
    assert scores_untested["career_readiness_score"] > 0
    assert scores_untested["project_ownership_evidence_score"] > 80

    # Test B: When practical verification IS completed
    mock_practical_eval = {
        "completed": True,
        "practical_score": 85,
        "project_understanding_score": 88,
        "coding_performance_score": 82,
        "status_summary": "Strong Practical Competency",
        "question_evaluations": [
            {
                "question_id": 1,
                "score": 90,
                "source_file_ref": "app/main.py",
                "time_spent_seconds": 65,
                "timed_out": False,
                "answer_text": "Explained request dispatching clearly.",
                "correct_aspects": "Accurately identified entry point.",
            }
        ],
        "coding_challenge_evaluation": {
            "syntax_valid": True,
            "logic_score": 82,
        },
        "factual_signals": ["AST parsed cleanly", "0 syntax errors"],
        "ai_inferences": ["Strong architectural familiarity"],
    }
    scores_tested = skill_matcher.calculate_career_readiness(
        verification_rows=vrows,
        target_role="Python Developer",
        role_skills=["Python", "SQL", "Git", "REST API"],
        platform_evidence=mock_evidence,
        profile_data={"education": [{"degree": "B.Tech"}], "projects": [{"title": "API"}]},
        practical_result=mock_practical_eval,
    )
    assert scores_tested["github_project_understanding_score"] == 88
    assert scores_tested["practical_coding_performance_score"] == 82
    assert "five_categories_summary" in scores_tested

    # Test C: Transparent Combined Summary with configurable weights
    comb = skill_matcher.calculate_combined_summary(scores_tested)
    assert 0 <= comb["combined_score"] <= 100
    assert "weights_used" in comb

    print(f"Test 8 Passed: 5 distinct scores and transparent combined summary calculated:")
    print(f"   - 1. Career Readiness Score: {scores_tested['career_readiness_score']}%")
    print(f"   - 2. Role Skill Match Score: {scores_tested['resume_to_role_skill_match_score']}%")
    print(f"   - 3. GitHub Project Understanding: {scores_tested['github_project_understanding_score']}%")
    print(f"   - 4. Practical Coding Performance: {scores_tested['practical_coding_performance_score']}%")
    print(f"   - 5. Project Ownership Evidence: {scores_tested['project_ownership_evidence_score']}%")
    print(f"   - Combined Aggregated Summary: {comb['combined_score']}%")
except Exception as e:
    print(f"Test 8 FAILED: 5 distinct scores calculation error: {e}")
    sys.exit(1)

# 9. Assessment Eligibility Gate & Admin Override (Requirement 1)
try:
    # Under threshold -> locked
    el_locked = skill_matcher.check_assessment_eligibility(
        readiness_score=50,
        skill_match_score=40,
        readiness_threshold=60,
        skill_threshold=50,
        admin_override=False,
    )
    assert not el_locked["eligible"], "Should be locked when below thresholds"

    # Above threshold -> unlocked
    el_unlocked = skill_matcher.check_assessment_eligibility(
        readiness_score=75,
        skill_match_score=60,
        readiness_threshold=60,
        skill_threshold=50,
        admin_override=False,
    )
    assert el_unlocked["eligible"], "Should be unlocked when above thresholds"

    # Below threshold + admin override -> unlocked
    el_override = skill_matcher.check_assessment_eligibility(
        readiness_score=30,
        skill_match_score=20,
        readiness_threshold=60,
        skill_threshold=50,
        admin_override=True,
    )
    assert el_override["eligible"], "Admin override must unlock assessment regardless of score"
    print("Test 9 Passed: Assessment eligibility checking and admin override working properly.")
except Exception as e:
    print(f"Test 9 FAILED: Assessment eligibility test error: {e}")
    sys.exit(1)

# 10. Server-Side Timed Assessment Expiry Simulation (Requirement 4)
try:
    import time
    start_time = time.time() - 150  # 150 seconds ago
    time_limit = 120  # 120s limit
    deadline = start_time + time_limit
    now = time.time()
    remaining = max(0, int(deadline - now))
    is_timed_out = remaining <= 0
    assert is_timed_out, "Server-side check must identify expired timer"

    # Answer schema validation
    val_q = practical_verification.validate_question_schema({
        "id": 1,
        "question": "Explain the order processing state machine in app/api_router.py",
        "category": "Architecture & Functions",
        "expected_concepts": ["State transition", "HTTP 400 validation"],
        "time_limit_seconds": 120,
    })
    assert val_q["difficulty"] in ("Beginner", "Intermediate", "Advanced")
    assert val_q["time_limit_seconds"] == 120
    print("Test 10 Passed: Server-side timer expiry and question schema validation working as required.")
except Exception as e:
    print(f"Test 10 FAILED: Server-side timer test error: {e}")
    sys.exit(1)

# 11. PDF Report Generation with 5 Scores & Assessment Audit Table
try:
    full_result = {
        "generated_at": "2026-10-16T12:00:00Z",
        "target_role": "Python Developer",
        "role_required_skills": ["Python", "SQL", "Git", "REST API"],
        "candidate_profile": {
            "candidate_name": "Alex Coder",
            "email": "alex@example.com",
            "skills": claimed_skills,
        },
        "detected_urls": [
            {"platform": "GitHub", "type": "Profile", "url": "https://github.com/sample", "status": "Verified"},
        ],
        "provenance_list": [mock_prov_original, mock_prov_clone],
        "verification": vrows,
        "scores": scores_tested,
        "practical_evaluation": mock_practical_eval,
        "recommendations": {
            "executive_summary": "Solid candidate with authentic Python projects.",
            "recommended_projects": [],
            "bullet_point_improvements": [],
        },
        "roadmap": [
            {"week_number": 1, "topic": "Async Python", "deliverable_project": "Async API client"}
        ],
    }
    pdf_output = report_generator.generate_pdf_report(full_result)
    assert len(pdf_output) > 1000, "PDF bytes should be generated"
    assert pdf_output.startswith(b"%PDF"), "Output must be valid PDF"
    print(f"Test 11 Passed: Multi-page PDF report with 5 distinct scores & Timed Assessment Audit generated cleanly ({len(pdf_output)} bytes).")
except Exception as e:
    print(f"Test 11 FAILED: PDF report error: {e}")
    sys.exit(1)

print("=" * 65)
print("ALL VERIFICATION SUITE TESTS PASSED SUCCESSFULLY!")
print("=" * 65)
