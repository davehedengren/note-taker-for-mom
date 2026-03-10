"""First-run setup — downloads ML models with a progress GUI.

Shows a PyQt6 dialog so mom isn't staring at a blank terminal for 20 minutes
while 5GB of models download.
"""

import sys
import os
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton,
    QTextEdit, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from enroll import get_hf_token


class SetupSignals(QObject):
    progress = pyqtSignal(str, int)  # (message, percent)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # (success, message)


class SetupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Session Notes — First-Time Setup")
        self.setMinimumSize(520, 400)
        self.setModal(True)
        self.signals = SetupSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.log.connect(self._on_log)
        self.signals.finished.connect(self._on_finished)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "<h2>Welcome to Session Notes</h2>"
            "<p>First-time setup needs to download speech recognition and "
            "summarization models. This is a one-time process.</p>"
            "<p><b>Everything stays on this machine — no patient data leaves your computer.</b></p>"
        ))

        self.status_label = QLabel("Ready to set up")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        log_group = QGroupBox("Details")
        log_layout = QVBoxLayout(log_group)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(150)
        self.log_display.setStyleSheet("font-family: monospace; font-size: 11px;")
        log_layout.addWidget(self.log_display)
        layout.addWidget(log_group)

        self.start_btn = QPushButton("Start Setup")
        self.start_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.start_btn.clicked.connect(self._start_setup)
        layout.addWidget(self.start_btn)

        self.close_btn = QPushButton("Launch App")
        self.close_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.hide()
        layout.addWidget(self.close_btn)

    def _start_setup(self):
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Setting up...")
        threading.Thread(target=self._run_setup, daemon=True).start()

    def _run_setup(self):
        try:
            # Step 1: Check HF token
            self.signals.progress.emit("Checking Hugging Face token...", 5)
            try:
                token = get_hf_token()
                self.signals.log.emit(f"✓ HF token found: {token[:8]}...")
            except EnvironmentError as e:
                self.signals.finished.emit(False,
                    "No Hugging Face token found. Please add HUGGING_FACE_API_KEY to the .env file.")
                return

            # Step 2: Check ffmpeg
            self.signals.progress.emit("Checking ffmpeg...", 10)
            import shutil
            if shutil.which("ffmpeg"):
                self.signals.log.emit("✓ ffmpeg found")
            else:
                self.signals.log.emit("⚠ ffmpeg not found — install with: brew install ffmpeg")
                self.signals.log.emit("  (needed for m4a/mp3 conversion)")

            # Step 3: Download whisper model
            self.signals.progress.emit("Downloading speech recognition model (~3 GB)...", 15)
            self.signals.log.emit("Downloading mlx-community/whisper-large-v3-mlx...")
            self.signals.log.emit("This may take 5-10 minutes on a typical connection.")
            from huggingface_hub import snapshot_download
            snapshot_download(
                "mlx-community/whisper-large-v3-mlx",
                token=token,
            )
            self.signals.log.emit("✓ Whisper model downloaded")
            self.signals.progress.emit("Speech recognition model ready", 50)

            # Step 4: Download Phi-3 model
            self.signals.progress.emit("Downloading summarization model (~2.2 GB)...", 55)
            self.signals.log.emit("Downloading mlx-community/Phi-3-mini-4k-instruct-4bit...")
            snapshot_download(
                "mlx-community/Phi-3-mini-4k-instruct-4bit",
                token=token,
            )
            self.signals.log.emit("✓ Phi-3 model downloaded")
            self.signals.progress.emit("Summarization model ready", 80)

            # Step 5: Download pyannote models
            self.signals.progress.emit("Downloading speaker identification models...", 85)
            self.signals.log.emit("Downloading pyannote models (gated — requires license acceptance)...")
            try:
                from pyannote.audio import Pipeline
                Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=token,
                )
                self.signals.log.emit("✓ Pyannote diarization model downloaded")
            except Exception as e:
                self.signals.log.emit(f"⚠ Pyannote download issue: {e}")
                self.signals.log.emit("  You may need to accept the license at:")
                self.signals.log.emit("  https://huggingface.co/pyannote/speaker-diarization-3.1")

            self.signals.progress.emit("Setup complete!", 100)
            self.signals.log.emit("\n✓ All models ready. You can now use Session Notes.")
            self.signals.finished.emit(True, "Setup complete!")

        except Exception as e:
            self.signals.finished.emit(False, f"Setup error: {e}")

    def _on_progress(self, message, percent):
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)

    def _on_log(self, message):
        self.log_display.append(message)

    def _on_finished(self, success, message):
        self.status_label.setText(message)
        if success:
            self.start_btn.hide()
            self.close_btn.show()
        else:
            self.start_btn.setEnabled(True)
            self.start_btn.setText("Retry Setup")


def needs_setup() -> bool:
    """Check if models are already cached."""
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    whisper_cached = any(cache_dir.glob("models--mlx-community--whisper-large-v3-mlx*"))
    phi3_cached = any(cache_dir.glob("models--mlx-community--Phi-3-mini-4k-instruct-4bit*"))
    return not (whisper_cached and phi3_cached)


def run_setup_if_needed():
    """Show setup dialog if models aren't downloaded yet. Returns True if ready."""
    if not needs_setup():
        return True

    app = QApplication.instance()
    standalone = app is None
    if standalone:
        app = QApplication(sys.argv)

    dialog = SetupDialog()
    result = dialog.exec()

    if standalone:
        pass  # Don't call app.exec() — dialog.exec() already ran the event loop

    return result == QDialog.DialogCode.Accepted


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SetupDialog()
    dialog.show()
    sys.exit(app.exec())
