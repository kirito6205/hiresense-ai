import cv2
import mediapipe as mp
from deepface import DeepFace
from collections import Counter

mp_face_mesh = mp.solutions.face_mesh

LEFT_EYE = [33, 133]
RIGHT_EYE = [362, 263]

def analyze_face(video_path):

    cap = cv2.VideoCapture(video_path)

    emotions_detected = []

    eye_contact_frames = 0
    total_frames = 0

    frame_count = 0

    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True
    )

    while cap.isOpened():

        ret, frame = cap.read()

        if not ret:
            break

        frame_count += 1
        total_frames += 1

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = face_mesh.process(rgb_frame)

        # Eye contact estimation
        if results.multi_face_landmarks:

            eye_contact_frames += 1

        # Emotion analysis every 30th frame
        if frame_count % 30 == 0:

            try:

                result = DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False
                )

                dominant_emotion = result[0]['dominant_emotion']

                emotions_detected.append(
                    dominant_emotion
                )

            except:
                pass

    cap.release()

    if len(emotions_detected) == 0:

        return 50, "No clear face detected"

    emotion_counts = Counter(emotions_detected)

    dominant_emotion = emotion_counts.most_common(1)[0][0]

    confident_emotions = [
        'happy',
        'neutral'
    ]

    confidence_count = sum(
        emotion in confident_emotions
        for emotion in emotions_detected
    )

    emotion_score = (
        confidence_count /
        len(emotions_detected)
    ) * 100

    eye_contact_score = (
        eye_contact_frames /
        total_frames
    ) * 100

    final_face_score = (
        emotion_score * 0.7 +
        eye_contact_score * 0.3
    )

    # Behavior interpretation
    if dominant_emotion == 'happy':

        behavior = (
            "Appeared confident, positive, "
            "and maintained good engagement."
        )

    elif dominant_emotion == 'neutral':

        behavior = (
            "Appeared calm, composed, "
            "and attentive."
        )

    elif dominant_emotion in ['fear', 'sad']:

        behavior = (
            "Behavioral indicators suggest "
            "possible nervousness."
        )

    elif dominant_emotion == 'angry':

        behavior = (
            "Appeared tense or stressed."
        )

    else:

        behavior = (
            f"Dominant emotion detected: "
            f"{dominant_emotion}"
        )

    # Add eye contact interpretation
    if eye_contact_score > 75:

        behavior += (
            " Maintained strong eye contact."
        )

    elif eye_contact_score > 40:

        behavior += (
            " Maintained moderate eye contact."
        )

    else:

        behavior += (
            " Eye contact appeared limited."
        )

    return round(final_face_score, 2), behavior