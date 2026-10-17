"""Professional PDF Report generation using ReportLab.
"""

from io import BytesIO
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)


class NumberedCanvas:
    """Canvas that adds page numbers in a two-pass layout."""
    def __init__(self, *args, **kwargs):
        pass


def generate_pdf_report(analysis_result: dict) -> bytes:
    """Generate a clean, multi-page professional PDF report from the analysis results."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    primary_color = colors.HexColor("#1E3A8A")  # Navy / Slate
    accent_color = colors.HexColor("#0D9488")   # Teal
    text_dark = colors.HexColor("#1F2937")      # Dark gray

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=12,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark,
    )
    body_bold = ParagraphStyle(
        "DocBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=text_dark,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=primary_color,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#6B7280"),
    )

    story = []

    profile = analysis_result.get("candidate_profile", {})
    scores = analysis_result.get("scores", {})
    target_role = analysis_result.get("target_role", "Software Engineer")
    cand_name = profile.get("candidate_name") or "Candidate"
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")

    # Document Header
    story.append(Paragraph("Career Readiness, Project Ownership & Skill Verification Report", title_style))
    story.append(
        Paragraph(
            f"<b>Candidate:</b> {cand_name} &nbsp;|&nbsp; <b>Target Role:</b> {target_role} &nbsp;|&nbsp; <b>Generated:</b> {now_str}",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=10))

    # Executive Summary / Five Distinct Score Categories (Requirement 6)
    story.append(Paragraph("1. Assessment Scores & Verification Breakdown (5 Distinct Categories)", section_heading))

    s_cr = scores.get("career_readiness_score", scores.get("overall", 0))
    s_sm = scores.get("resume_to_role_skill_match_score", scores.get("role_fit_score", 0))
    s_pu = scores.get("github_project_understanding_score", "Not tested")
    s_pc = scores.get("practical_coding_performance_score", "Not tested")
    s_own = scores.get("project_ownership_evidence_score", scores.get("ownership_evidence_score", 50))

    pu_str = f"{int(s_pu)}%" if isinstance(s_pu, (int, float)) else str(s_pu)
    pc_str = f"{int(s_pc)}%" if isinstance(s_pc, (int, float)) else str(s_pc)

    five_score_data = [
        [
            Paragraph("<b>Assessment Category</b>", table_cell_bold),
            Paragraph("<b>Score</b>", table_cell_bold),
            Paragraph("<b>Evaluation Methodology & Evidence Base</b>", table_cell_bold),
        ],
        [
            Paragraph("<b>1. Career Readiness Score</b>", table_cell),
            Paragraph(f"<b><font size=11 color='#1E3A8A'>{int(s_cr)}%</font></b>", table_cell),
            Paragraph("Verified skill claims (40%), target role fit (30%), project recency (15%), and DSA practice (10%).", table_cell),
        ],
        [
            Paragraph("<b>2. Resume-to-Role Skill Match</b>", table_cell),
            Paragraph(f"<b><font size=11 color='#0D9488'>{int(s_sm)}%</font></b>", table_cell),
            Paragraph(f"Percentage of technical requirements for '{target_role}' matched from resume and verified claims.", table_cell),
        ],
        [
            Paragraph("<b>3. GitHub Project Understanding</b>", table_cell),
            Paragraph(f"<b><font size=11 color='#047857'>{pu_str}</font></b>", table_cell),
            Paragraph("Timed written explanations of codebase architecture, algorithms, debugging, and commits.", table_cell),
        ],
        [
            Paragraph("<b>4. Practical Coding Performance</b>", table_cell),
            Paragraph(f"<b><font size=11 color='#047857'>{pc_str}</font></b>", table_cell),
            Paragraph("Live coding challenge correctness, static AST syntax safety, defensive validation, and edge case coverage.", table_cell),
        ],
        [
            Paragraph("<b>5. Project Ownership Evidence</b>", table_cell),
            Paragraph(f"<b><font size=11 color='#0D9488'>{int(s_own)}%</font></b>", table_cell),
            Paragraph("Commit authorship ratio, repository history iteration, non-fork originality, and custom documentation.", table_cell),
        ],
    ]
    five_score_table = Table(five_score_data, colWidths=[165, 65, 310])
    five_score_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(five_score_table)
    story.append(Spacer(1, 8))

    # Project Ownership Provenance Section
    story.append(Paragraph("2. Repository Provenance & Ownership Findings", section_heading))
    provenance_list = analysis_result.get("provenance_list", [])
    if not provenance_list:
        # Check platform_evidence for provenance
        for ev in analysis_result.get("platform_evidence", []):
            if ev.get("platform") == "GitHub" and ev.get("provenance_list"):
                provenance_list = ev["provenance_list"]
                break

    if provenance_list:
        prov_table_data = [
            [
                Paragraph("<b>Repository</b>", table_cell_bold),
                Paragraph("<b>Fork / Upstream</b>", table_cell_bold),
                Paragraph("<b>Candidate Commits</b>", table_cell_bold),
                Paragraph("<b>Ownership Status</b>", table_cell_bold),
            ]
        ]
        for p in provenance_list[:6]:
            fork_str = f"Fork of {p['parent_repo']['full_name'][:20]}" if p.get("is_fork") and p.get("parent_repo") else "Original (Non-fork)"
            cand_c = p.get("candidate_authored_commits", 0)
            tot_c = p.get("total_commits_inspected", 0)
            commit_str = f"{cand_c}/{tot_c} ({int(p.get('candidate_commit_ratio', 0) * 100)}%)"

            stat = p.get("ownership_status", "Requires manual review")
            if stat == "Strong supporting evidence":
                stat_col = "#047857"
            elif stat == "Some supporting evidence":
                stat_col = "#0D9488"
            elif stat == "Insufficient evidence":
                stat_col = "#B91C1C"
            else:
                stat_col = "#B45309"

            prov_table_data.append([
                Paragraph(f"<b>{p.get('repository_name', 'Repo')}</b>", table_cell),
                Paragraph(fork_str, table_cell),
                Paragraph(commit_str, table_cell),
                Paragraph(f"<b><font color='{stat_col}'>{stat}</font></b>", table_cell),
            ])

        prov_table = Table(prov_table_data, colWidths=[140, 140, 110, 150])
        prov_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(prov_table)
    else:
        story.append(Paragraph("No public GitHub repositories were accessible for detailed provenance analysis.", body_style))
    story.append(Spacer(1, 8))

    # Target Role Alignment & Gaps
    story.append(Paragraph("3. Target Role Skill Alignment", section_heading))
    matched_skills = scores.get("matched_role_skills", [])
    missing_skills = scores.get("missing_role_skills", [])

    matched_text = ", ".join(matched_skills) if matched_skills else "None explicitly detected"
    missing_text = ", ".join(missing_skills) if missing_skills else "None - all target role skills claimed!"

    story.append(Paragraph(f"<b>Skills Matching '{target_role}':</b> {matched_text}", body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Key Skill Gaps to Bridge:</b> <font color='#B91C1C'>{missing_text}</font>", body_style))
    story.append(Spacer(1, 10))

    # Detected Platforms and Online Profiles
    story.append(Paragraph("4. Detected Online Profiles & Evidence Sources", section_heading))
    detected_urls = analysis_result.get("detected_urls", [])
    if detected_urls:

        url_table_data = [
            [
                Paragraph("<b>Platform</b>", table_cell_bold),
                Paragraph("<b>Type / Category</b>", table_cell_bold),
                Paragraph("<b>URL</b>", table_cell_bold),
                Paragraph("<b>Status</b>", table_cell_bold),
            ]
        ]
        for u in detected_urls[:10]:
            url_str = u.get("url", "")
            short_url = url_str if len(url_str) <= 45 else url_str[:42] + "..."
            status_text = u.get("status", "Checked")
            url_table_data.append([
                Paragraph(u.get("platform", "Web"), table_cell),
                Paragraph(u.get("type", "General"), table_cell),
                Paragraph(f"<a href='{url_str}'>{short_url}</a>", table_cell),
                Paragraph(status_text, table_cell),
            ])
        url_table = Table(url_table_data, colWidths=[90, 110, 240, 100])
        url_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(url_table)
    else:
        story.append(Paragraph("No online profile URLs were detected in the resume text.", body_style))
    story.append(Spacer(1, 10))

    # Resume Claims vs. Online Evidence Verification Table
    story.append(Paragraph("4. Resume Claim Verification Table", section_heading))
    story.append(
        Paragraph(
            "Each claimed skill is evaluated against accessible public GitHub code, LeetCode/Codeforces stats, and live demo artifacts.",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    verif_rows = analysis_result.get("verification", [])
    if verif_rows:
        vtable_data = [
            [
                Paragraph("<b>Skill Claim</b>", table_cell_bold),
                Paragraph("<b>Status</b>", table_cell_bold),
                Paragraph("<b>Confidence</b>", table_cell_bold),
                Paragraph("<b>Supporting Evidence & Source</b>", table_cell_bold),
                Paragraph("<b>Recommended Action</b>", table_cell_bold),
            ]
        ]
        for row in verif_rows[:15]:
            status_val = row.get("status", "Not Verified")
            if status_val == "Supported":
                status_color = "#047857"
            elif status_val == "Partially Supported":
                status_color = "#B45309"
            elif status_val == "Unable to Check":
                status_color = "#6D28D9"
            else:
                status_color = "#4B5563"

            vtable_data.append([
                Paragraph(f"<b>{row.get('skill', '')}</b>", table_cell),
                Paragraph(f"<b><font color='{status_color}'>{status_val}</font></b>", table_cell),
                Paragraph(row.get("confidence", "Medium"), table_cell),
                Paragraph(row.get("evidence_snippet", "")[:120], table_cell),
                Paragraph(row.get("suggested_next_action", "")[:100], table_cell),
            ])

        v_table = Table(vtable_data, colWidths=[95, 75, 55, 185, 130])
        v_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(v_table)
    story.append(Spacer(1, 10))

    # 5. Timed Technical Assessment & Practical Verification
    practical_eval = analysis_result.get("practical_evaluation") or analysis_result.get("practical_result")
    if practical_eval and practical_eval.get("completed"):
        story.append(Paragraph("5. Timed Practical Skill Verification & Code Safety Audit", section_heading))
        story.append(Paragraph(
            f"<b>Assessment Status:</b> {practical_eval.get('status_summary', 'Completed')} &nbsp;|&nbsp; "
            f"<b>Project Understanding:</b> {practical_eval.get('project_understanding_score', 0)}% &nbsp;|&nbsp; "
            f"<b>Coding Performance:</b> {practical_eval.get('coding_performance_score', 0)}%",
            body_style,
        ))
        story.append(Spacer(1, 4))

        # Coding challenge evaluation
        code_eval = practical_eval.get("coding_challenge_evaluation", {})
        syn_ok = "Passed (Valid Python AST)" if code_eval.get("syntax_valid") else "Syntax Error"
        story.append(Paragraph(
            f"<b>Safe AST Static Syntax Validation:</b> <font color='{'#047857' if code_eval.get('syntax_valid') else '#B91C1C'}'>{syn_ok}</font> &nbsp;|&nbsp; "
            f"<b>Code Logic Score:</b> {code_eval.get('logic_score', 0)}% &nbsp;|&nbsp; "
            f"<b>Runtime Execution on Host:</b> <i>None (Protected against untrusted execution)</i>",
            body_style,
        ))
        story.append(Spacer(1, 6))

        # Question responses table
        q_evals = practical_eval.get("question_evaluations", [])
        if q_evals:
            q_table_data = [
                [
                    Paragraph("<b>Q#</b>", table_cell_bold),
                    Paragraph("<b>Source File Ref</b>", table_cell_bold),
                    Paragraph("<b>Time Used</b>", table_cell_bold),
                    Paragraph("<b>Score</b>", table_cell_bold),
                    Paragraph("<b>Candidate Key Observations</b>", table_cell_bold),
                ]
            ]
            for qe in q_evals:
                t_str = f"{qe.get('time_spent_seconds', 0)}s" + (" (Timeout)" if qe.get("timed_out") else "")
                q_table_data.append([
                    Paragraph(f"Q{qe.get('question_id', '')}", table_cell),
                    Paragraph(qe.get("source_file_ref", "codebase")[:25], table_cell),
                    Paragraph(t_str, table_cell),
                    Paragraph(f"<b>{qe.get('score', 0)}%</b>", table_cell),
                    Paragraph(qe.get("correct_aspects", "Evaluated")[:140], table_cell),
                ])
            q_table = Table(q_table_data, colWidths=[35, 125, 75, 45, 260])
            q_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ])
            )
            story.append(q_table)
            story.append(Spacer(1, 6))

        # Factual Signals vs AI Inferences
        if practical_eval.get("factual_signals"):
            f_text = " • ".join(practical_eval["factual_signals"][:3])
            story.append(Paragraph(f"<b>Factual Signals:</b> {f_text}", body_style))
            story.append(Spacer(1, 3))
        if practical_eval.get("ai_inferences"):
            ai_text = " • ".join(practical_eval["ai_inferences"][:2])
            story.append(Paragraph(f"<b>AI Inferences:</b> <i>{ai_text}</i>", body_style))
            story.append(Spacer(1, 8))

    # Actionable AI Recommendations
    recs = analysis_result.get("recommendations", {})
    if recs:
        story.append(Paragraph("6. Career Recommendations & Project Ideas", section_heading))
        if recs.get("executive_summary"):
            story.append(Paragraph(f"<b>Coach Summary:</b> {recs['executive_summary']}", body_style))
            story.append(Spacer(1, 6))

        proj_list = recs.get("recommended_projects", [])
        if proj_list:
            for p in proj_list[:2]:
                title = p.get("title", "Recommended Project")
                desc = p.get("description", "")
                techs = ", ".join(p.get("technologies", []))
                story.append(Paragraph(f"• <b>{title}</b> ({techs}): {desc}", body_style))
            story.append(Spacer(1, 6))

    # Personalized Learning Roadmap
    roadmap = analysis_result.get("roadmap", [])
    if roadmap:
        story.append(Paragraph("7. Personalized 4-Week Learning Roadmap", section_heading))
        for item in roadmap:
            w_num = item.get("week_number") or item.get("week", "Week")
            topic = item.get("topic") or item.get("goal", "")
            deliverable = item.get("deliverable_project") or item.get("github_deliverable", "")
            story.append(Paragraph(f"<b>Week {w_num}: {topic}</b>", body_bold))
            story.append(Paragraph(f"<i>Deliverable:</i> {deliverable}", body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    # Limitations & Legal / Ethical Disclaimer
    story.append(Paragraph("8. Methodology & Limitations Notice", section_heading))
    disclaimer_text = (
        "<b>Notice:</b> This analysis evaluates publicly accessible online code repositories, platform profiles, "
        "and portfolio demonstrations at the time of report generation. A status of 'Not Verified' or an inaccessible "
        "profile does NOT imply that a candidate lacks skill or has misrepresented their qualifications. "
        "This tool is designed for educational guidance, self-assessment, and portfolio improvement, and does not "
        "constitute an official hiring assessment or employment guarantee."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
