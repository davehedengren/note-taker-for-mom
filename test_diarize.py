"""Quick visual test for diarization — shows a speaker timeline."""

import sys
from audio_utils import ensure_wav
from diarize import diarize, assign_speaker_labels


def print_timeline(segments: list[dict], width: int = 80):
    """Print a text-based timeline of who spoke when."""
    if not segments:
        print("No segments found.")
        return

    total_duration = max(seg["end"] for seg in segments)
    print(f"\nTotal duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"Segments: {len(segments)}")
    print()

    # Collect unique speakers
    speakers = list(dict.fromkeys(seg["speaker"] for seg in segments))
    colors = {"Therapist": "█", "Patient": "▒"}

    # Print legend
    for speaker in speakers:
        char = colors.get(speaker, "░")
        total_time = sum(seg["end"] - seg["start"] for seg in segments if seg["speaker"] == speaker)
        pct = (total_time / total_duration) * 100
        print(f"  {char}{char}{char} {speaker}: {total_time:.1f}s ({pct:.0f}%)")
    print()

    # Print timeline bar
    print(f"  {'0s':<{width-6}}{'%.0fs' % total_duration:>6}")
    bar = [" "] * width
    for seg in segments:
        start_pos = int((seg["start"] / total_duration) * width)
        end_pos = int((seg["end"] / total_duration) * width)
        char = colors.get(seg["speaker"], "░")
        for i in range(start_pos, min(end_pos, width)):
            bar[i] = char
    print(f"  [{''.join(bar)}]")
    print()

    # Print first 20 segments as a table
    print(f"  {'Speaker':<12} {'Start':>7} {'End':>7} {'Duration':>8}")
    print(f"  {'-'*12} {'-'*7} {'-'*7} {'-'*8}")
    for seg in segments[:20]:
        dur = seg["end"] - seg["start"]
        start_fmt = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
        end_fmt = f"{int(seg['end']//60):02d}:{int(seg['end']%60):02d}"
        print(f"  {seg['speaker']:<12} {start_fmt:>7} {end_fmt:>7} {dur:>7.1f}s")
    if len(segments) > 20:
        print(f"  ... and {len(segments) - 20} more segments")


if __name__ == "__main__":
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "Fake-therapy-session.m4a"
    print(f"Converting {audio_path} to WAV...")
    wav_path = ensure_wav(audio_path)

    print(f"Running diarization on {wav_path}...")
    segments, diarize_output = diarize(wav_path, num_speakers=2)
    segments = assign_speaker_labels(segments, diarize_output)

    print_timeline(segments)
