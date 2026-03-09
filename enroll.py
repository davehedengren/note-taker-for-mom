"""Therapist voice enrollment — record a short sample to identify the therapist speaker.

The therapist records ~30 seconds of their voice. We extract a speaker embedding
using pyannote and store it locally. During diarization, we compare speaker
embeddings against this enrolled voice to determine who is the therapist.
All other speakers are labeled as Patient.
"""

import json
import os
from pathlib import Path

import numpy as np
import torch

ENROLLMENT_DIR = Path.home() / ".note-taker-for-mom" / "enrollment"
EMBEDDING_PATH = ENROLLMENT_DIR / "therapist_embedding.npy"
META_PATH = ENROLLMENT_DIR / "therapist_meta.json"


def get_hf_token() -> str:
    """Load Hugging Face token from .env or environment."""
    # Check environment first
    token = os.environ.get("HUGGING_FACE_API_KEY") or os.environ.get("HF_TOKEN")
    if token:
        return token

    # Try loading from .env file in the project directory
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("HUGGING_FACE_API_KEY="):
                return line.split("=", 1)[1].strip()
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip()

    raise EnvironmentError(
        "No Hugging Face token found. Set HUGGING_FACE_API_KEY in .env or environment."
    )


def extract_embedding(audio_path: str) -> np.ndarray:
    """Extract a speaker embedding from an audio file using pyannote.

    Args:
        audio_path: Path to a WAV file containing a single speaker.

    Returns:
        Speaker embedding as a numpy array.
    """
    from pyannote.audio import Model, Inference

    hf_token = get_hf_token()
    model = Model.from_pretrained(
        "pyannote/embedding",
        token=hf_token,
    )
    inference = Inference(model, window="whole")
    embedding = inference(audio_path)
    return np.array(embedding)


def enroll_therapist(audio_path: str, therapist_name: str = "Therapist") -> str:
    """Enroll the therapist's voice from a sample recording.

    Args:
        audio_path: Path to WAV file of the therapist speaking (~30s recommended).
        therapist_name: Display name for the therapist.

    Returns:
        Path to the saved embedding file.
    """
    ENROLLMENT_DIR.mkdir(parents=True, exist_ok=True)

    embedding = extract_embedding(audio_path)
    np.save(str(EMBEDDING_PATH), embedding)

    meta = {
        "name": therapist_name,
        "source_audio": audio_path,
    }
    META_PATH.write_text(json.dumps(meta, indent=2))

    return str(EMBEDDING_PATH)


def is_enrolled() -> bool:
    """Check if a therapist voice has been enrolled."""
    return EMBEDDING_PATH.exists()


def get_therapist_embedding() -> np.ndarray:
    """Load the stored therapist embedding."""
    if not EMBEDDING_PATH.exists():
        raise FileNotFoundError(
            "No therapist voice enrolled. Record a voice sample first."
        )
    return np.load(str(EMBEDDING_PATH))


def get_therapist_name() -> str:
    """Get the enrolled therapist's display name."""
    if META_PATH.exists():
        meta = json.loads(META_PATH.read_text())
        return meta.get("name", "Therapist")
    return "Therapist"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
