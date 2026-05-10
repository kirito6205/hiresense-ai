from flask import (
    Flask,
    render_template,
    request,
    flash,
    redirect
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from pymongo import MongoClient

from dotenv import load_dotenv

from datetime import datetime

import bcrypt
from markupsafe import Markup
import markdown as md_lib
import os


# =========================
# Interview AI Modules
# =========================
from modules.speech_analysis import analyze_speech
from modules.facial_analysis import analyze_face
from modules.nlp_analysis import analyze_text
from modules.star_analysis import analyze_star_structure
from modules.scoring import calculate_score, generate_feedback

# =========================
# Resume AI Modules
# =========================
from modules.resume_analysis import analyze_resume

# =========================
# Recruiter Intelligence
# =========================
from modules.hiring_recommendation import generate_hiring_recommendation

# =========================
# LLM Recruiter Feedback
# =========================
from modules.llm_feedback import generate_llm_feedback
from modules.question_generator import (
    generate_interview_question
)
from models.user import User

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY"
)
# =========================
# MongoDB Setup
# =========================

client = MongoClient(
    os.getenv("MONGO_URI")
)

db = client["hiresense_ai"]

users_collection = db["users"]

results_collection = db["results"]

# =========================
# Flask Login Setup
# =========================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):

    return User.get(
        users_collection,
        user_id
    )

# =========================
# Markdown Jinja Filter
# =========================
@app.template_filter('markdown')
def render_markdown(text):

    if not text:
        return Markup("")

    return Markup(
        md_lib.markdown(
            str(text),
            extensions=['nl2br']
        )
    )

# =========================
# Storage Folders
# =========================
UPLOAD_FOLDER = "uploads"
RESUME_FOLDER = "resumes"
JD_FOLDER = "job_descriptions"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESUME_FOLDER, exist_ok=True)
os.makedirs(JD_FOLDER, exist_ok=True)

# ====================================================
# Register
# ====================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get("name")

        email = request.form.get("email")

        password = request.form.get("password")

        role = request.form.get("role")

        existing_user = users_collection.find_one({
            "email": email
        })

        if existing_user:

            flash(
                "Email already exists."
            )

            return redirect("/register")

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        users_collection.insert_one({

            "name": name,

            "email": email,

            "password": hashed_password,

            "role": role
        })

        flash(
            "Registration successful."
        )

        return redirect("/login")

    return render_template(
        "register.html"
    )

# ====================================================
# Login
# ====================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():
    if current_user.is_authenticated:

        if current_user.role == "recruiter":

            return redirect("/dashboard")

        return redirect("/")

    if request.method == "POST":

        email = request.form.get("email")

        password = request.form.get("password")

        user_data = users_collection.find_one({
            "email": email
        })

        if user_data and bcrypt.checkpw(
            password.encode("utf-8"),
            user_data["password"]
        ):

            user = User(user_data)

            login_user(user)

            flash(
                "Login successful."
            )

            if user.role == "recruiter":

                return redirect("/dashboard")

            return redirect("/")

        flash(
            "Invalid email or password."
        )

        return redirect("/login")

    return render_template(
        "login.html"
    )

# ====================================================
# Logout
# ====================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "Logged out successfully."
    )

    return redirect("/login")

# ====================================================
# Landing Page
# ====================================================
@app.route("/")
def home():

    if not current_user.is_authenticated:

        return redirect("/login")

    if current_user.role == "recruiter":

        return redirect("/dashboard")

    return render_template(
        "index.html"
    )

# ====================================================
# Interview Intelligence
# ====================================================
@app.route(
    "/interview-analysis",
    methods=["GET", "POST"]
)
@login_required
def interview_analysis():

    if request.method == "POST":

        try:

            ai_question = request.form.get(
                "question_key"
            )

            if "video" not in request.files:

                flash(
                    "Please upload an interview file."
                )

                return redirect(
                    "/interview-analysis"
                )

            video = request.files["video"]

            if video.filename == "":

                flash(
                    "No interview file selected."
                )

                return redirect(
                    "/interview-analysis"
                )

            # =================================
            # Save File
            # =================================

            video_path = os.path.join(
                UPLOAD_FOLDER,
                video.filename
            )

            video.save(video_path)

            # =================================
            # Detect Audio or Video
            # =================================

            file_type = video.mimetype

            is_audio_only = file_type.startswith(
                "audio"
            )

            # =================================
            # Speech Analysis
            # =================================

            speech_score, transcript, speech_analysis = analyze_speech(
                video_path
            )

            # =================================
            # Facial Analysis
            # =================================

            if is_audio_only:

                face_score = 0

                behavior = {

                    "emotion":
                    "Not Available (Audio Only)",

                    "confidence":
                    "Not Available",

                    "eye_contact":
                    "Not Available"
                }

            else:

                face_score, behavior = analyze_face(
                    video_path
                )

            # =================================
            # NLP + STAR
            # =================================

            nlp_result = analyze_text(
                transcript,
                ai_question
            )

            nlp_score = nlp_result["score"]

            star_result = analyze_star_structure(
                transcript
            )

            # =================================
            # Final Scoring
            # =================================

            final_score = calculate_score(
                speech_score,
                face_score,
                nlp_score
            )

            feedback = generate_feedback(
                speech_score,
                face_score,
                nlp_score,
                behavior
            )

            llm_feedback = generate_llm_feedback(
                transcript,
                final_score,
                nlp_result["communication_level"],
                star_result["level"]
            )

            # =================================
            # Result
            # =================================

            result = {

                "speech":
                speech_score,

                "face":
                face_score,

                "nlp":
                nlp_score,

                "final":
                final_score,

                "transcript":
                transcript,

                "behavior":
                behavior,

                "feedback":
                feedback,

                "llm_feedback":
                llm_feedback,

                "speech_analysis":
                speech_analysis,

                "nlp_communication":
                nlp_result["communication_level"],

                "nlp_strengths":
                nlp_result["strengths"],

                "nlp_weaknesses":
                nlp_result["weaknesses"],

                "star_score":
                star_result["score"],

                "star_level":
                star_result["level"],

                "star_details":
                star_result["details"],

                "is_audio_only":
                is_audio_only
            }
            results_collection.insert_one({

                "user_id": current_user.id,

                "name": current_user.name,

                "email": current_user.email,

                "type": "interview",

                "score": final_score,

                "created_at": datetime.now()
        })
           
            return render_template(
                "dashboard.html",
                result=result
            )

        except Exception as e:
                 
            print("\n========== ERROR ==========")
            print(e)
            print("===========================\n")

            raise e

    role = request.args.get(

        "role",

        "Data Scientist"
    )

    ai_question = generate_interview_question(
        role
    )

    return render_template(

        "interview_upload.html",

        ai_question=ai_question,

        role=role
    )

# ====================================================
# Resume Intelligence
# ====================================================
@app.route(
    "/resume-analysis",
    methods=["GET", "POST"]
)
@login_required
def resume_analysis():

    if request.method == "POST":

        try:

            resume = request.files["resume"]
            jd = request.files["jd"]

            resume_path = os.path.join(
                RESUME_FOLDER,
                resume.filename
            )

            jd_path = os.path.join(
                JD_FOLDER,
                jd.filename
            )

            resume.save(resume_path)
            jd.save(jd_path)

            result = analyze_resume(
                resume_path,
                jd_path
            )

            interview_score = 78

            hiring_result = generate_hiring_recommendation(
                interview_score,
                result["match_score"],
                "Moderate",
                50
            )

            result["interview_score"] = interview_score
            result["overall_score"] = hiring_result["overall_score"]
            result["recommendation"] = hiring_result["recommendation"]
            result["insight"] = hiring_result["insight"]
            result["competencies"] = hiring_result["competencies"]
            result["concerns"] = hiring_result["concerns"]

            return render_template(
                "resume_dashboard.html",
                result=result
            )

        except Exception as e:

            print(e)

            flash(
                "Resume analysis failed."
            )

            return redirect(
                "/resume-analysis"
            )

    return render_template(
        "resume_upload.html"
    )

# ====================================================
# Unified Hiring Intelligence
# ====================================================
@app.route(
    "/full-analysis",
    methods=["GET", "POST"]
)
@login_required
def full_analysis():

    if request.method == "POST":

        try:

            ai_question = request.form.get(
                "question_key"
            )

            video = request.files["video"]
            resume = request.files["resume"]
            jd = request.files["jd"]

            # =================================
            # Save Files
            # =================================

            video_path = os.path.join(
                UPLOAD_FOLDER,
                video.filename
            )

            resume_path = os.path.join(
                RESUME_FOLDER,
                resume.filename
            )

            jd_path = os.path.join(
                JD_FOLDER,
                jd.filename
            )

            video.save(video_path)
            resume.save(resume_path)
            jd.save(jd_path)

            # =================================
            # Detect Audio or Video
            # =================================

            file_type = video.mimetype

            is_audio_only = file_type.startswith(
                "audio"
            )

            # =================================
            # Speech Analysis
            # =================================

            speech_score, transcript, speech_analysis = analyze_speech(
                video_path
            )

            # =================================
            # Facial Analysis
            # =================================

            if is_audio_only:

                face_score = 0

                behavior = {

                    "emotion":
                    "Not Available (Audio Only)",

                    "confidence":
                    "Not Available",

                    "eye_contact":
                    "Not Available"
                }

            else:

                face_score, behavior = analyze_face(
                    video_path
                )

            # =================================
            # NLP + STAR
            # =================================

            nlp_result = analyze_text(
                transcript,
                ai_question
            )

            nlp_score = nlp_result["score"]

            star_result = analyze_star_structure(
                transcript
            )

            interview_score = calculate_score(
                speech_score,
                face_score,
                nlp_score
            )

            feedback = generate_feedback(
                speech_score,
                face_score,
                nlp_score,
                behavior
            )

            llm_feedback = generate_llm_feedback(
                transcript,
                interview_score,
                nlp_result["communication_level"],
                star_result["level"]
            )

            # =================================
            # Resume Analysis
            # =================================

            resume_result = analyze_resume(
                resume_path,
                jd_path
            )

            # =================================
            # Hiring Recommendation
            # =================================

            hiring_result = generate_hiring_recommendation(
                interview_score,
                resume_result["match_score"],
                nlp_result["communication_level"],
                star_result["score"]
            )

            # =================================
            # Result
            # =================================

            result = {

                "speech":
                speech_score,

                "face":
                face_score,

                "nlp":
                nlp_score,

                "interview_score":
                interview_score,

                "transcript":
                transcript,

                "behavior":
                behavior,

                "feedback":
                feedback,

                "llm_feedback":
                llm_feedback,

                "speech_analysis":
                speech_analysis,

                "nlp_communication":
                nlp_result["communication_level"],

                "nlp_strengths":
                nlp_result["strengths"],

                "nlp_weaknesses":
                nlp_result["weaknesses"],

                "star_score":
                star_result["score"],

                "star_level":
                star_result["level"],

                "star_details":
                star_result["details"],

                "resume_score":
                resume_result["match_score"],

                "matched_skills":
                resume_result["matched_skills"],

                "missing_skills":
                resume_result["missing_skills"],

                "overall_score":
                hiring_result["overall_score"],

                "recommendation":
                hiring_result["recommendation"],

                "insight":
                hiring_result["insight"],

                "competencies":
                hiring_result["competencies"],

                "concerns":
                hiring_result["concerns"],

                "is_audio_only":
                is_audio_only
            }
            results_collection.insert_one({

                "user_id": current_user.id,

                "name": current_user.name,

                "email": current_user.email,

                "type": "full analysis",

                "score": hiring_result["overall_score"],

                "created_at": datetime.now()
            })

            return render_template(
                "hiring_dashboard.html",
                result=result
            )

        except Exception as e:

            print(e)

            flash(
                 "Unified analysis failed."
            )

            return redirect(
                "/full-analysis"
            )

    role = request.args.get(

        "role",

        "Data Scientist"
    )

    ai_question = generate_interview_question(
        role
    )

    return render_template(

        "full_analysis.html",

        ai_question=ai_question,

        role=role
    )
# ====================================================
# Dashboard
# ====================================================

@app.route("/dashboard")
@login_required
def dashboard():

    if current_user.role == "recruiter":

        results = list(
            results_collection.find()
        )

        return render_template(
            "recruiter_dashboard.html",
            results=results
        )

    results = list(

        results_collection.find({

            "user_id": current_user.id

        })

    )

    return render_template(

        "candidate_dashboard.html",

        results=results
    )
# ====================================================
# Run Flask
# ====================================================
if __name__ == "__main__":

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True,

        use_reloader=False

    )