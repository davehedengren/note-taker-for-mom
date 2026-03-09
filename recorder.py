"""Audio recording using sounddevice. Saves WAV files locally."""

import os
import threading
from datetime import datetime
from pathlib import Path

import sounddevice as sd
import soundfile as sf

RECORDINGS_DIR = Path.home() / ".note-taker-for-mom" / "recordings"
SAMPLE_RATE = 16000  # 16kHz — standard for speech recognition
CHANNELS = 1  # Mono — sufficient for speech, smaller files


class Recorder:
    def __init__(self):
        self._recording = False
        self._frames = []
        self._thread = None
        self._output_path = None

    def start(self) -> str:
        """Start recording. Returns the path where the audio will be saved."""
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._output_path = str(RECORDINGS_DIR / f"session_{timestamp}.wav")
        self._frames = []
        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        return self._output_path

    def stop(self) -> tuple[str, float]:
        """Stop recording. Returns (file_path, duration_seconds)."""
        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)

        if not self._frames:
            return self._output_path, 0.0

        import numpy as np
        audio_data = np.concatenate(self._frames, axis=0)
        sf.write(self._output_path, audio_data, SAMPLE_RATE)
        duration = len(audio_data) / SAMPLE_RATE
        return self._output_path, duration

    def is_recording(self) -> bool:
        return self._recording

    def _record_loop(self):
        """Capture audio in chunks."""
        import numpy as np
        chunk_duration = 0.5  # seconds per chunk
        chunk_samples = int(SAMPLE_RATE * chunk_duration)

        while self._recording:
            chunk = sd.rec(chunk_samples, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
            sd.wait()
            if self._recording:  # Only save if we didn't stop mid-chunk
                self._frames.append(chunk)
