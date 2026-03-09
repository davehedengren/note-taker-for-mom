"""Local DAP summary generation using Phi-3 via MLX."""

from mlx_lm import load, generate


# Phi-3 Mini — small enough to run locally, good enough for structured summaries.
# First run will download the model (~2.2GB).
MODEL_NAME = "mlx-community/Phi-3-mini-4k-instruct-4bit"

_model = None
_tokenizer = None


def _load_model():
    global _model, _tokenizer
    if _model is None:
        _model, _tokenizer = load(MODEL_NAME)
    return _model, _tokenizer


def generate_dap_summary(
    transcript_text: str,
    word_target: int = 75,
) -> str:
    """Generate a DAP (Data, Assessment, Plan) summary from a session transcript.

    Args:
        transcript_text: The full diarized transcript as plain text.
        word_target: Target word count for the summary (50-100, default 75).

    Returns:
        A DAP-formatted summary string.
    """
    model, tokenizer = _load_model()

    prompt = f"""<|user|>
You are a clinical documentation assistant. Given the following therapy session transcript,
write a concise DAP note in approximately {word_target} words.

DAP format:
- **Data**: Key objective facts and observations from the session (what the patient reported, behaviors observed).
- **Assessment**: Clinical interpretation of the data (progress, patterns, concerns).
- **Plan**: Next steps for treatment (interventions, homework, next session focus).

Be factual and professional. Do not include patient names or identifying information in the summary.

TRANSCRIPT:
{transcript_text}

Write the DAP note now.<|end|>
<|assistant|>
"""

    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=300,
        verbose=False,
    )

    return response.strip()


def format_transcript_for_summary(segments: list[dict]) -> str:
    """Convert merged transcript segments into plain text for the LLM."""
    lines = []
    for seg in segments:
        timestamp = _format_time(seg["start"])
        lines.append(f"[{seg['speaker']} {timestamp}] {seg['text']}")
    return "\n".join(lines)


def _format_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"
