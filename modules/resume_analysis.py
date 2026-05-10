import fitz
import docx
import spacy

from sentence_transformers import (
    SentenceTransformer
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)

# Load NLP model
nlp = spacy.load(
    "en_core_web_sm"
)

# Load semantic model
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

# Skill database
SKILLS = [

    "python",
    "machine learning",
    "deep learning",
    "flask",
    "django",
    "sql",
    "mongodb",
    "tensorflow",
    "pytorch",
    "communication",
    "teamwork",
    "problem solving",
    "docker",
    "aws",
    "git",
    "data science",
    "nlp",
    "computer vision",
    "leadership",
    "react",
    "javascript",
    "java",
    "c++",
    "html",
    "css"
]

def extract_text(file_path):

    # PDF extraction
    if file_path.endswith(".pdf"):

        text = ""

        pdf = fitz.open(file_path)

        for page in pdf:

            text += page.get_text()

        return text

    # DOCX extraction
    elif file_path.endswith(".docx"):

        doc = docx.Document(file_path)

        text = "\n".join(
            para.text
            for para in doc.paragraphs
        )

        return text

    else:

        return ""

def extract_skills(text):

    text = text.lower()

    doc = nlp(text)

    found_skills = set()

    # Direct matching
    for skill in SKILLS:

        if skill in text:

            found_skills.add(skill)

    # NLP noun phrase analysis
    for chunk in doc.noun_chunks:

        chunk_text = chunk.text.strip()

        for skill in SKILLS:

            if skill in chunk_text:

                found_skills.add(skill)

    return list(found_skills)

def analyze_resume(
    resume_path,
    jd_path
):

    resume_text = extract_text(
        resume_path
    )

    jd_text = extract_text(
        jd_path
    )

    # Semantic embeddings
    resume_embedding = model.encode(
        [resume_text]
    )

    jd_embedding = model.encode(
        [jd_text]
    )

    similarity = cosine_similarity(
        resume_embedding,
        jd_embedding
    )[0][0]

    match_score = max(
        0,
        similarity * 100
    )

    # Skill extraction
    resume_skills = extract_skills(
        resume_text
    )

    jd_skills = extract_skills(
        jd_text
    )

    matched_skills = list(
        set(resume_skills)
        &
        set(jd_skills)
    )

    missing_skills = list(
        set(jd_skills)
        -
        set(resume_skills)
    )

    return {

        "match_score": round(
            float(match_score),
            2
        ),

        "matched_skills": matched_skills,

        "missing_skills": missing_skills
    }