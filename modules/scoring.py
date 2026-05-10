def generate_feedback(
    speech,
    face,
    nlp,
    behavior
):

    feedback = []

    # Speech
    if speech > 80:
        feedback.append(
            "Candidate communicated fluently with minimal filler words."
        )

    else:
        feedback.append(
            "Speech delivery needs improvement."
        )

    # Face / Behavior
    if face > 70:
        feedback.append(
            f"{behavior} during the interview."
        )

    else:
        feedback.append(
            "Facial confidence indicators were relatively low."
        )

    # NLP
    if nlp > 70:
        feedback.append(
            "Answer content was highly relevant and meaningful."
        )

    elif nlp > 40:
        feedback.append(
            "Answer was partially relevant."
        )

    else:
        feedback.append(
            "Response relevance to the interview context was low."
        )

    return " ".join(feedback)


def calculate_score(
    speech,
    face,
    nlp
):

    final_score = round(
        0.3 * speech +
        0.3 * face +
        0.4 * nlp,
        2
    )

    return final_score