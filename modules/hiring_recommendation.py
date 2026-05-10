def generate_hiring_recommendation(
    interview_score,
    resume_score,
    nlp_level="Moderate",
    star_score=50
):
    # =========================
    # Overall Score
    # =========================
    overall_score = round(
        interview_score * 0.6 + resume_score * 0.4,
        2
    )

    # =========================
    # Competency Evaluation
    # =========================
    competencies = []
    concerns = []

    # Interview Performance
    if interview_score >= 80:
        competencies.append("Strong interview communication and confidence.")
    elif interview_score >= 65:
        competencies.append("Good overall interview performance.")
    else:
        concerns.append("Interview communication needs improvement.")

    # Resume Alignment
    if resume_score >= 80:
        competencies.append("Resume shows strong alignment with job requirements.")
    elif resume_score >= 60:
        competencies.append("Resume demonstrates moderate role alignment.")
    else:
        concerns.append("Resume alignment with job description is limited.")

    # NLP Communication
    if nlp_level == "Excellent":
        competencies.append("Communication clarity and response quality were excellent.")
    elif nlp_level == "Good":
        competencies.append("Candidate demonstrated good communication structure.")
    else:
        concerns.append("Communication quality can be improved further.")

    # STAR Analysis
    if star_score >= 75:
        competencies.append("Candidate used strong STAR-based behavioral responses.")
    elif star_score >= 50:
        competencies.append("Behavioral response structure was moderately effective.")
    else:
        concerns.append("Behavioral interview structure was weak.")

    # =========================
    # Final Recommendation
    # =========================
    if overall_score >= 80:
        recommendation = "Highly Recommended"
    elif overall_score >= 65:
        recommendation = "Recommended"
    elif overall_score >= 50:
        recommendation = "Consider with Reservations"
    else:
        recommendation = "Not Recommended"

    # =========================
    # Final Recruiter Insight — clean sentence building
    # =========================
    insight_parts = []

    if competencies:
        # Strip trailing periods for clean joining
        comp_clean = [c.rstrip('.') for c in competencies]
        insight_parts.append("The candidate demonstrated: " + "; ".join(comp_clean) + ".")

    if concerns:
        concern_clean = [c.rstrip('.') for c in concerns]
        insight_parts.append("Areas requiring improvement: " + "; ".join(concern_clean) + ".")

    insight = " ".join(insight_parts)

    return {
        "overall_score": overall_score,
        "recommendation": recommendation,
        "competencies": competencies,
        "concerns": concerns,
        "insight": insight
    }