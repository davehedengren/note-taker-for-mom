"""Audio format utilities — converts various formats to 16kHz mono WAV for processing."""

import subprocess
import shutil
from pathlib import Path


SUPPORTED_EXTENSIONS = {".wav", ".m4a", ".mp3", ".mp4", ".ogg", ".flac", ".aac", ".wma"}


def ensure_wav(audio_path: str) -> str:
    """Convert audio file to 16kHz mono WAV if needed.

    If already a WAV at the right spec, returns the original path.
    Otherwise, converts using ffmpeg and returns the new path.

    Args:
        audio_path: Path to any supported audio file.

    Returns:
        Path to a 16kHz mono WAV file.
    """
    path = Path(audio_path)

    if path.suffix.lower() == ".wav":
        # TODO: Could verify sample rate/channels, but skip for now
        return audio_path

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported audio format: {path.suffix}")

    if not shutil.which("ffmpeg"):
        raise EnvironmentError(
            "ffmpeg is required for audio conversion. Install with: brew install ffmpeg"
        )

    wav_path = path.with_suffix(".wav")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(path),
            "-ar", "16000",      # 16kHz sample rate
            "-ac", "1",          # mono
            "-sample_fmt", "s16", # 16-bit PCM
            str(wav_path),
        ],
        capture_output=True,
        check=True,
    )

    return str(wav_path)
