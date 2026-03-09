"""Speaker diarization using pyannote-audio. Identifies who spoke when.

Uses therapist voice enrollment to reliably label the therapist speaker.
All other speakers are labeled as Patient.
"""

# IMPORTANT: pyannote-audio requires:
# 1. A Hugging Face account
# 2. Accept the license at https://huggingface.co/pyannote/speaker-diarization-3.1
# 3. Accept the license at https://huggingface.co/pyannote/segmentation-3.0
# 4. Set HUGGING_FACE_API_KEY in .env

import numpy as np
from enroll import (
    get_hf_token,
    is_enrolled,
    get_therapist_embedding,
    get_therapist_name,
    extract_embedding,
    cosine_similarity,
)


def diarize(audio_path: str, num_speakers: int = 2) -> list[dict]:
    """Run speaker diarization on an audio file.

    Args:
        audio_path: Path to WAV file (16kHz mono recommended).
        num_speakers: Expected number of speakers (default 2: therapist + patient).

    Returns:
        List of segments: [{"speaker": "SPEAKER_00", "start": 0.0, "end": 5.2}, ...]
    """
    from pyannote.audio import Pipeline

    hf_token = get_hf_token()

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token,
    )

    # Run diarization with known number of speakers
    diarize_output = pipeline(audio_path, num_speakers=num_speakers)

    # pyannote v4 returns a DiarizeOutput dataclass
    annotation = diarize_output.speaker_diarization

    segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
        })

    return segments, diarize_output


def assign_speaker_labels(segments: list[dict], diarize_output) -> list[dict]:
    """Label speakers as Therapist or Patient using voice enrollment.

    Uses speaker embeddings from pyannote's DiarizeOutput when available,
    compared against the enrolled therapist voice.

    Falls back to a heuristic (first speaker = Therapist) if no enrollment exists.
    """
    if not segments:
        return segments

    # Get unique speaker IDs (in order from the annotation)
    annotation = diarize_output.speaker_diarization
    speaker_ids = annotation.labels()

    if is_enrolled() and diarize_output.speaker_embeddings is not None:
        therapist_embedding = get_therapist_embedding()
        therapist_name = get_therapist_name()

        # speaker_embeddings is (num_speakers, dimension), ordered by speaker_ids
        similarities = {}
        for i, sid in enumerate(speaker_ids):
            sim = cosine_similarity(therapist_embedding, diarize_output.speaker_embeddings[i])
            similarities[sid] = sim
            print(f"  Speaker {sid}: similarity to therapist = {sim:.3f}")

        therapist_id = max(similarities, key=similarities.get)
        label_map = {}
        for sid in speaker_ids:
            if sid == therapist_id:
                label_map[sid] = therapist_name
            else:
                label_map[sid] = "Patient"
        print(f"  Matched {therapist_id} as '{therapist_name}' (similarity: {similarities[therapist_id]:.3f})")
    else:
        if not is_enrolled():
            print("WARNING: No therapist voice enrolled. Using heuristic (first speaker = Therapist).")
            print("         Enroll a voice sample for reliable speaker identification.")
        else:
            print("WARNING: No speaker embeddings returned. Using heuristic.")
        first_speaker = segments[0]["speaker"]
        label_map = {first_speaker: "Therapist"}
        for sid in speaker_ids:
            if sid not in label_map:
                label_map[sid] = "Patient"

    for seg in segments:
        seg["speaker"] = label_map.get(seg["speaker"], "Unknown")

    return segments
