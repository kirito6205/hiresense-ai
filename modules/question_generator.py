import ollama


def generate_interview_question(role):

    prompt = f"""
    Generate ONE professional interview question
    for a {role} candidate.

    Rules:
    - Return ONLY the interview question
    - No explanations
    - No numbering
    - Professional tone
    """

    response = ollama.chat(

        model="phi3",

        messages=[

            {
                "role": "user",
                "content": prompt
            }

        ]

    )

    question = response["message"]["content"]

    return question.strip()