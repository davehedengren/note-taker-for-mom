"""Orchestrates the full pipeline: convert → diarize → transcribe → merge → summarize."""

from audio_utils import ensure_wav
from diarize import diarize, assign_speaker_labels
from transcribe import transcribe, merge_diarization_and_transcript
from summarize import generate_dap_summary, format_transcript_for_summary
from db import (
    init_db,
    create_session,
    save_transcript_segments,
    save_summary,
    get_transcript,
)


def process_audio(audio_path: str, word_target: int = 75) -> dict:
    """Run the full pipeline on a recorded audio file.

    Args:
        audio_path: Path to the audio file (WAV, m4a, mp3, etc.).
        word_target: Target word count for DAP summary.

    Returns:
        Dict with session_id, transcript segments, and summary.
    """
    init_db()

    print(f"[0/4] Converting audio to WAV...")
    wav_path = ensure_wav(audio_path)
    print(f"       Using: {wav_path}")

    print(f"[1/4] Starting diarization...")
    diar_segments, diarize_output = diarize(wav_path, num_speakers=2)
    diar_segments = assign_speaker_labels(diar_segments, diarize_output)
    print(f"       Found {len(diar_segments)} speaker segments.")

    print(f"[2/4] Transcribing audio...")
    transcript_segments = transcribe(wav_path)
    print(f"       Transcribed {len(transcript_segments)} text segments.")

    print(f"[3/4] Merging diarization with transcript...")
    merged = merge_diarization_and_transcript(diar_segments, transcript_segments)

    # Get audio duration from the last segment
    duration = merged[-1]["end"] if merged else 0.0
    session_id = create_session(audio_path, duration)
    save_transcript_segments(session_id, merged)

    print(f"[4/4] Generating DAP summary ({word_target} word target)...")
    transcript_text = format_transcript_for_summary(merged)
    summary = generate_dap_summary(transcript_text, word_target=word_target)
    save_summary(session_id, summary, word_target=word_target)

    print(f"\nDone! Session #{session_id} saved.")
    return {
        "session_id": session_id,
        "segments": merged,
        "summary": summary,
    }


def reprocess_summary(session_id: int, word_target: int = 75) -> str:
    """Regenerate a summary for an existing session."""
    segments = get_transcript(session_id)
    if not segments:
        raise ValueError(f"No transcript found for session {session_id}")

    transcript_text = format_transcript_for_summary(segments)
    summary = generate_dap_summary(transcript_text, word_target=word_target)
    save_summary(session_id, summary, word_target=word_target)
    return summary


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <audio_file> [word_target]")
        print("Supports: WAV, m4a, mp3, mp4, ogg, flac, aac")
        sys.exit(1)

    audio_file = sys.argv[1]
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 75
    result = process_audio(audio_file, word_target=target)

    print("\n--- TRANSCRIPT ---")
    for seg in result["segments"]:
        mins = int(seg["start"] // 60)
        secs = int(seg["start"] % 60)
        print(f"[{seg['speaker']} {mins:02d}:{secs:02d}] {seg['text']}")

    print("\n--- DAP SUMMARY ---")
    print(result["summary"])
