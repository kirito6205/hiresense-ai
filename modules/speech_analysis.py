import whisper
from moviepy import VideoFileClip
import os

model = whisper.load_model("base")

FILLER_WORDS = [
    "um",
    "uh",
    "like",
    "you know",
    "basically",
    "actually",
    "so"
]

def analyze_speech(video_path):

    audio_path = "temp_audio.wav"

    # Convert video to audio safely
    if video_path.lower().endswith(
        (".mp4", ".mov", ".avi", ".mkv")
    ):

        video = VideoFileClip(video_path)

        if video.audio is None:

            raise Exception(
                "No audio stream found."
            )

        video.audio.write_audiofile(
            audio_path,
            logger=None
        )

        transcription_path = audio_path

    else:

        transcription_path = video_path

    result = model.transcribe(
        transcription_path
    )

    transcript = result["text"]

    words = transcript.split()

    word_count = len(words)

    filler_count = sum(

        word.lower().strip(".,!?")
        in FILLER_WORDS

        for word in words
    )

    filler_ratio = (
        filler_count / word_count
        if word_count > 0
        else 0
    )

    duration = result.get(
        "segments",
        []
    )

    total_duration = 0

    for segment in duration:

        total_duration += (
            segment["end"] -
            segment["start"]
        )

    if total_duration > 0:

        words_per_minute = (
            word_count / total_duration
        ) * 60

    else:

        words_per_minute = 0

    if words_per_minute < 90:

        pace_feedback = (
            "Speech pace was slow."
        )

    elif words_per_minute <= 150:

        pace_feedback = (
            "Speech pace was balanced."
        )

    else:

        pace_feedback = (
            "Speech pace was fast."
        )

    if filler_ratio < 0.03:

        clarity_feedback = (
            "Communication was very clear."
        )

    elif filler_ratio < 0.08:

        clarity_feedback = (
            "Communication clarity was moderate."
        )

    else:

        clarity_feedback = (
            "Frequent filler words reduced clarity."
        )

    if (
        filler_ratio < 0.05 and
        90 <= words_per_minute <= 150
    ):

        confidence = "High"

    elif filler_ratio < 0.1:

        confidence = "Moderate"

    else:

        confidence = "Low"

    speech_score = max(
        0,
        100 - (
            filler_ratio * 100
        )
    )

    speech_analysis = (
        f"{pace_feedback} "
        f"{clarity_feedback} "
        f"Detected {filler_count} filler words. "
        f"Estimated confidence level: {confidence}."
    )

    # Cleanup
    if os.path.exists(audio_path):

        os.remove(audio_path)

    return (
        round(speech_score, 2),
        transcript,
        speech_analysis
    )