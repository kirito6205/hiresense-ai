import ollama

def generate_llm_feedback(
    transcript,
    score,
    communication_level,
    star_level
):
    prompt = f"""
You are an expert AI recruiter assistant evaluating a candidate interview.

Analyze the interview response below and return structured recruiter feedback in clean Markdown format.

Use these exact section headers (##) and bullet points (-):

## 1. Communication
- [your point here]

## 2. Confidence
- [your point here]

## 3. Technical Clarity
- [your point here]

## 4. Behavioral / STAR Quality
- [your point here]

## 5. Improvements
- [your point here]

## 6. Final Recommendation
- [your point here]

Rules:
- Use proper Markdown with ## for headings and - for bullet points
- Each section: 1-2 concise bullet points only
- Be specific, professional, and actionable
- Do NOT write long paragraphs

Candidate Transcript:
{transcript}

Interview Score: {score}
Communication Level: {communication_level}
STAR Level: {star_level}
"""

    try:
        response = ollama.chat(
            model="phi3",
            messages=[{"role": "user", "content": prompt}]
        )
        feedback = response["message"]["content"]
        return feedback

    except Exception as e:
        return f"""## Communication
- Unable to generate AI recruiter feedback at this time.

## System Error
- {str(e)}

## Next Steps
- Ensure Ollama is running: `ollama serve`
- Ensure the phi3 model is installed: `ollama pull phi3`
"""