def analyze_star_structure(transcript):

    transcript = transcript.lower()

    star_result = {

        "situation": False,
        "task": False,
        "action": False,
        "result": False
    }

    # Situation keywords

    situation_keywords = [

        "during",
        "when",
        "in my project",
        "while",
        "at my internship"
    ]

    # Task keywords

    task_keywords = [

        "needed to",
        "had to",
        "responsible",
        "task",
        "challenge"
    ]

    # Action keywords

    action_keywords = [

        "implemented",
        "developed",
        "created",
        "solved",
        "built",
        "managed"
    ]

    # Result keywords

    result_keywords = [

        "improved",
        "increased",
        "successfully",
        "achieved",
        "reduced",
        "result"
    ]

    # Detection

    if any(
        word in transcript
        for word in situation_keywords
    ):
        star_result["situation"] = True

    if any(
        word in transcript
        for word in task_keywords
    ):
        star_result["task"] = True

    if any(
        word in transcript
        for word in action_keywords
    ):
        star_result["action"] = True

    if any(
        word in transcript
        for word in result_keywords
    ):
        star_result["result"] = True

    # Score

    score = sum(
        star_result.values()
    ) * 25

    # Level

    if score == 100:

        level = "Excellent STAR Structure"

    elif score >= 75:

        level = "Strong STAR Structure"

    elif score >= 50:

        level = "Moderate STAR Structure"

    else:

        level = "Weak STAR Structure"

    return {

        "score": score,

        "level": level,

        "details": star_result
    }