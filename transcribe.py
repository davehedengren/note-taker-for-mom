"""Local transcription using Whisper via MLX on Apple Silicon."""

import mlx_whisper


# Use the large-v3 model for accuracy over speed.
# First run will download the model (~3GB).
MODEL = "mlx-community/whisper-large-v3-mlx"


def transcribe(audio_path: str) -> list[dict]:
    """Transcribe an audio file with timestamps.

    Args:
        audio_path: Path to WAV file.

    Returns:
        List of segments: [{"start": 0.0, "end": 5.2, "text": "..."}, ...]
    """
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=MODEL,
        language="en",
        verbose=False,
    )

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return segments


def merge_diarization_and_transcript(
    diarization_segments: list[dict],
    transcript_segments: list[dict],
) -> list[dict]:
    """Merge diarization (who) with transcription (what) based on time overlap.

    For each transcript segment, find the diarization segment with the most
    temporal overlap and assign that speaker.

    Returns:
        List of merged segments:
        [{"speaker": "Therapist", "start": 0.0, "end": 5.2, "text": "..."}, ...]
    """
    merged = []

    for t_seg in transcript_segments:
        best_speaker = "Unknown"
        best_overlap = 0.0

        for d_seg in diarization_segments:
            # Calculate overlap between transcript and diarization segments
            overlap_start = max(t_seg["start"], d_seg["start"])
            overlap_end = min(t_seg["end"], d_seg["end"])
            overlap = max(0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d_seg["speaker"]

        merged.append({
            "speaker": best_speaker,
            "start": t_seg["start"],
            "end": t_seg["end"],
            "text": t_seg["text"],
        })

    return merged
