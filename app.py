"""Main desktop UI for the clinical note-taker."""

import sys
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QSpinBox, QMessageBox, QListWidget,
    QListWidgetItem, QStatusBar, QGroupBox, QFileDialog, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from recorder import Recorder
from pipeline import process_audio
from export import export_session_pdf
from feedback import thumbs_up, thumbs_down
from enroll import enroll_therapist, is_enrolled, get_therapist_name
from audio_utils import ensure_wav
from db import init_db, list_sessions, get_transcript, get_summary


class PipelineSignals(QObject):
    """Signals for communicating between the pipeline thread and the UI."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    status = pyqtSignal(str)


class EnrollSignals(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Session Notes — Clinical Note Taker")
        self.setMinimumSize(950, 750)

        self.recorder = Recorder()
        self.current_session_id = None
        self.pipeline_signals = PipelineSignals()
        self.pipeline_signals.finished.connect(self._on_pipeline_finished)
        self.pipeline_signals.error.connect(self._on_pipeline_error)
        self.pipeline_signals.status.connect(self._on_status_update)

        self.enroll_signals = EnrollSignals()
        self.enroll_signals.finished.connect(self._on_enroll_finished)
        self.enroll_signals.error.connect(self._on_enroll_error)

        self._build_ui()
        self._load_session_list()
        self._update_enrollment_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Left panel — session list + enrollment
        left_panel = QVBoxLayout()

        # Enrollment section
        enroll_group = QGroupBox("Therapist Voice")
        enroll_layout = QVBoxLayout(enroll_group)

        self.enroll_status_label = QLabel("Not enrolled")
        enroll_layout.addWidget(self.enroll_status_label)

        self.therapist_name_input = QLineEdit()
        self.therapist_name_input.setPlaceholderText("Therapist name (e.g., Olivia)")
        enroll_layout.addWidget(self.therapist_name_input)

        enroll_btn_layout = QHBoxLayout()

        self.enroll_record_btn = QPushButton("Record Voice Sample")
        self.enroll_record_btn.clicked.connect(self._toggle_enrollment_recording)
        enroll_btn_layout.addWidget(self.enroll_record_btn)

        self.enroll_file_btn = QPushButton("From File")
        self.enroll_file_btn.clicked.connect(self._enroll_from_file)
        enroll_btn_layout.addWidget(self.enroll_file_btn)

        enroll_layout.addLayout(enroll_btn_layout)
        left_panel.addWidget(enroll_group)

        # Session list
        left_panel.addWidget(QLabel("Sessions"))
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self._on_session_selected)
        left_panel.addWidget(self.session_list)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setMaximumWidth(280)

        # Right panel — recording controls + content
        right_panel = QVBoxLayout()

        # Recording controls
        controls_group = QGroupBox("Session Recording")
        controls_layout = QHBoxLayout(controls_group)

        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self._toggle_recording)
        self.record_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; }")
        controls_layout.addWidget(self.record_btn)

        self.load_file_btn = QPushButton("Load Audio File")
        self.load_file_btn.clicked.connect(self._load_audio_file)
        controls_layout.addWidget(self.load_file_btn)

        self.process_btn = QPushButton("Process")
        self.process_btn.clicked.connect(self._process_recording)
        self.process_btn.setEnabled(False)
        controls_layout.addWidget(self.process_btn)

        controls_layout.addWidget(QLabel("Summary words:"))
        self.word_target_spin = QSpinBox()
        self.word_target_spin.setRange(50, 100)
        self.word_target_spin.setValue(75)
        controls_layout.addWidget(self.word_target_spin)

        right_panel.addWidget(controls_group)

        # Transcript display
        right_panel.addWidget(QLabel("Transcript"))
        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        right_panel.addWidget(self.transcript_display)

        # Summary display
        right_panel.addWidget(QLabel("DAP Summary"))
        self.summary_display = QTextEdit()
        self.summary_display.setMaximumHeight(200)
        right_panel.addWidget(self.summary_display)

        # Feedback + export
        bottom_layout = QHBoxLayout()

        feedback_label = QLabel("Was this helpful?")
        bottom_layout.addWidget(feedback_label)

        self.thumbs_up_btn = QPushButton("👍")
        self.thumbs_up_btn.clicked.connect(lambda: self._give_feedback("up"))
        bottom_layout.addWidget(self.thumbs_up_btn)

        self.thumbs_down_btn = QPushButton("👎")
        self.thumbs_down_btn.clicked.connect(lambda: self._give_feedback("down"))
        bottom_layout.addWidget(self.thumbs_down_btn)

        bottom_layout.addStretch()

        self.export_btn = QPushButton("Export PDF")
        self.export_btn.clicked.connect(self._export_pdf)
        bottom_layout.addWidget(self.export_btn)

        right_panel.addLayout(bottom_layout)

        right_widget = QWidget()
        right_widget.setLayout(right_panel)

        # Assemble
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")

    # --- Enrollment ---

    def _update_enrollment_status(self):
        if is_enrolled():
            name = get_therapist_name()
            self.enroll_status_label.setText(f"Enrolled: {name}")
            self.enroll_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.therapist_name_input.setText(name)
        else:
            self.enroll_status_label.setText("Not enrolled — record a voice sample")
            self.enroll_status_label.setStyleSheet("color: orange;")

    def _toggle_enrollment_recording(self):
        if self.recorder.is_recording():
            audio_path, duration = self.recorder.stop()
            self.enroll_record_btn.setText("Record Voice Sample")
            self.enroll_record_btn.setStyleSheet("")
            if duration < 3:
                self.statusBar().showMessage("Recording too short — need at least 10 seconds")
                return
            self._run_enrollment(audio_path)
        else:
            audio_path = self.recorder.start()
            self.enroll_record_btn.setText("Stop Recording (speak for ~30s)")
            self.enroll_record_btn.setStyleSheet("background-color: #cc3333; color: white;")
            self.statusBar().showMessage("Recording therapist voice sample...")

    def _enroll_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Therapist Voice Sample",
            str(Path.home()),
            "Audio Files (*.wav *.m4a *.mp3 *.mp4 *.ogg *.flac);;All Files (*)",
        )
        if file_path:
            self._run_enrollment(file_path)

    def _run_enrollment(self, audio_path: str):
        name = self.therapist_name_input.text().strip() or "Therapist"
        self.statusBar().showMessage(f"Enrolling {name}'s voice...")
        self.enroll_record_btn.setEnabled(False)
        self.enroll_file_btn.setEnabled(False)

        def run():
            try:
                wav_path = ensure_wav(audio_path)
                enroll_therapist(wav_path, therapist_name=name)
                self.enroll_signals.finished.emit(name)
            except Exception as e:
                self.enroll_signals.error.emit(str(e))

        threading.Thread(target=run, daemon=True).start()

    def _on_enroll_finished(self, name: str):
        self.enroll_record_btn.setEnabled(True)
        self.enroll_file_btn.setEnabled(True)
        self._update_enrollment_status()
        self.statusBar().showMessage(f"Enrolled {name}'s voice successfully!")

    def _on_enroll_error(self, error_msg: str):
        self.enroll_record_btn.setEnabled(True)
        self.enroll_file_btn.setEnabled(True)
        self.statusBar().showMessage(f"Enrollment error: {error_msg}")
        QMessageBox.critical(self, "Enrollment Error", error_msg)

    # --- Session Recording ---

    def _toggle_recording(self):
        if self.recorder.is_recording():
            audio_path, duration = self.recorder.stop()
            self.record_btn.setText("Start Recording")
            self.record_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; }")
            self._last_audio_path = audio_path
            self._last_duration = duration
            self.process_btn.setEnabled(True)
            self.statusBar().showMessage(f"Recorded {duration:.0f}s — ready to process")
        else:
            audio_path = self.recorder.start()
            self._last_audio_path = audio_path
            self.record_btn.setText("Stop Recording")
            self.record_btn.setStyleSheet(
                "QPushButton { padding: 10px; font-size: 14px; background-color: #cc3333; color: white; }"
            )
            self.process_btn.setEnabled(False)
            self.statusBar().showMessage("Recording session...")

    def _load_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Session Audio",
            str(Path.home()),
            "Audio Files (*.wav *.m4a *.mp3 *.mp4 *.ogg *.flac);;All Files (*)",
        )
        if file_path:
            self._last_audio_path = file_path
            self.process_btn.setEnabled(True)
            self.statusBar().showMessage(f"Loaded: {Path(file_path).name}")

    def _process_recording(self):
        if not is_enrolled():
            reply = QMessageBox.warning(
                self, "No Voice Enrolled",
                "No therapist voice enrolled. Speaker identification will use a heuristic "
                "(first speaker = Therapist).\n\nContinue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.process_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.load_file_btn.setEnabled(False)
        self.statusBar().showMessage("Processing — this may take a while...")

        word_target = self.word_target_spin.value()
        audio_path = self._last_audio_path

        def run():
            try:
                result = process_audio(audio_path, word_target=word_target)
                self.pipeline_signals.finished.emit(result)
            except Exception as e:
                self.pipeline_signals.error.emit(str(e))

        threading.Thread(target=run, daemon=True).start()

    def _on_pipeline_finished(self, result: dict):
        self.current_session_id = result["session_id"]
        self._display_segments(result["segments"])
        self.summary_display.setPlainText(result["summary"])
        self.record_btn.setEnabled(True)
        self.load_file_btn.setEnabled(True)
        self.statusBar().showMessage(f"Session #{result['session_id']} processed successfully")
        self._load_session_list()

    def _on_pipeline_error(self, error_msg: str):
        self.record_btn.setEnabled(True)
        self.load_file_btn.setEnabled(True)
        self.process_btn.setEnabled(True)
        self.statusBar().showMessage(f"Error: {error_msg}")
        QMessageBox.critical(self, "Processing Error", error_msg)

    def _on_status_update(self, msg: str):
        self.statusBar().showMessage(msg)

    # --- Display ---

    def _display_segments(self, segments: list[dict]):
        self.transcript_display.clear()
        for seg in segments:
            mins = int(seg["start"] // 60)
            secs = int(seg["start"] % 60)
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "")
            self.transcript_display.append(f"[{speaker} {mins:02d}:{secs:02d}] {text}\n")

    def _on_session_selected(self, item: QListWidgetItem):
        session_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_session_id = session_id

        transcript = get_transcript(session_id)
        self.transcript_display.clear()
        for seg in transcript:
            mins = int(seg["start_time"] // 60)
            secs = int(seg["start_time"] % 60)
            self.transcript_display.append(
                f"[{seg['speaker']} {mins:02d}:{secs:02d}] {seg['text']}\n"
            )

        summary = get_summary(session_id)
        if summary:
            self.summary_display.setPlainText(summary["content"])
        else:
            self.summary_display.setPlainText("(No summary generated)")

    def _load_session_list(self):
        self.session_list.clear()
        for session in list_sessions():
            date_str = session["created_at"][:16].replace("T", " ")
            duration_mins = round(session.get("duration_seconds", 0) / 60, 1)
            label = f"#{session['id']} — {date_str} ({duration_mins}m)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, session["id"])
            self.session_list.addItem(item)

    # --- Feedback ---

    def _give_feedback(self, rating: str):
        if not self.current_session_id:
            return
        if rating == "up":
            thumbs_up("summary", session_id=self.current_session_id)
        else:
            thumbs_down("summary", session_id=self.current_session_id)
        self.statusBar().showMessage("Feedback recorded — thank you!")

    # --- Export ---

    def _export_pdf(self):
        if not self.current_session_id:
            QMessageBox.warning(self, "No Session", "Select or record a session first.")
            return
        try:
            path = export_session_pdf(self.current_session_id)
            self.statusBar().showMessage(f"Exported to {path}")
            QMessageBox.information(self, "Export Complete", f"PDF saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # First-run: download models if needed
    from first_run_setup import needs_setup, SetupDialog
    if needs_setup():
        dialog = SetupDialog()
        result = dialog.exec()
        if result != SetupDialog.DialogCode.Accepted:
            sys.exit(0)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
