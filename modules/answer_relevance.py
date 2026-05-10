import ollama
import re

def evaluate_answer_relevance(
    question,
    answer
):

    prompt = f"""
You are an extremely strict AI interviewer.

Interview Question:
{question}

Candidate Answer:
{answer}

Evaluate ONLY how relevant the answer is to the question.

SCORING RULES:

0-20:
Completely irrelevant answer.

21-40:
Mostly unrelated or vague answer.

41-60:
Partially answers question.

61-80:
Good relevant answer.

81-100:
Excellent precise answer.

IMPORTANT:
- If the answer avoids the topic, give below 20.
- If candidate introduces themselves for a technical question, give below 15.
- Be extremely strict.

Return ONLY a number.
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

    result = response["message"]["content"]

    numbers = re.findall(
        r'\d+',
        result
    )

    if numbers:

        score = int(numbers[0])

    else:

        score = 10

    score = max(
        0,
        min(score, 100)
    )

    return score