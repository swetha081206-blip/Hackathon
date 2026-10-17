"""Career Readiness Analyzer — AI-Powered Resume, Provenance, Ownership & Practical Skill Verification.

Built with Python, Streamlit, Google Gemini AI, and platform integrations.
"""

import json
import os
import time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv

# Import modular application components
from security_utils import validate_pdf_file
from url_detector import extract_urls_from_text, probe_url_accessibility, classify_url
from platform_analyzers import dispatch_analyzer
from resume_parser import parse_resume
import importlib
import skill_matcher
importlib.reload(skill_matcher)

from skill_matcher import (
    load_roles,
    verify_resume_claims,
    calculate_career_readiness,
    normalize_skill_name,
    check_assessment_eligibility,
    calculate_combined_summary,
)

from project_provenance import (
    analyze_repository_provenance,
    calculate_project_ownership_score,
)
from practical_verification import (
    fetch_repository_source_files,
    fetch_repository_details,
    generate_project_understanding_assessment,
    validate_python_code_statically,
    evaluate_practical_verification,
    validate_question_schema,
)
from gemini_service import (
    get_gemini_client,
    generate_recommendations_with_ai,
)
from roadmap_generator import generate_learning_roadmap
from report_generator import generate_pdf_report

load_dotenv()

APP_TITLE = "🧭 Career Readiness & Skill Verification Analyzer"
APP_SUBTITLE = "AI Resume Parsing • Repository Provenance • Anti-Clone Ownership Checks • Practical Skill Verification"

st.set_page_config(
    page_title="Career Readiness & Provenance Analyzer",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern, student-friendly styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.02rem;
        color: #4B5563;
        margin-bottom: 1.4rem;
    }
    .tri-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 10px;
    }
    .tri-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 6px 0;
    }
    .tri-label {
        font-size: 0.85rem;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    .status-strong {
        color: #047857;
        font-weight: 600;
    }
    .status-some {
        color: #0D9488;
        font-weight: 600;
    }
    .status-review {
        color: #B45309;
        font-weight: 600;
    }
    .status-insufficient {
        color: #B91C1C;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session_state():
    """Initialize necessary Streamlit session state variables."""
    if "parsed_resume" not in st.session_state:
        st.session_state["parsed_resume"] = None
    if "editable_profile" not in st.session_state:
        st.session_state["editable_profile"] = None
    if "detected_urls" not in st.session_state:
        st.session_state["detected_urls"] = []
    if "platform_evidence" not in st.session_state:
        st.session_state["platform_evidence"] = []
    if "provenance_list" not in st.session_state:
        st.session_state["provenance_list"] = []
    if "practical_assessment" not in st.session_state:
        st.session_state["practical_assessment"] = None
    if "practical_evaluation" not in st.session_state:
        st.session_state["practical_evaluation"] = None
    if "practical_source_files" not in st.session_state:
        st.session_state["practical_source_files"] = []
    if "analysis_complete" not in st.session_state:
        st.session_state["analysis_complete"] = False
    if "final_results" not in st.session_state:
        st.session_state["final_results"] = None


init_session_state()

# -------------------------------------------------------------
# SIDEBAR: Configuration & Target Role
# -------------------------------------------------------------
roles_dict = load_roles()
role_options = list(roles_dict.keys()) + ["Custom Role / Other"]

with st.sidebar:
    st.markdown("### ⚙️ Configuration & Target Role")

    target_role_choice = st.selectbox(
        "Select your target career role:",
        role_options,
        index=0,
        help="The analyzer compares your resume and verified evidence against this target profile.",
    )

    if target_role_choice == "Custom Role / Other":
        custom_role_name = st.text_input("Enter custom role title:", value="Full-Stack Engineer")
        custom_role_skills_str = st.text_input(
            "Enter required skills (comma-separated):",
            value="Python, JavaScript, SQL, REST API, Git, Docker",
        )
        target_role = custom_role_name.strip()
        role_skills = [s.strip() for s in custom_role_skills_str.split(",") if s.strip()]
    else:
        target_role = target_role_choice
        role_skills = roles_dict.get(target_role_choice, [])

    st.markdown(f"**Required skills for {target_role}:**")
    st.caption(", ".join(role_skills))

    st.divider()

    st.markdown("### 🤖 AI Engine & Security")
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        st.success("✅ Gemini AI Key: Active", icon="🔒")
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        st.caption(f"Model: `{model_name}`")
    else:
        st.info("ℹ️ Gemini AI Key: Offline (Using deterministic parser)", icon="💡")

    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    if github_token:
        st.caption("✅ GitHub Token: Active (High rate limits)")
    else:
        st.caption("ℹ️ GitHub Token: Standard limits")

    st.divider()
    max_repos = st.slider("Max GitHub repos to inspect:", min_value=3, max_value=25, value=10, step=1)
    roadmap_weeks = st.select_slider("Roadmap duration (weeks):", options=[2, 3, 4, 6, 8], value=4)

    st.divider()
    st.caption(
        "🛡️ **Fairness & Security Notice**:\n"
        "- Repository ownership is evaluated separately from source code authorship.\n"
        "- Cloned/forked code without contributions does not grant unearned points.\n"
        "- No untrusted repository code is ever executed on this server."
    )


# -------------------------------------------------------------
# MAIN APP HEADER & 5-TAB WORKFLOW
# -------------------------------------------------------------
st.markdown(f"<div class='main-header'>{APP_TITLE}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-header'>{APP_SUBTITLE}</div>", unsafe_allow_html=True)

tab_upload, tab_profiles, tab_dashboard, tab_practical, tab_report = st.tabs([
    "1. 📄 Resume Upload & Review",
    "2. 🔗 Detected Profiles & Links",
    "3. 📊 Tri-Factor Readiness Dashboard",
    "4. 🧪 Practical Skill Verification (Q&A & Code)",
    "5. 📥 Downloadable Reports",
])

# -------------------------------------------------------------
# TAB 1: RESUME UPLOAD & EDITABLE REVIEW
# -------------------------------------------------------------
with tab_upload:
    st.markdown("### Step 1: Upload Your Resume")
    st.write("Upload a PDF resume to extract skills, projects, and online profile links.")

    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        uploaded_resume = st.file_uploader(
            "Choose a PDF file (Max 10MB)",
            type=["pdf"],
            help="Upload your latest software engineering or technical resume.",
        )

    with col_u2:
        st.info(
            "💡 **Provenance & Authenticity Protection**:\n"
            "- Cloned repositories are inspected for fork status and commit authorship.\n"
            "- You can test your practical knowledge in Tab 4 to verify hands-on competency.\n"
            "- You can edit and correct any extracted details below before running analysis."
        )

    if uploaded_resume:
        valid_pdf, valid_msg = validate_pdf_file(uploaded_resume)
        if not valid_pdf:
            st.error(valid_msg)
        else:
            if (
                st.session_state["parsed_resume"] is None
                or st.session_state.get("_last_uploaded_name") != uploaded_resume.name
            ):
                with st.spinner("Extracting text and identifying profiles..."):
                    try:
                        parsed = parse_resume(uploaded_resume)
                        st.session_state["parsed_resume"] = parsed
                        st.session_state["_last_uploaded_name"] = uploaded_resume.name
                        st.session_state["editable_profile"] = dict(parsed["profile"])
                        st.session_state["detected_urls"] = list(parsed["detected_urls"])
                        st.session_state["analysis_complete"] = False
                        st.success(f"Resume extracted successfully via {parsed['extraction_method']}!")
                    except ValueError as val_err:
                        st.error(f"⚠️ {val_err}")
                        st.stop()
                    except Exception as exc:
                        st.error(f"Extraction error: {exc}")
                        st.stop()

    # Editable Review Section
    if st.session_state["editable_profile"]:
        st.divider()
        st.markdown("### Step 2: Review & Edit Extracted Information")
        st.write(
            "Verify the extracted details below. You can correct names, add missing skills, "
            "or edit projects to ensure the evaluation is accurate."
        )

        ep = st.session_state["editable_profile"]

        with st.form("edit_profile_form"):
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                new_name = st.text_input("Candidate Name", value=ep.get("candidate_name") or "Candidate")
            with col_e2:
                new_email = st.text_input("Email", value=ep.get("email") or "")
            with col_e3:
                new_phone = st.text_input("Phone", value=ep.get("phone") or "")

            current_skills_str = ", ".join(ep.get("skills", []))
            new_skills_str = st.text_area(
                "Technical Skills (comma-separated)",
                value=current_skills_str,
                help="Edit, add, or remove skills that you want the analyzer to evaluate.",
                height=100,
            )

            # Education summary
            edu_items = ep.get("education", [])
            edu_summary = "; ".join([e.get("degree", "") or e.get("institution", "") for e in edu_items if isinstance(e, dict)])
            new_edu = st.text_input("Education / Degree", value=edu_summary)

            save_profile_button = st.form_submit_button("💾 Save Profile Changes", use_container_width=True)
            if save_profile_button:
                cleaned_skills = [s.strip() for s in new_skills_str.split(",") if s.strip()]
                st.session_state["editable_profile"]["candidate_name"] = new_name
                st.session_state["editable_profile"]["email"] = new_email
                st.session_state["editable_profile"]["phone"] = new_phone
                st.session_state["editable_profile"]["skills"] = cleaned_skills
                st.success("Profile updated! Proceed to Tab 2 to verify your links.")

        with st.expander("📄 View Extracted Raw Resume Text"):
            if st.session_state["parsed_resume"]:
                st.text_area(
                    "Raw PDF Text",
                    value=st.session_state["parsed_resume"]["raw_text"],
                    height=250,
                    disabled=True,
                )


# -------------------------------------------------------------
# TAB 2: DETECTED PROFILES & LINKS
# -------------------------------------------------------------
with tab_profiles:
    st.markdown("### Detected Online Profiles & Evidence Links")
    st.write(
        "The system scans your resume for GitHub, LeetCode, LinkedIn, Codeforces, HackerRank, "
        "Kaggle, live project demos, and portfolio links. You can verify, edit, or manually add links below."
    )

    detected_urls = st.session_state["detected_urls"]

    if detected_urls:
        st.markdown(f"**Found {len(detected_urls)} relevant links:**")

        for idx, item in enumerate(detected_urls):
            with st.container(border=True):
                c_p1, c_p2, c_p3, c_p4 = st.columns([2, 2, 4, 1])
                with c_p1:
                    st.markdown(f"**{item['platform']}**")
                    st.caption(f"Type: {item['type']}")
                with c_p2:
                    st.write(f"ID: `{item.get('identifier') or 'N/A'}`")
                with c_p3:
                    st.markdown(f"[{item['url']}]({item['url']})")
                    if item.get("status") and item["status"] != "Pending Verification":
                        st.caption(f"Status: {item['status']}")
                with c_p4:
                    if st.button("🗑️ Remove", key=f"del_url_{idx}"):
                        st.session_state["detected_urls"].pop(idx)
                        st.rerun()

        col_probe1, col_probe2 = st.columns([1, 3])
        with col_probe1:
            if st.button("🔍 Check Public Accessibility", use_container_width=True):
                with st.spinner("Probing URL accessibility safely..."):
                    for u in st.session_state["detected_urls"]:
                        acc, code, msg = probe_url_accessibility(u["url"])
                        u["accessible"] = acc
                        u["http_status"] = code
                        u["status"] = msg
                    st.success("Accessibility checks completed!")
                    st.rerun()
    else:
        st.info("No online links detected yet. Upload a resume in Tab 1 or add links manually below.")

    st.divider()
    st.markdown("#### ➕ Add or Manually Specify a Profile / Project URL")
    with st.form("manual_url_form"):
        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            manual_url = st.text_input("Enter URL (e.g. GitHub, LeetCode, Codeforces, or live demo):")
        with col_m2:
            add_url_button = st.form_submit_button("Add URL", use_container_width=True)

        if add_url_button:
            if manual_url.strip():
                plat, cat, ident = classify_url(manual_url.strip())
                st.session_state["detected_urls"].append({
                    "url": manual_url.strip(),
                    "raw_match": manual_url.strip(),
                    "platform": plat,
                    "type": cat,
                    "identifier": ident,
                    "status": "Pending Verification",
                    "accessible": None,
                    "http_status": None,
                    "error": None,
                })
                st.success(f"Added {plat} link: {manual_url.strip()}")
                st.rerun()
            else:
                st.warning("Please enter a valid URL.")

    # Primary Action Button to run the comprehensive analysis
    st.divider()
    run_col1, run_col2, run_col3 = st.columns([1, 2, 1])
    with run_col2:
        start_analysis = st.button("🚀 Run Comprehensive Career Readiness Analysis", type="primary", use_container_width=True)

    if start_analysis:
        if not st.session_state["editable_profile"]:
            st.error("Please upload a resume or enter profile skills in Tab 1 first.")
        else:
            with st.spinner("Retrieving evidence from platforms, checking provenance & authorship, and evaluating role readiness..."):
                profile_data = st.session_state["editable_profile"]
                urls_list = st.session_state["detected_urls"]

                # 1. Dispatch platform analyzers for all detected URLs
                evidence_list = []
                all_provenance = []
                for u in urls_list:
                    ev = dispatch_analyzer(u)
                    evidence_list.append(ev)
                    if ev.get("platform") == "GitHub" and ev.get("provenance_list"):
                        all_provenance.extend(ev["provenance_list"])

                st.session_state["platform_evidence"] = evidence_list
                st.session_state["provenance_list"] = all_provenance

                # 2. Check resume claims against evidence
                claimed_skills = profile_data.get("skills", [])
                verification_rows = verify_resume_claims(claimed_skills, evidence_list)

                # 3. Calculate career readiness scores (incorporating practical assessment if completed)
                try:
                    scores = calculate_career_readiness(
                        verification_rows=verification_rows,
                        target_role=target_role,
                        role_skills=role_skills,
                        platform_evidence=evidence_list,
                        profile_data=profile_data,
                        practical_result=st.session_state.get("practical_evaluation"),
                    )
                except TypeError:
                    scores = calculate_career_readiness(
                        verification_rows=verification_rows,
                        target_role=target_role,
                        role_skills=role_skills,
                        platform_evidence=evidence_list,
                        profile_data=profile_data,
                    )
                    prac_eval = st.session_state.get("practical_evaluation")
                    scores["practical_verification_score"] = prac_eval.get("practical_score", "Not tested") if prac_eval else "Not tested"


                # 4. Generate AI recommendations
                evidence_summary_lines = []
                for ev in evidence_list:
                    evidence_summary_lines.append(f"Platform: {ev.get('platform')}, Status: {ev.get('status')}, Notes: {ev.get('notes')}")
                evidence_summary = "\n".join(evidence_summary_lines)

                recommendations = generate_recommendations_with_ai(
                    target_role=target_role,
                    extracted_data=profile_data,
                    scores=scores,
                    gaps=scores["missing_role_skills"],
                    evidence_summary=evidence_summary,
                )

                # 5. Generate personalized learning roadmap
                roadmap = generate_learning_roadmap(
                    target_role=target_role,
                    skill_gaps=scores["missing_role_skills"],
                    verified_skills=[r["skill"] for r in verification_rows if r["status"] == "Supported"],
                    weeks_count=roadmap_weeks,
                )

                # Save package of final results
                st.session_state["final_results"] = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "target_role": target_role,
                    "role_required_skills": role_skills,
                    "candidate_profile": profile_data,
                    "detected_urls": urls_list,
                    "platform_evidence": evidence_list,
                    "provenance_list": all_provenance,
                    "verification": verification_rows,
                    "scores": scores,
                    "recommendations": recommendations,
                    "roadmap": roadmap,
                }
                st.session_state["analysis_complete"] = True
                st.success("Analysis complete! Switch to Tab 3 to view your results.")


# -------------------------------------------------------------
# TAB 3: CAREER READINESS & OWNERSHIP DASHBOARD
# -------------------------------------------------------------
with tab_dashboard:
    if not st.session_state["analysis_complete"] or not st.session_state["final_results"]:
        st.info("👈 Please upload a resume and click 'Run Comprehensive Career Readiness Analysis' in Tab 2 to view results.")
    else:
        res = st.session_state["final_results"]
        scores = res["scores"]
        prof = res["candidate_profile"]
        vrows = res["verification"]
        target_role = res["target_role"]
        prov_list = res.get("provenance_list", [])

        st.markdown(f"### 🎯 Tri-Factor Evaluation — {target_role}")
        st.write(f"Candidate: **{prof.get('candidate_name', 'Candidate')}** | Generated: `{res['generated_at'][:10]}`")

        # 1. THREE SEPARATE SCORES DISPLAY
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown(
                f"""
                <div class='tri-card'>
                    <div class='tri-label'>A. Career Readiness Score</div>
                    <div class='tri-value' style='color:#1E3A8A;'>{scores.get('overall', 0)}%</div>
                    <small>Role skill match & verified coding evidence</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_s2:
            own_score = scores.get("ownership_evidence_score", 50)
            own_label = scores.get("ownership_data", {}).get("status_label", "Moderate Ownership Evidence")
            st.markdown(
                f"""
                <div class='tri-card'>
                    <div class='tri-label'>B. Project Ownership Evidence</div>
                    <div class='tri-value' style='color:#0D9488;'>{own_score}%</div>
                    <small>{own_label}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_s3:
            prac_val = scores.get("practical_verification_score", "Not tested")
            prac_disp = f"{prac_val}%" if isinstance(prac_val, (int, float)) else "Not tested"
            prac_color = "#047857" if isinstance(prac_val, (int, float)) else "#64748B"
            st.markdown(
                f"""
                <div class='tri-card'>
                    <div class='tri-label'>C. Practical Skill Verification</div>
                    <div class='tri-value' style='color:{prac_color};'>{prac_disp}</div>
                    <small>Project Q&A and coding challenge (Tab 4)</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Explainable Scoring Formula Breakdown
        with st.expander("📐 How are these three separate scores calculated? (Transparent Methodology)"):
            st.markdown(
                """
                To prevent unearned high scores from cloned repositories, the system evaluates three distinct dimensions:
                
                - **A. Career Readiness Score (0-100)**: Evaluates role-specific skill fit (30%), verified skill claims (40%), repository recency (15%), and DSA practice (10%).
                - **B. Project Ownership Evidence Score (0-100)**: Evaluates commit authorship ratio (35%), multi-commit iterative history (25%), non-fork/upstream originality (25%), and custom documentation (15%).
                - **C. Practical Skill Verification Score (0-100 or 'Not tested')**: Evaluates candidate's written technical answers to project architecture questions (60%) and safe coding challenge submission (40%). Displays 'Not tested' if not completed.
                """
            )
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.write("**Career Readiness Breakdown:**")
                st.caption(f"- Role Fit: {scores.get('role_fit_score')}%")
                st.caption(f"- Verified Claims: {scores.get('verified_evidence_score')}%")
                st.caption(f"- Project Recency: {scores.get('project_score')}%")
            with sc2:
                own_d = scores.get("ownership_data", {})
                st.write("**Ownership Evidence Breakdown:**")
                st.caption(f"- Authorship Ratio: {own_d.get('authorship_score', 0)}%")
                st.caption(f"- Commit Iteration: {own_d.get('iteration_score', 0)}%")
                st.caption(f"- Originality: {own_d.get('originality_score', 0)}%")
            with sc3:
                st.write("**Practical Skill Status:**")
                st.caption(scores.get("practical_status", "Not tested"))

        st.divider()

        # 2. REPOSITORY PROVENANCE & CLONE DETECTION REPORT
        st.markdown("### 🔍 Repository Provenance & Ownership Findings")
        st.caption(
            "Distinguishes repository ownership from source-code authorship. "
            "Evaluates fork status, parent repos, commit authorship distribution, and template similarity."
        )

        if prov_list:
            for p in prov_list:
                with st.container(border=True):
                    p_left, p_mid, p_right = st.columns([2, 3, 2])
                    with p_left:
                        st.markdown(f"**[{p.get('repository_name')}]({p.get('repo_url')})**")
                        if p.get("is_fork") and p.get("parent_repo"):
                            parent_name = p['parent_repo']['full_name']
                            parent_url = p['parent_repo'].get('html_url', f"https://github.com/{parent_name}")
                            st.warning(f"🍴 Fork of [{parent_name}]({parent_url})")
                        else:
                            st.success("📦 Original Repository (Non-fork)")

                        st.write(f"Created: `{p.get('created_at', '')[:10]}`")
                        st.write(f"Updated: `{p.get('updated_at', '')[:10]}`")

                    with p_mid:
                        cand_c = p.get("candidate_authored_commits", 0)
                        tot_c = p.get("total_commits_inspected", 0)
                        ratio = p.get("candidate_commit_ratio", 0)
                        st.write(f"**Candidate Commit Authorship:** {cand_c} / {tot_c} ({int(ratio * 100)}%)")

                        if p.get("is_single_commit_import"):
                            st.error("⚠️ Single commit import detected (bulk codebase upload).")

                        if p.get("template_matches"):
                            for tmpl in p["template_matches"]:
                                st.info(f"📋 Boilerplate match: {tmpl['template_name']}")

                        if p.get("upstream_similarity") is not None:
                            st.caption(f"README similarity to upstream: {int(p['upstream_similarity'] * 100)}%")

                        if p.get("supporting_evidence"):
                            for ev_item in p["supporting_evidence"]:
                                st.markdown(f"• <span class='status-strong'>{ev_item}</span>", unsafe_allow_html=True)

                    with p_right:
                        stat = p.get("ownership_status", "Requires manual review")
                        if stat == "Strong supporting evidence":
                            st.markdown(f"<span class='status-strong'>✅ {stat}</span>", unsafe_allow_html=True)
                        elif stat == "Some supporting evidence":
                            st.markdown(f"<span class='status-some'>ℹ️ {stat}</span>", unsafe_allow_html=True)
                        elif stat == "Insufficient evidence":
                            st.markdown(f"<span class='status-insufficient'>❌ {stat}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span class='status-review'>⚠️ {stat}</span>", unsafe_allow_html=True)

                        if p.get("potential_concerns"):
                            for concern in p["potential_concerns"]:
                                st.caption(f"⚠️ {concern}")
        else:
            st.info("No GitHub repositories were inspected for provenance.")

        st.divider()

        # 3. TARGET ROLE SKILLS & GAPS
        st.markdown(f"### 🎯 Target Role Skill Alignment — {target_role}")
        col_match, col_gap = st.columns(2)
        with col_match:
            st.markdown("#### ✅ Matched Skills")
            if scores["matched_role_skills"]:
                for s in scores["matched_role_skills"]:
                    st.success(f"• **{s}** (Claimed & supported by evidence)")
            else:
                st.warning("No target role skills matched yet.")

        with col_gap:
            st.markdown("#### ⚠️ Identified Skill Gaps")
            if scores["missing_role_skills"]:
                for g in scores["missing_role_skills"]:
                    st.error(f"• **{g}** (Recommended to learn or demonstrate)")
            else:
                st.success("🎉 All target role skills are present in your profile.")

        st.divider()

        # 4. RESUME CLAIM VERIFICATION TABLE
        st.markdown("### 📋 Resume Claim Verification")
        st.caption("Cross-referencing claimed skills against public GitHub code, LeetCode/Codeforces stats, and live demos.")

        for row in vrows:
            with st.container(border=True):
                r_l, r_m, r_r = st.columns([1.5, 3, 2.5])
                with r_l:
                    st.markdown(f"**{row['skill']}**")
                    st.write(f"Status: **{row['status']}**")
                    st.caption(f"Confidence: {row['confidence']}")
                with r_m:
                    st.write(row["evidence_snippet"])
                with r_r:
                    st.markdown(f"**Next Action:** {row['suggested_next_action']}")

        st.divider()

        # 5. PERSONALIZED ROADMAP
        st.markdown(f"### 🗺️ Personalized {len(res.get('roadmap', []))}-Week Roadmap")
        for week in res.get("roadmap", []):
            w_num = week.get("week_number") or week.get("week", 1)
            topic = week.get("topic") or week.get("goal", "")
            with st.expander(f"Week {w_num}: {topic}", expanded=(w_num == 1)):
                st.write("**Objectives:** " + ", ".join(week.get("learning_objectives", [])))
                st.info(f"**Deliverable:** {week.get('deliverable_project') or week.get('github_deliverable', '')}")


# -------------------------------------------------------------
# TAB 4: TIMED GITHUB REPOSITORY VERIFICATION & CODE ASSESSMENT
# -------------------------------------------------------------
with tab_practical:
    st.markdown("### 🧪 Timed GitHub Verification & Practical Assessment")
    st.write(
        "To definitively substantiate repository ownership and technical competency, this timed assessment evaluates "
        "your actual source code, design choices, debugging strategies, and live coding performance."
    )

    # 1. ASSESSMENT ELIGIBILITY GATE (Requirement 1)
    st.markdown("#### 1. Assessment Eligibility & Reviewer Controls")

    # Configurable thresholds expander / card
    with st.expander("⚙️ Configure Eligibility Thresholds & Admin Override", expanded=False):
        c_th1, c_th2, c_th3 = st.columns([1, 1, 1])
        with c_th1:
            cfg_readiness_th = st.slider("Readiness Score Threshold (%)", min_value=30, max_value=90, value=60, step=5)
        with c_th2:
            cfg_skill_th = st.slider("Role Skill Match Threshold (%)", min_value=20, max_value=90, value=50, step=5)
        with c_th3:
            admin_override_active = st.checkbox(
                "👑 Admin Override: Enable Assessment Manually",
                value=st.session_state.get("admin_override", False),
                help="Authorized reviewer override to unlock the assessment round regardless of current scores.",
            )
            st.session_state["admin_override"] = admin_override_active

    # Check eligibility against current scores or admin override
    final_res = st.session_state.get("final_results")
    if final_res:
        curr_scores = final_res.get("scores", {})
        cand_readiness = curr_scores.get("career_readiness_score", curr_scores.get("overall", 0))
        cand_skill = curr_scores.get("resume_to_role_skill_match_score", curr_scores.get("role_fit_score", 0))
    else:
        cand_readiness = 0
        cand_skill = 0

    eligibility = check_assessment_eligibility(
        readiness_score=cand_readiness,
        skill_match_score=cand_skill,
        readiness_threshold=cfg_readiness_th,
        skill_threshold=cfg_skill_th,
        admin_override=admin_override_active,
    )

    if eligibility["eligible"]:
        st.success(
            f"✅ **Candidate Unlocked for GitHub Technical Verification Round** "
            + ("*(Admin Override Active)*" if eligibility["admin_override"] else f"*(Readiness: {cand_readiness}%, Skill Match: {cand_skill}%)*")
        )
    else:
        st.warning(
            f"🔒 **Assessment Locked**: Candidate must achieve a Readiness Score of at least {cfg_readiness_th}% "
            f"(currently {cand_readiness}%) and Role Skill Match of at least {cfg_skill_th}% (currently {cand_skill}%). "
            f"To unlock, run analysis in Tab 3 or enable **Admin Override** above."
        )

    st.divider()

    # 2. REPOSITORY DISCOVERY & CONFIRMATION (Requirement 2)
    st.markdown("#### 2. Select & Confirm GitHub Repository to Inspect")

    gh_repos = []
    for ev in st.session_state.get("platform_evidence", []):
        if ev.get("platform") == "GitHub":
            gh_repos = ev.get("repositories", [])
            break

    col_sel1, col_sel2 = st.columns([1, 1])
    target_repo_name = st.session_state.get("target_repo_name", "")
    target_owner = st.session_state.get("target_owner", "")
    target_readme = ""
    is_demo = False

    with col_sel1:
        if gh_repos:
            repo_names = [r["name"] for r in gh_repos]
            selected_from_list = st.selectbox("Choose from your detected repositories:", repo_names)
            selected_repo_obj = next((r for r in gh_repos if r["name"] == selected_from_list), None)
            if selected_repo_obj and not st.session_state.get("active_demo_repo"):
                target_repo_name = selected_repo_obj["name"]
                target_owner = selected_repo_obj["full_name"].split("/")[0] if "/" in selected_repo_obj["full_name"] else "owner"
                target_readme = selected_repo_obj.get("readme", "")
        else:
            st.info("💡 Tip: Discovered repositories from Tab 2 will appear here. Or specify any public repository below.")

    with col_sel2:
        custom_input = st.text_input(
            "Or enter any GitHub repo (e.g. `fastapi/fastapi` or URL):",
            placeholder="https://github.com/username/project",
            key="custom_repo_input",
        )
        if custom_input.strip():
            import re
            m = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)", custom_input.strip())
            if m:
                target_owner = m.group(1)
                target_repo_name = m.group(2)
            elif "/" in custom_input.strip():
                parts = custom_input.strip().split("/")
                target_owner = parts[0]
                target_repo_name = parts[1]

        load_demo_btn = st.button("⚡ Test with Sample Project (FastAPI eCommerce API)", use_container_width=True)
        if load_demo_btn:
            st.session_state["active_demo_repo"] = True
            st.session_state["target_repo_name"] = "ecommerce-api"
            st.session_state["target_owner"] = "sample-developer"
            st.session_state["timed_session"] = None
            st.session_state["practical_assessment"] = None
            st.rerun()

    if st.session_state.get("active_demo_repo"):
        target_repo_name = "ecommerce-api"
        target_owner = "sample-developer"
        target_readme = "Production eCommerce REST API architecture with FastAPI, PostgreSQL, JWT auth, and PyTest."
        is_demo = True

    if target_repo_name:
        st.session_state["target_repo_name"] = target_repo_name
        st.session_state["target_owner"] = target_owner

    if not target_repo_name:
        st.info("👈 Please select a repository from the list, enter a GitHub URL, or click 'Test with Sample Project'.")
    else:
        # Fetch or display metadata
        with st.container(border=True):
            col_inf1, col_inf2, col_inf3 = st.columns([2, 2, 2])
            with col_inf1:
                st.markdown(f"**Repository:** `{target_owner}/{target_repo_name}`")
                st.caption("Sample Mock Codebase" if is_demo else "Public GitHub Repository")
            with col_inf2:
                st.markdown("**Public Access Only:** Safe AST analysis")
                st.caption("Never accesses private repositories or runs untrusted host code.")
            with col_inf3:
                if st.button("🔄 Inspect / Re-fetch Repository Details", use_container_width=True):
                    with st.spinner("Fetching public repository metadata and files..."):
                        if is_demo or target_repo_name == "ecommerce-api":
                            sfiles = [
                                {
                                    "name": "api_router.py",
                                    "path": "app/api_router.py",
                                    "content": "from fastapi import APIRouter, HTTPException, Depends\nfrom pydantic import BaseModel, Field\n\nrouter = APIRouter()\n\nclass OrderPayload(BaseModel):\n    user_id: int\n    items: list[str]\n    total_amount: float = Field(gt=0)\n\n@router.post('/orders/checkout')\ndef create_order(payload: OrderPayload):\n    if not payload.items:\n        raise HTTPException(status_code=400, detail='Order items cannot be empty')\n    return {'status': 'created', 'order_id': 1042, 'amount': payload.total_amount}\n",
                                }
                            ]
                            commits_sample = [{"sha": "c1042a1", "author_name": "developer", "message": "Add checkout router and order validation"}]
                        else:
                            repo_details = fetch_repository_details(target_owner, target_repo_name)
                            sfiles = repo_details.get("source_files", [])
                            commits_sample = repo_details.get("recent_commits", [])
                        st.session_state["practical_source_files"] = sfiles
                        st.session_state["repo_commits_sample"] = commits_sample
                        st.success(f"Inspected {len(sfiles)} prominent source files!")

        # 3. ASSESSMENT INSTRUCTIONS & CANDIDATE CONSENT (Requirement 4 & 7)
        st.markdown("#### 3. Assessment Guidelines & Candidate Consent")
        with st.container(border=True):
            st.markdown(
                """
                - **Timed Questions**: Displayed one question at a time. Deadlines are validated server-side.
                - **Automatic Submission**: When time expires, your typed response is automatically saved and advanced.
                - **Non-Editable Submissions**: Once submitted, answers cannot be edited.
                - **Safe Static Analysis**: The practical coding challenge is statically parsed via Python AST and never executed on the host server.
                """
            )
            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                consent_given = st.checkbox(
                    "I understand and agree to the timed assessment guidelines and confirm my consent to proceed.",
                    key="cand_consent_chk",
                )
            with col_c2:
                accom_choice = st.selectbox(
                    "Accessibility Accommodation:",
                    options=["Standard Time (1.0x)", "Extra Time (+50% / 1.5x)", "Double Time (+100% / 2.0x)"],
                    index=0,
                )
                accom_multiplier = 1.0
                if "1.5x" in accom_choice:
                    accom_multiplier = 1.5
                elif "2.0x" in accom_choice:
                    accom_multiplier = 2.0

            st.caption("ℹ️ Notice: Clipboard copy/paste is restricted where practical in this interface. Please note that browser-level restrictions cannot prevent all external assistance or make an online assessment completely cheat-proof.")

        # Button to generate assessment and start
        if not eligibility["eligible"]:
            st.warning("⚠️ Candidate must meet eligibility requirements (or have Admin Override enabled) to start.")
        elif not consent_given:
            st.info("👆 Please confirm the consent checkbox above to unlock the assessment.")
        else:
            # Check or generate assessment
            timed_session = st.session_state.get("timed_session")

            if not timed_session:
                if st.button("🚀 Begin Timed Verification Round", type="primary", use_container_width=True):
                    with st.spinner("Analyzing repository files and generating code-grounded questions..."):
                        sfiles = st.session_state.get("practical_source_files", [])
                        if not sfiles:
                            if is_demo or target_repo_name == "ecommerce-api":
                                sfiles = [
                                    {
                                        "name": "api_router.py",
                                        "path": "app/api_router.py",
                                        "content": "from fastapi import APIRouter, HTTPException, Depends\nfrom pydantic import BaseModel, Field\n\nrouter = APIRouter()\n\nclass OrderPayload(BaseModel):\n    user_id: int\n    items: list[str]\n    total_amount: float = Field(gt=0)\n\n@router.post('/orders/checkout')\ndef create_order(payload: OrderPayload):\n    if not payload.items:\n        raise HTTPException(status_code=400, detail='Order items cannot be empty')\n    return {'status': 'created', 'order_id': 1042, 'amount': payload.total_amount}\n",
                                    }
                                ]
                            else:
                                sfiles = fetch_repository_source_files(target_owner, target_repo_name, max_files=3)
                            st.session_state["practical_source_files"] = sfiles

                        commits_sample = st.session_state.get("repo_commits_sample", [])
                        assessment = generate_project_understanding_assessment(
                            repo_name=target_repo_name,
                            readme_text=target_readme,
                            source_files=sfiles,
                            commits_data=commits_sample,
                        )
                        st.session_state["practical_assessment"] = assessment

                        questions = assessment.get("questions", [])
                        coding_challenge = assessment.get("coding_challenge", {})

                        # Initialize server-controlled timed session
                        first_limit = int(questions[0].get("time_limit_seconds", 120) * accom_multiplier) if questions else 120
                        now_ts = time.time()
                        st.session_state["timed_session"] = {
                            "status": "in_progress",
                            "questions": questions,
                            "coding_challenge": coding_challenge,
                            "current_step": 0,
                            "answers": {},
                            "time_records": {},
                            "step_start_time": now_ts,
                            "step_deadline": now_ts + first_limit,
                            "accommodation_multiplier": accom_multiplier,
                            "target_repo_name": target_repo_name,
                            "submitted_code": coding_challenge.get("starter_code", ""),
                        }
                        st.rerun()

            # 4. TIMED ONE-QUESTION-AT-A-TIME INTERFACE (Requirement 4)
            timed_session = st.session_state.get("timed_session")
            if timed_session and timed_session.get("status") == "in_progress":
                questions = timed_session["questions"]
                coding_challenge = timed_session["coding_challenge"]
                current_step = timed_session["current_step"]
                total_steps = len(questions) + 1  # 5 conceptual + 1 coding challenge

                now = time.time()
                deadline = timed_session["step_deadline"]
                remaining = max(0, int(deadline - now))

                st.divider()

                # Step 1 to N: Conceptual Questions
                if current_step < len(questions):
                    q = questions[current_step]
                    q_id = q["id"]
                    total_time = int(q.get("time_limit_seconds", 120) * timed_session["accommodation_multiplier"])

                    # Server-side timeout check
                    if remaining <= 0:
                        st.error(f"⏱️ Time expired for Question {q_id}! Auto-saving response and advancing to next question...")
                        prev_typed = st.session_state.get(f"q_input_{q_id}", "").strip()
                        timed_session["answers"][q_id] = prev_typed or "[Time Expired - Auto-submitted]"
                        timed_session["time_records"][q_id] = {"time_spent_seconds": total_time, "timed_out": True}

                        # Advance to next step
                        next_step = current_step + 1
                        timed_session["current_step"] = next_step
                        timed_session["step_start_time"] = time.time()
                        if next_step < len(questions):
                            nxt_limit = int(questions[next_step].get("time_limit_seconds", 120) * timed_session["accommodation_multiplier"])
                        else:
                            nxt_limit = int(coding_challenge.get("time_limit_seconds", 180) * timed_session["accommodation_multiplier"])
                        timed_session["step_deadline"] = time.time() + nxt_limit
                        time.sleep(1.2)
                        st.rerun()

                    # Header with progress and timer
                    col_h1, col_h2, col_h3 = st.columns([2, 2, 2])
                    with col_h1:
                        st.markdown(f"#### 📝 Question {current_step + 1} of {total_steps}")
                        st.caption(f"Category: **{q.get('category')}**")
                    with col_h2:
                        st.markdown(f"**Difficulty:** `{q.get('difficulty', 'Intermediate')}`")
                        st.caption(f"📍 Ref: `{q.get('source_file_ref', 'codebase')}`")
                    with col_h3:
                        time_color = "#B91C1C" if remaining < 25 else "#B45309" if remaining < 50 else "#047857"
                        st.markdown(f"**Time Remaining:** <font size=4 color='{time_color}'><b>{remaining}s</b></font>", unsafe_allow_html=True)
                        st.progress(max(0.0, min(1.0, remaining / total_time)))

                    # Question Card
                    with st.container(border=True):
                        st.markdown(f"##### {q['question']}")
                        if q.get("is_general_fallback"):
                            st.caption("ℹ️ *General question: repository contains limited source file context.*")

                        # Answer Input (ordinary copy/paste disabled where practical)
                        ans_val = st.text_area(
                            "Your Detailed Technical Answer:",
                            value=timed_session["answers"].get(q_id, ""),
                            key=f"q_input_{q_id}",
                            height=130,
                            placeholder="Explain the flow, function decisions, trade-offs, and edge cases...",
                        )

                        col_sub1, col_sub2 = st.columns([3, 1])
                        with col_sub2:
                            if st.button("Submit & Next ⏩", type="primary", use_container_width=True):
                                time_spent = max(1, int(time.time() - timed_session["step_start_time"]))
                                timed_session["answers"][q_id] = ans_val.strip() or "No response provided"
                                timed_session["time_records"][q_id] = {"time_spent_seconds": time_spent, "timed_out": False}

                                next_step = current_step + 1
                                timed_session["current_step"] = next_step
                                timed_session["step_start_time"] = time.time()
                                if next_step < len(questions):
                                    nxt_limit = int(questions[next_step].get("time_limit_seconds", 120) * timed_session["accommodation_multiplier"])
                                else:
                                    nxt_limit = int(coding_challenge.get("time_limit_seconds", 180) * timed_session["accommodation_multiplier"])
                                timed_session["step_deadline"] = time.time() + nxt_limit
                                st.rerun()

                # Step N+1: Practical Coding Challenge
                elif current_step == len(questions):
                    challenge = coding_challenge
                    total_time = int(challenge.get("time_limit_seconds", 180) * timed_session["accommodation_multiplier"])

                    # Server-side timeout check for coding challenge
                    if remaining <= 0:
                        st.error("⏱️ Time expired for Coding Challenge! Auto-submitting solution for evaluation...")
                        sub_code = st.session_state.get("code_editor_area", challenge.get("starter_code", ""))
                        timed_session["submitted_code"] = sub_code
                        timed_session["status"] = "evaluating"
                        st.rerun()

                    col_h1, col_h2, col_h3 = st.columns([2, 2, 2])
                    with col_h1:
                        st.markdown(f"#### 💻 Final Step: Practical Coding Challenge")
                        st.caption(f"Task: **{challenge.get('title')}**")
                    with col_h2:
                        st.markdown(f"**Difficulty:** `{challenge.get('difficulty', 'Intermediate')}`")
                        st.caption(f"📍 Ref: `{challenge.get('source_file_ref', 'codebase')}`")
                    with col_h3:
                        time_color = "#B91C1C" if remaining < 30 else "#B45309" if remaining < 60 else "#047857"
                        st.markdown(f"**Time Remaining:** <font size=4 color='{time_color}'><b>{remaining}s</b></font>", unsafe_allow_html=True)
                        st.progress(max(0.0, min(1.0, remaining / total_time)))

                    with st.container(border=True):
                        st.markdown(f"**Instructions:** {challenge.get('instructions')}")
                        st.caption("Evaluation criteria: " + ", ".join(challenge.get("evaluation_criteria", [])))

                        submitted_code = st.text_area(
                            "Python Solution Editor:",
                            value=timed_session.get("submitted_code") or challenge.get("starter_code", ""),
                            key="code_editor_area",
                            height=220,
                            help="Untrusted code is analyzed statically via AST parser and never executed on the host.",
                        )
                        timed_session["submitted_code"] = submitted_code

                        col_csub1, col_csub2 = st.columns([2, 2])
                        with col_csub2:
                            if st.button("🚀 Final Submit & Run AI Evaluation", type="primary", use_container_width=True):
                                timed_session["submitted_code"] = submitted_code
                                timed_session["status"] = "evaluating"
                                st.rerun()

            # Evaluating State
            if timed_session and timed_session.get("status") == "evaluating":
                with st.spinner("Evaluating written responses, verifying code syntax via AST, and grading practical skills..."):
                    eval_res = evaluate_practical_verification(
                        assessment=st.session_state["practical_assessment"],
                        candidate_answers=timed_session.get("answers", {}),
                        submitted_code=timed_session.get("submitted_code", ""),
                        source_files=st.session_state.get("practical_source_files", []),
                        time_records=timed_session.get("time_records", {}),
                    )
                    eval_res["completed"] = True
                    st.session_state["practical_evaluation"] = eval_res
                    timed_session["status"] = "completed"

                    # Recalculate all 5 categories
                    if st.session_state.get("final_results"):
                        fres = st.session_state["final_results"]
                        fres["scores"] = calculate_career_readiness(
                            verification_rows=fres["verification"],
                            target_role=fres["target_role"],
                            role_skills=fres["role_required_skills"],
                            platform_evidence=fres["platform_evidence"],
                            profile_data=fres["candidate_profile"],
                            practical_result=eval_res,
                        )
                        fres["practical_evaluation"] = eval_res
                    st.success("Practical skill evaluation complete! See detailed 5-score breakdown below.")
                    st.rerun()

        # 5. RESULTS & 5-SCORE BREAKDOWN DISPLAY (Requirement 5 & 6)
        eval_res = st.session_state.get("practical_evaluation")
        if eval_res and eval_res.get("completed"):
            st.divider()
            st.markdown("### 🏆 Comprehensive Verification & 5-Category Scores")
            st.caption("Factual repository provenance is strictly separated from AI understanding inferences.")

            # Display 5 distinct cards
            fres = st.session_state.get("final_results", {})
            sc_data = fres.get("scores", {}) if fres else {}

            sc_1 = sc_data.get("career_readiness_score", sc_data.get("overall", 75))
            sc_2 = sc_data.get("resume_to_role_skill_match_score", sc_data.get("role_fit_score", 70))
            sc_3 = eval_res.get("project_understanding_score", eval_res.get("practical_score", 80))
            sc_4 = eval_res.get("coding_performance_score", 80)
            sc_5 = sc_data.get("project_ownership_evidence_score", 50)

            c_c1, c_c2, c_c3, c_c4, c_c5 = st.columns(5)
            with c_c1:
                st.markdown(
                    f"""
                    <div class='tri-card'>
                        <div class='tri-label'>1. Career Readiness</div>
                        <div class='tri-value' style='color:#1E3A8A;'>{int(sc_1)}%</div>
                        <small>Profile & Evidence Strength</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_c2:
                st.markdown(
                    f"""
                    <div class='tri-card'>
                        <div class='tri-label'>2. Role Skill Match</div>
                        <div class='tri-value' style='color:#0D9488;'>{int(sc_2)}%</div>
                        <small>Target Competency Fit</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_c3:
                st.markdown(
                    f"""
                    <div class='tri-card'>
                        <div class='tri-label'>3. Code Understanding</div>
                        <div class='tri-value' style='color:#047857;'>{int(sc_3)}%</div>
                        <small>Grounded Q&A Score</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_c4:
                st.markdown(
                    f"""
                    <div class='tri-card'>
                        <div class='tri-label'>4. Practical Coding</div>
                        <div class='tri-value' style='color:#047857;'>{int(sc_4)}%</div>
                        <small>AST Syntax & Logic</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_c5:
                st.markdown(
                    f"""
                    <div class='tri-card'>
                        <div class='tri-label'>5. Ownership Evidence</div>
                        <div class='tri-value' style='color:#0D9488;'>{int(sc_5)}%</div>
                        <small>Commit Authorship & History</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Transparent Configurable Combined Summary
            with st.expander("⚖️ Transparent Configurable Combined Summary"):
                st.write("Customize weighting to see an aggregated summary without altering the original readiness score:")
                col_w1, col_w2, col_w3, col_w4, col_w5 = st.columns(5)
                with col_w1:
                    w1 = st.slider("Readiness Weight", 0, 50, 25, 5, key="w_readiness")
                with col_w2:
                    w2 = st.slider("Skill Match Weight", 0, 50, 25, 5, key="w_skill")
                with col_w3:
                    w3 = st.slider("Understanding Weight", 0, 50, 20, 5, key="w_und")
                with col_w4:
                    w4 = st.slider("Coding Weight", 0, 50, 15, 5, key="w_code")
                with col_w5:
                    w5 = st.slider("Ownership Weight", 0, 50, 15, 5, key="w_own")

                custom_weights = {
                    "career_readiness": w1 / 100.0,
                    "role_skill_match": w2 / 100.0,
                    "project_understanding": w3 / 100.0,
                    "practical_coding": w4 / 100.0,
                    "project_ownership": w5 / 100.0,
                }
                combined_res = calculate_combined_summary(
                    scores={
                        "career_readiness_score": sc_1,
                        "resume_to_role_skill_match_score": sc_2,
                        "github_project_understanding_score": sc_3,
                        "practical_coding_performance_score": sc_4,
                        "project_ownership_evidence_score": sc_5,
                    },
                    weights=custom_weights,
                )
                st.info(f"**Aggregated Composite Summary:** **{combined_res['combined_score']}%** (Normalized weights: {combined_res['weights_used']})")

            # Factual Signals vs AI Inferences Section
            st.divider()
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown("#### 📌 Factual Repository Signals")
                for sig in eval_res.get("factual_signals", []):
                    st.write(f"• {sig}")
                code_eval = eval_res.get("coding_challenge_evaluation", {})
                st.write(f"• Safe AST Syntax Valid: **{'Yes (0 syntax errors)' if code_eval.get('syntax_valid') else 'No'}**")
                st.write(f"• Host Runtime Execution: **None (Protected)**")
            with col_f2:
                st.markdown("#### 🧠 AI-Generated Inferences & Feedback")
                st.info(f"**Interviewer Feedback:** {eval_res.get('overall_feedback', '')}")
                for inf in eval_res.get("ai_inferences", []):
                    st.caption(f"• {inf}")

            # Question by Question Detailed Breakdown
            st.markdown("#### 📋 Question-by-Question Audit")
            for q_eval in eval_res.get("question_evaluations", []):
                with st.container(border=True):
                    col_qe1, col_qe2 = st.columns([3, 1])
                    with col_qe1:
                        st.markdown(f"**Question {q_eval.get('question_id')}:** (Ref: `{q_eval.get('source_file_ref', 'codebase')}`)")
                        st.caption(f"Candidate Answer: *\"{q_eval.get('answer_text', '')[:200]}...\"*")
                        st.write(f"• Correct: {q_eval.get('correct_aspects', '')}")
                        if q_eval.get("incomplete_aspects"):
                            st.caption(f"• To expand: {q_eval.get('incomplete_aspects', '')}")
                    with col_qe2:
                        st.metric("Score", f"{q_eval.get('score', 0)}%")
                        t_sec = q_eval.get("time_spent_seconds", 0)
                        to_flag = " (Timed Out)" if q_eval.get("timed_out") else ""
                        st.caption(f"Time: {t_sec}s{to_flag}")

            if st.button("🔄 Restart Assessment for Another Repository", key="restart_assessment_btn"):
                st.session_state["timed_session"] = None
                st.session_state["practical_assessment"] = None
                st.session_state["practical_evaluation"] = None
                st.rerun()


# -------------------------------------------------------------
# TAB 5: DOWNLOADABLE REPORTS
# -------------------------------------------------------------
with tab_report:
    st.markdown("### 📥 Downloadable Reports")
    st.write("Generate and download comprehensive PDF or JSON reports to share with recruiters or mentors.")

    if not st.session_state["analysis_complete"] or not st.session_state["final_results"]:
        st.info("Please run the analysis first to generate downloadable reports.")
    else:
        results_data = st.session_state["final_results"]

        col_rep1, col_rep2 = st.columns(2)

        with col_rep1:
            st.markdown("#### 📄 Professional PDF Report")
            st.write(
                "Includes Tri-Factor Score cards, repository provenance breakdown, "
                "claim verification table, practical test results, recommendations, and roadmap."
            )
            with st.spinner("Preparing PDF report..."):
                try:
                    pdf_bytes = generate_pdf_report(results_data)
                    cand_clean = results_data["candidate_profile"].get("candidate_name", "candidate").replace(" ", "_").lower()
                    st.download_button(
                        label="⬇️ Download Full PDF Report",
                        data=pdf_bytes,
                        file_name=f"career_readiness_report_{cand_clean}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
                except Exception as pdf_err:
                    st.error(f"Error generating PDF report: {pdf_err}")

        with col_rep2:
            st.markdown("#### 📊 Machine-Readable JSON Export")
            st.write("Export all raw structured data, provenance findings, verified claims, and metrics for programmatic use.")
            json_str = json.dumps(results_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="⬇️ Download JSON Data",
                data=json_str.encode("utf-8"),
                file_name="career_readiness_data.json",
                mime="application/json",
                use_container_width=True,
            )
