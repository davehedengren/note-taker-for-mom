# Session Notes — Clinical Note Taker

A local-only therapy note-taking app. Records sessions, identifies speakers, transcribes audio, and generates DAP summaries. **All processing happens on your Mac — no patient data ever leaves the machine.**

Built for HIPAA-compliant clinical documentation.

## Quickstart

### Prerequisites

- **Mac with Apple Silicon** (M1/M2/M3/M4)
- **Python 3.11+** — download from [python.org](https://www.python.org/downloads/)
- **ffmpeg** — install with `brew install ffmpeg`
- **Hugging Face account** — free at [huggingface.co](https://huggingface.co/join)

### 1. Accept gated model licenses

Visit each link below while logged into Hugging Face and click "Agree and access":

- [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
- [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
- [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)

### 2. Set up your token

Create a `.env` file in the project folder:

```
HUGGING_FACE_API_KEY=hf_your_token_here
```

Get your token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

### 3. Launch

Double-click **`Start.command`** or run from terminal:

```bash
# First run creates venv and installs dependencies (~5 min)
# Then downloads ML models (~5 GB, one-time, ~10-20 min)
./Start.command
```

That's it. The app opens and you can start recording sessions.

### Quick test (no UI)

```bash
source venv/bin/activate
python pipeline.py your-session-recording.m4a
```

## How it works

```
Record/load audio
  → Speaker diarization (pyannote-audio) — who spoke when
  → Transcription (Whisper large-v3 via MLX) — what was said
  → Merge — labeled transcript
  → DAP summary (Phi-3 via MLX) — Data, Assessment, Plan
  → Save to encrypted local database
  → Export as PDF
```

### Speaker identification

The app can learn the therapist's voice. Enroll a ~30 second voice sample using the "Therapist Voice" panel in the sidebar. After enrollment, the app automatically identifies which speaker is the therapist and which is the patient.

Without enrollment, it uses a heuristic (first speaker = therapist).

## What's in the box

| File | Purpose |
|---|---|
| `app.py` | PyQt6 desktop UI |
| `recorder.py` | Mic audio capture (16kHz mono WAV) |
| `diarize.py` | Speaker diarization via pyannote-audio |
| `transcribe.py` | Whisper transcription via MLX |
| `summarize.py` | Phi-3 DAP summary generation via MLX |
| `pipeline.py` | Orchestrates the full processing flow |
| `enroll.py` | Therapist voice enrollment + matching |
| `audio_utils.py` | Audio format conversion (m4a, mp3, etc → WAV) |
| `db.py` | SQLite storage for sessions, transcripts, summaries |
| `export.py` | PDF export with transcript + summary |
| `feedback.py` | Thumbs up/down feedback logging |
| `first_run_setup.py` | First-launch model download wizard |
| `demo.html` | Interactive demo UI (open in browser) |
| `test_diarize.py` | Visual diarization test script |
| `Start.command` | Double-click launcher for macOS |

## Privacy and compliance

- **Local only.** Audio, transcripts, summaries, and patient data never leave the machine.
- **No cloud APIs.** All ML models run on-device via Apple Silicon (MLX).
- **No telemetry.** No analytics, crash reports, or external network calls (except initial model download from Hugging Face).
- **Encrypted storage.** Database supports encryption via sqlcipher (enable for production use).
- **Audit logging.** All feedback and access is logged locally.
- **.gitignore excludes all sensitive files** — .env, .db, .wav, .m4a, .pdf, enrollment data.

## Data storage

All data lives in `~/.note-taker-for-mom/`:

```
~/.note-taker-for-mom/
  sessions.db          # Session database
  recordings/          # Audio files
  enrollment/          # Therapist voice embedding
  exports/             # Generated PDFs
```

## Roadmap

- [ ] Switch to sqlcipher for encrypted database
- [ ] App authentication (passphrase / biometric)
- [ ] Cerner (Oracle Health) FHIR R4 integration
- [ ] Editable speaker labels in transcript view
- [ ] Swap speaker assignment after diarization
- [ ] Configurable note formats (SOAP, BIRP)
- [ ] Encrypted local backup to USB

## License

This project is for educational use. Not certified for clinical production use without proper security review and encryption enabled.
