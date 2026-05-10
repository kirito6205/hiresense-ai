# ============================================================
# live_interview_routes.py
# Add this file to your project root, then register it in app.py
# ============================================================
#
# INSTALL DEPENDENCIES FIRST:
#   pip install flask-socketio opencv-python mediapipe \
#               openai-whisper numpy scipy soundfile eventlet
#
# IN YOUR app.py, add these lines near the top:
#   from flask_socketio import SocketIO, emit
#   from live_interview_routes import register_live_routes
#   socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
#   register_live_routes(socketio, db)
#
# CHANGE your app runner at the bottom of app.py to:
#   if __name__ == "__main__":
#       socketio.run(app, host="127.0.0.1", port=5000, debug=True)
# ============================================================

import os
import uuid
import base64
import tempfile
import threading
import numpy as np
from datetime import datetime
from collections import deque

# OpenCV + MediaPipe
import cv2
import mediapipe as mp

# Whisper (speech-to-text)
import whisper

# Your existing modules
from modules.nlp_analysis import analyze_text
from modules.scoring import calculate_score, generate_feedback
from modules.llm_feedback import generate_llm_feedback
from modules.question_generator import generate_interview_question
from modules.answer_relevance import evaluate_answer_relevance

# ─── Globals ──────────────────────────────────────────────────────────────────
_whisper_model = None
_whisper_lock  = threading.Lock()

mp_face_mesh   = mp.solutions.face_mesh
mp_drawing     = mp.solutions.drawing_utils

# Per-session state  {session_id: {...}}
_sessions: dict = {}


def _get_whisper():
    global _whisper_model
    with _whisper_lock:
        if _whisper_model is None:
            _whisper_model = whisper.load_model("base")  # swap to "small" for better accuracy
    return _whisper_model


# ─── Emotion from landmarks ────────────────────────────────────────────────────
def _detect_emotion_from_landmarks(landmarks, w, h):
    """
    Lightweight rule-based emotion detection from MediaPipe face landmarks.
    Returns (emotion_label, confidence_score 0-100).
    """
    try:
        # Key landmark indices
        LEFT_EYE_TOP    = 159
        LEFT_EYE_BOT    = 145
        RIGHT_EYE_TOP   = 386
        RIGHT_EYE_BOT   = 374
        MOUTH_LEFT      = 61
        MOUTH_RIGHT     = 291
        UPPER_LIP       = 13
        LOWER_LIP       = 14
        LEFT_BROW_TOP   = 105
        LEFT_EYE_INNER  = 133

        def pt(idx):
            l = landmarks.landmark[idx]
            return np.array([l.x * w, l.y * h])

        # Eye Aspect Ratio (low = eyes closed / stressed)
        eye_h_l = np.linalg.norm(pt(LEFT_EYE_TOP)  - pt(LEFT_EYE_BOT))
        eye_h_r = np.linalg.norm(pt(RIGHT_EYE_TOP) - pt(RIGHT_EYE_BOT))
        eye_w   = np.linalg.norm(pt(MOUTH_LEFT)    - pt(MOUTH_RIGHT))
        ear     = (eye_h_l + eye_h_r) / (2.0 * eye_w + 1e-6)

        # Mouth openness ratio
        mouth_h = np.linalg.norm(pt(UPPER_LIP) - pt(LOWER_LIP))
        mouth_w = np.linalg.norm(pt(MOUTH_LEFT) - pt(MOUTH_RIGHT))
        mar     = mouth_h / (mouth_w + 1e-6)

        # Brow raise (higher = surprised/confident)
        brow_raise = (pt(LEFT_EYE_INNER)[1] - pt(LEFT_BROW_TOP)[1]) / (h + 1e-6)

        # Simple decision rules
        if ear < 0.05:
            return "Nervous", 40
        elif mar > 0.35:
            return "Surprised", 60
        elif brow_raise > 0.06 and ear > 0.08:
            return "Confident", 82
        elif ear > 0.07 and mar < 0.15:
            return "Calm", 75
        else:
            return "Neutral", 65

    except Exception:
        return "Neutral", 60


# ─── Eye contact score ─────────────────────────────────────────────────────────
def _eye_contact_score(landmarks, w, h):
    """Returns 0-100 score based on how centred the nose tip is horizontally."""
    try:
        nose = landmarks.landmark[1]
        deviation = abs(nose.x - 0.5)          # 0 = perfect centre
        score = max(0, int((1 - deviation * 4) * 100))
        return min(score, 100)
    except Exception:
        return 70


# ─── Register all live-interview socket events ─────────────────────────────────
def register_live_routes(socketio, db):
    results_collection = db["results"]
    live_collection    = db["live_sessions"]   # new collection for live data

    # ------------------------------------------------------------------
    # START SESSION  →  client sends role, gets first question
    # ------------------------------------------------------------------
    @socketio.on("live_start")
    def handle_live_start(data):
        from flask_socketio import emit
        from flask_login import current_user

        sid         = data.get("sid", str(uuid.uuid4()))
        role        = data.get("role", "Software Engineer")
        num_qs      = int(data.get("num_questions", 5))
        user_id     = data.get("user_id", "anonymous")
        user_name   = data.get("user_name", "Candidate")

        # Generate all questions upfront
        questions = [generate_interview_question(role) for _ in range(num_qs)]

        _sessions[sid] = {
            "sid":          sid,
            "user_id":      user_id,
            "user_name":    user_name,
            "role":         role,
            "questions":    questions,
            "current_q":    0,
            "answers":      [],           # list of per-answer result dicts
            "face_mesh":    mp_face_mesh.FaceMesh(
                                static_image_mode=False,
                                max_num_faces=1,
                                refine_landmarks=True,
                                min_detection_confidence=0.5,
                                min_tracking_confidence=0.5
                            ),
            # Rolling buffers (last 2 s worth of frames / audio chunks)
            "emotion_buf":  deque(maxlen=30),
            "eye_buf":      deque(maxlen=30),
            # Audio PCM accumulator for current answer
            "audio_chunks": [],
            "recording":    False,
            "started_at":   datetime.now(),
        }

        emit("live_session_ready", {
            "sid":      sid,
            "question": questions[0],
            "q_index":  0,
            "total":    num_qs,
        })

    # ------------------------------------------------------------------
    # VIDEO FRAME  →  client sends base64 JPEG every ~200 ms
    # ------------------------------------------------------------------
    @socketio.on("live_frame")
    def handle_live_frame(data):
        from flask_socketio import emit

        sid   = data.get("sid")
        frame = data.get("frame")   # base64 JPEG

        if sid not in _sessions or not frame:
            return

        sess = _sessions[sid]

        # Decode JPEG → numpy BGR
        try:
            img_bytes = base64.b64decode(frame.split(",")[-1])
            nparr     = np.frombuffer(img_bytes, np.uint8)
            img_bgr   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_bgr is None:
                return
            h, w = img_bgr.shape[:2]
        except Exception:
            return

        # MediaPipe face mesh
        img_rgb  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        results  = sess["face_mesh"].process(img_rgb)

        emotion, conf = "Neutral", 65
        eye_score     = 70

        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0]
            emotion, conf = _detect_emotion_from_landmarks(lm, w, h)
            eye_score     = _eye_contact_score(lm, w, h)

        sess["emotion_buf"].append((emotion, conf))
        sess["eye_buf"].append(eye_score)

        # Rolling averages
        avg_eye   = int(np.mean(list(sess["eye_buf"])))
        top_emo   = max(set(e for e, _ in sess["emotion_buf"]),
                        key=lambda e: sum(1 for x, _ in sess["emotion_buf"] if x == e))
        avg_conf  = int(np.mean([c for _, c in sess["emotion_buf"]]))

        emit("live_face_update", {
            "emotion":    top_emo,
            "confidence": avg_conf,
            "eye_contact": avg_eye,
        })

    # ------------------------------------------------------------------
    # AUDIO CHUNK  →  client sends base64 WebM/OGG chunk periodically
    # ------------------------------------------------------------------
    @socketio.on("live_audio_chunk")
    def handle_audio_chunk(data):
        sid   = data.get("sid")
        chunk = data.get("chunk")    # base64 audio

        if sid not in _sessions or not chunk:
            return

        try:
            audio_bytes = base64.b64decode(chunk.split(",")[-1])
            _sessions[sid]["audio_chunks"].append(audio_bytes)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # ANSWER DONE  →  client signals candidate stopped speaking
    #                 server transcribes + scores + saves + sends next Q
    # ------------------------------------------------------------------
    @socketio.on("live_answer_done")
    def handle_answer_done(data):
        from flask_socketio import emit

        sid = data.get("sid")
        if sid not in _sessions:
            emit("live_error", {"msg": "Session not found."})
            return

        sess     = _sessions[sid]
        q_index  = sess["current_q"]
        question = sess["questions"][q_index]

        emit("live_processing", {"msg": "Transcribing your answer…"})

        # ── Transcribe accumulated audio ──────────────────────────────
        transcript = ""
        audio_data = sess["audio_chunks"]

        if audio_data:
            try:
                # Write accumulated WebM chunks to a temp file
                with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                    for chunk in audio_data:
                        tmp.write(chunk)
                    tmp_path = tmp.name

                model      = _get_whisper()
                wresult    = model.transcribe(tmp_path, fp16=False)
                transcript = wresult.get("text", "").strip()
                os.unlink(tmp_path)
            except Exception as e:
                print(f"[Whisper error] {e}")
                transcript = ""

        # ── NLP scoring ───────────────────────────────────────────────
        # ── NLP scoring ───────────────────────────────────────────────
            try:
                nlp_result = analyze_text(transcript, question)
                nlp_score_nlp = nlp_result["score"]
            except Exception:
                nlp_result = {"score": 50, "communication_level": "Moderate",
                            "strengths": [], "weaknesses": []}
                nlp_score_nlp = 50

            # ── Ollama answer relevance (your phi3 model) ─────────────────
            try:
                if transcript.strip():
                    relevance_score = evaluate_answer_relevance(question, transcript)
                else:
                    relevance_score = 0
            except Exception as e:
                print(f"[Ollama error] {e}")
                relevance_score = nlp_score_nlp  # fallback to NLP score

            # Blend both: Ollama relevance is stricter and more accurate
            nlp_score = int(relevance_score * 0.7 + nlp_score_nlp * 0.3)

        # ── Face summary for this answer ──────────────────────────────
        emotion_buf = list(sess["emotion_buf"])
        eye_buf     = list(sess["eye_buf"])

        if emotion_buf:
            top_emotion = max(set(e for e, _ in emotion_buf),
                              key=lambda e: sum(1 for x, _ in emotion_buf if x == e))
            avg_face_conf = int(np.mean([c for _, c in emotion_buf]))
        else:
            top_emotion   = "Neutral"
            avg_face_conf = 65

        avg_eye = int(np.mean(eye_buf)) if eye_buf else 70

        # Face score = blend of face confidence + eye contact
        face_score = int(avg_face_conf * 0.6 + avg_eye * 0.4)

        # ── Combined answer score ─────────────────────────────────────
        speech_score = min(100, max(0, int(len(transcript.split()) / 2)))  # rough proxy
        final_score  = calculate_score(speech_score, face_score, nlp_score)

        # ── LLM qualitative feedback ──────────────────────────────────
        try:
            llm_fb = generate_llm_feedback(
                transcript, final_score,
                nlp_result["communication_level"], "Moderate"
            )
        except Exception:
            llm_fb = "Good attempt. Focus on providing more structured answers."

        # ── Build answer record ───────────────────────────────────────
        answer_record = {
            "q_index":    q_index,
            "question":   question[:120],
            "word_count": len(transcript.split()),
            "scores": {
                "speech":     speech_score,
                "face":       face_score,
                "nlp":        nlp_score,
                "final":      final_score,
            },
            "behavior": {
                "emotion":      top_emotion,
                "confidence":   avg_face_conf,
                "eye_contact":  avg_eye,
            },
            "nlp": {
                "communication_level": nlp_result["communication_level"],
                "strengths":           nlp_result.get("strengths", []),
                "weaknesses":          nlp_result.get("weaknesses", []),
            },
            "llm_feedback": llm_fb,
            "recorded_at":  datetime.now().isoformat(),
        }

        sess["answers"].append(answer_record)

        # ── Save to MongoDB (per answer) ──────────────────────────────
        live_collection.update_one(
            {"sid": sid},
            {"$set": {
                "user_id":    sess["user_id"],
                "user_name":  sess["user_name"],
                "role":       sess["role"],
                "updated_at": datetime.now(),
            }, "$push": {"answers": answer_record}},
            upsert=True
        )

        # ── Reset buffers for next question ──────────────────────────
        sess["audio_chunks"] = []
        sess["emotion_buf"].clear()
        sess["eye_buf"].clear()

        # ── Advance to next question or finish ────────────────────────
        next_index = q_index + 1
        sess["current_q"] = next_index

        emit("live_answer_result", {
            "q_index":    q_index,
            "question":   question,
            "transcript": transcript,
            "scores":     answer_record["scores"],
            "behavior":   answer_record["behavior"],
            "llm_feedback": llm_fb,
        })

        if next_index < len(sess["questions"]):
            emit("live_next_question", {
                "question": sess["questions"][next_index],
                "q_index":  next_index,
                "total":    len(sess["questions"]),
            })
        else:
            # ── All questions done → build full summary ────────────────
            _finish_session(sid, sess, results_collection, live_collection, emit)

    # ------------------------------------------------------------------
    # FINISH SESSION  →  aggregate all answers, emit summary
    # ------------------------------------------------------------------
    def _finish_session(sid, sess, results_col, live_col, emit_fn):
        answers = sess["answers"]
        if not answers:
            emit_fn("live_complete", {"error": "No answers recorded."})
            return

        # Average scores across all questions
        avg_speech = int(np.mean([a["scores"]["speech"] for a in answers]))
        avg_face   = int(np.mean([a["scores"]["face"]   for a in answers]))
        avg_nlp    = int(np.mean([a["scores"]["nlp"]    for a in answers]))
        avg_final  = int(np.mean([a["scores"]["final"]  for a in answers]))

        # Most common emotion overall
        all_emotions = [a["behavior"]["emotion"] for a in answers]
        overall_emotion = max(set(all_emotions), key=all_emotions.count)

        # Performance label
        if avg_final >= 80:
            level = "Outstanding Candidate"
        elif avg_final >= 65:
            level = "Strong Candidate"
        elif avg_final >= 50:
            level = "Moderate Candidate"
        else:
            level = "Needs Improvement"

        summary = {
            "sid":       sid,
            "role":      sess["role"],
            "answers":   answers,
            "overall": {
                "speech_score":  avg_speech,
                "face_score":    avg_face,
                "nlp_score":     avg_nlp,
                "final_score":   avg_final,
                "emotion":       overall_emotion,
                "level":         level,
                "total_questions": len(answers),
            },
            "completed_at": datetime.now().isoformat(),
        }

        # Save final summary to results collection (same as your other analyses)
        results_col.insert_one({
            "user_id":    sess["user_id"],
            "name":       sess["user_name"],
            "type":       "live_interview",
            "score":      avg_final,
            "role":       sess["role"],
            "summary":    summary,
            "created_at": datetime.now(),
        })

        # Mark live session as complete
        live_col.update_one(
            {"sid": sid},
            {"$set": {"completed": True, "summary": summary["overall"],
                      "completed_at": datetime.now()}}
        )

        # Clean up server-side session
        try:
            sess["face_mesh"].close()
        except Exception:
            pass
        _sessions.pop(sid, None)

        emit_fn("live_complete", summary)

    # ------------------------------------------------------------------
    # DISCONNECT cleanup
    # ------------------------------------------------------------------
    @socketio.on("disconnect")
    def handle_disconnect():
        # Clean up any orphaned sessions for this socket
        pass