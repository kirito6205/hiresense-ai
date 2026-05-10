from sentence_transformers import (
    SentenceTransformer
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)

from modules.answer_relevance import (
    evaluate_answer_relevance
)

# NLP model
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

# Confidence indicators
CONFIDENT_WORDS = [

    "confident",
    "achieved",
    "improved",
    "successfully",
    "developed",
    "led",
    "solved",
    "managed",
    "created",
    "built"
]

# Technical keywords
TECHNICAL_WORDS = [

    "python",
    "machine learning",
    "ai",
    "nlp",
    "flask",
    "tensorflow",
    "deep learning",
    "sql",
    "api",
    "database"
]

# Filler words
FILLER_WORDS = [

    "um",
    "uh",
    "like",
    "you know",
    "basically",
    "actually"
]

def analyze_text(
    transcript,
    question_key="Tell me about yourself"
):

    transcript = transcript.lower()

    strengths = []

    weaknesses = []

    # =====================
    # Dynamic AI Question
    # =====================

    ideal_answer = question_key.lower()

    # =====================
    # Relevance Evaluation
    # =====================

    relevance_score = evaluate_answer_relevance(
        ideal_answer,
        transcript
    )

    if relevance_score >= 75:

        strengths.append(
            "Answer was highly relevant to the interview question."
        )

    elif relevance_score >= 50:

        strengths.append(
            "Answer was partially relevant to the question."
        )

    else:

        weaknesses.append(
            "Answer did not properly address the interview question."
        )

    # =====================
    # Semantic Similarity
    # =====================

    transcript_embedding = (
        model.encode([transcript])
    )

    ideal_embedding = (
        model.encode([ideal_answer])
    )

    similarity = cosine_similarity(
        transcript_embedding,
        ideal_embedding
    )[0][0]

    semantic_score = (
        similarity * 100
    )

    # =====================
    # Completeness
    # =====================

    word_count = len(
        transcript.split()
    )

    if word_count > 120:

        completeness_score = 100

        strengths.append(
            "Provided detailed and complete responses."
        )

    elif word_count > 80:

        completeness_score = 80

        strengths.append(
            "Response showed reasonable explanation depth."
        )

    elif word_count > 40:

        completeness_score = 60

    else:

        completeness_score = 35

        weaknesses.append(
            "Answer lacked depth and detail."
        )

    # =====================
    # Confidence Detection
    # =====================

    confidence_hits = sum(

        1 for word in CONFIDENT_WORDS

        if word in transcript
    )

    confidence_score = min(
        confidence_hits * 20,
        100
    )

    if confidence_hits >= 3:

        strengths.append(
            "Used confident and achievement-oriented language."
        )

    else:

        weaknesses.append(
            "Confidence indicators were limited."
        )

    # =====================
    # Technical Vocabulary
    # =====================

    technical_hits = sum(

        1 for word in TECHNICAL_WORDS

        if word in transcript
    )

    technical_score = min(
        technical_hits * 15,
        100
    )

    if technical_hits >= 2:

        strengths.append(
            "Demonstrated strong technical vocabulary."
        )

    elif technical_hits == 0:

        weaknesses.append(
            "Limited technical terminology detected."
        )

    # =====================
    # Filler Words
    # =====================

    filler_hits = sum(

        transcript.count(word)

        for word in FILLER_WORDS
    )

    filler_penalty = min(
        filler_hits * 5,
        30
    )

    if filler_hits > 3:

        weaknesses.append(
            "Frequent filler words affected communication clarity."
        )

    else:

        strengths.append(
            "Communication appeared relatively clear and focused."
        )

    # =====================
    # Final Score
    # =====================

    final_score = (

        relevance_score * 0.40 +

        semantic_score * 0.20 +

        completeness_score * 0.15 +

        confidence_score * 0.10 +

        technical_score * 0.15

    )

    # =====================
    # Heavy Penalty for Irrelevant Answers
    # =====================

    if relevance_score < 20:

        final_score *= 0.2

    elif relevance_score < 40:

        final_score *= 0.4

    final_score -= filler_penalty

    final_score = max(
        0,
        min(final_score, 100)
    )

    # =====================
    # Communication Level
    # =====================

    if final_score >= 80:

        communication_level = (
            "Excellent"
        )

    elif final_score >= 65:

        communication_level = (
            "Good"
        )

    elif final_score >= 50:

        communication_level = (
            "Moderate"
        )

    else:

        communication_level = (
            "Needs Improvement"
        )

    return {

        "score": round(
            float(final_score),
            2
        ),

        "communication_level":
        communication_level,

        "relevance_score":
        round(
            float(relevance_score),
            2
        ),

        "strengths":
        strengths,

        "weaknesses":
        weaknesses
    }