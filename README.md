# AI-Powered Resume, GitHub Provenance, Skill Verification & Career Readiness Analyzer

An intelligent, secure, and explainable career readiness analyzer and verification dashboard built with Python, Streamlit, Google Gemini AI, and platform integrations.

---

## 🌟 Key Features

### 1. Intelligent Resume Parsing & Review
- Safe PDF text extraction via `pypdf` with strict validation against corrupted files and 10MB upload limits.
- Immediate detection and alerts for scanned or image-only PDFs that require OCR.
- Dual-mode extraction: high-precision structured entity extraction via Google Gemini AI with deterministic regex & keyword fallbacks.
- **Interactive Editable Review**: Allows students to inspect and correct extracted candidate names, contact details, technical skills, and education before running the evaluation.

### 2. Cross-Resume URL Detection & Platform Identification
- Automatic extraction and cross-line reconstruction for broken URLs in PDF text.
- Normalization, deduplication, and removal of tracking parameters (`utm_*`).
- Categorizes and verifies URLs across platforms:
  - **GitHub** (Profiles & Repositories)
  - **LeetCode** (Public profiles & problem statistics)
  - **LinkedIn** (Profile validation with privacy-safe manual input support)
  - **Codeforces** (Handles, official ratings, and problem tags)
  - **HackerRank** (Profiles & skill badges)
  - **CodeChef** & **GeeksforGeeks** (Profiles, ratings, problem statistics)
  - **Kaggle** (Profiles, notebooks, datasets)
  - **Personal Portfolios & Live Project Demos** (Vercel, Netlify, Render, Streamlit, HuggingFace)
  - **Certification Links** (Credly, Coursera, Udemy, research publications)
- Interactive link management: edit, delete, or manually add links.

### 3. Repository Provenance & Anti-Clone Verification
- **Fork Tracking & Upstream Analysis**: Inspects whether repositories are forks, identifies parent/source repositories, and compares README and code similarity against upstream code.
- **Commit History & Authorship Distribution**: Computes the exact ratio of commits authored by the candidate versus external contributors.
- **Single-Commit Import Detection**: Flags repositories containing only a single bulk import commit ("Initial commit") typical of copied code.
- **Boilerplate & Template Detection**: Detects common unmodified starters (Create React App, Vite, Next.js, Django starter, FreeCodeCamp exercises).
- **Four Clear Ownership Statuses**:
  - `Strong supporting evidence`
  - `Some supporting evidence`
  - `Insufficient evidence`
  - `Requires manual review`
- **Fairness Guarantee**: Clearly distinguishes repository ownership from code authorship; does not falsely label candidates as dishonest based solely on fork status or templates.

### 4. Gemini-Based Project Understanding & Safe Practical Verification
- **Grounding in Real Source Files**: Automatically fetches and inspects key source files (e.g. `main.py`, `app.py`, `index.js`) from the candidate's public repositories.
- **Technical Understanding Questions**: Generates 3 deep architectural, algorithmic, and debugging questions tailored to the candidate's actual code.
- **Practical Coding Challenge**: Provides a project-specific coding challenge with starter code and clear criteria.
- **Safe Evaluation (Zero Code Execution on Server)**: Uses AST static analysis to verify syntax and strictly reject unsafe constructs (`os.system`, `subprocess`, `eval`), evaluating logic and style via Gemini AI without executing untrusted code on the host server.

### 5. Tri-Factor Separate Scoring System
The system maintains **three distinct, transparent scores** so that a cloned repository cannot falsely inflate a candidate's evaluation:

1. **A. Career Readiness Score (0-100)**: Evaluates role-specific skill fit (30%), verified skill claims (40%), repository recency (15%), and DSA practice (10%).
2. **B. Project Ownership Evidence Score (0-100)**: Evaluates commit authorship ratio (35%), multi-commit iterative history (25%), non-fork/upstream originality (25%), and custom documentation (15%).
3. **C. Practical Skill Verification Score (0-100 or 'Not tested')**: Evaluates written technical answers to project questions (60%) and safe coding challenge quality (40%). Displays **"Not tested"** if the candidate has not completed the practical assessment.

### 6. Actionable AI Career Coaching & Personalized Roadmap
- Grounded resume bullet point improvements using the STAR method (Situation, Task, Action, Result).
- Tailored project ideas designed specifically to bridge identified skill gaps.
- Custom 4-week step-by-step learning roadmap with objectives, tasks, deliverables, and free learning resources.

### 7. Downloadable Multi-Page PDF & JSON Reports
- Generates clean, professional PDF reports via ReportLab with Tri-Factor score cards, repository provenance tables, claim verification tables, practical assessment feedback, and disclaimers.
- Downloadable machine-readable JSON export.

### 8. Strict Security & SSRF Protection
- Defense against Server-Side Request Forgery (SSRF) blocking localhost, internal IP ranges (`10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`), loopbacks, and cloud metadata endpoints (`169.254.169.254`).
- Revalidates redirect hops before following.
- API keys are read strictly from `.env` and are never exposed in UI, logs, reports, or source code.

---

## 📁 Project Architecture

- [app.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/app.py) — Streamlit entry point with modern 5-tab workflow.
- [project_provenance.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/project_provenance.py) — Fork tracking, commit authorship analysis, template signature detection, and Project Ownership Evidence scoring.
- [practical_verification.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/practical_verification.py) — Source file inspection, Gemini-grounded technical Q&A, AST static code safety validation, and practical evaluation.
- [security_utils.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/security_utils.py) — SSRF protection, safe URL validation, timeout controls, and PDF validation.
- [url_detector.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/url_detector.py) — Cross-line URL recovery, normalization, and platform categorization.
- [platform_analyzers.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/platform_analyzers.py) — Modular analyzers for GitHub, LeetCode, Codeforces, HackerRank, CodeChef, and web projects.
- [resume_parser.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/resume_parser.py) — PDF extraction, empty/scanned document detection, and dual AI/rule extraction.
- [skill_matcher.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/skill_matcher.py) — Skill canonical aliases, claim verification, and Tri-Factor scoring.
- [gemini_service.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/gemini_service.py) — Google GenAI integration with multi-model fallback and structured output handling.
- [roadmap_generator.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/roadmap_generator.py) — Personalized learning roadmap generator.
- [report_generator.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/report_generator.py) — Multi-page PDF report generation with ReportLab.
- [roles.json](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/roles.json) — Configurable target role definitions.
- [test_suite.py](file:///c:/Users/thsni/OneDrive/Desktop/career_readiness_analyzer_gemini/career_readiness_analyzer/test_suite.py) — Automated test suite verifying all 12 functional, provenance, safety, and scoring requirements.

---

## 🚀 Getting Started

### 1. Environment Setup

The application runs using the project's virtual environment:

```powershell
cd C:\Users\thsni\OneDrive\Desktop\career_readiness_analyzer_gemini\career_readiness_analyzer
..\.venv\Scripts\Activate.ps1
```

### 2. Configuration (`.env`)

The application loads configuration automatically from `.env`:
```text
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
GITHUB_TOKEN=your_optional_github_token_here
```

### 3. Running the Application

Launch the Streamlit web dashboard:
```powershell
python -m streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 4. Running the Automated Test Suite

Run the full verification suite to test all components:
```powershell
python test_suite.py
```

---

## ⚖️ Ethical & Educational Notice

This tool evaluates publicly accessible online evidence at the time of analysis. A status of **Not Verified** or an inaccessible platform profile does **not** indicate that a student lacks the skill or has misrepresented their qualifications. It is intended as an educational diagnostic and portfolio improvement guide, not an official employment assessment.
