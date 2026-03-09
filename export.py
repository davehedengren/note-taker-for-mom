"""Export session notes as PDF."""

from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from db import get_session, get_transcript, get_summary

EXPORT_DIR = Path.home() / ".note-taker-for-mom" / "exports"


def export_session_pdf(session_id: int, output_path: str = None) -> str:
    """Export a session's transcript and DAP summary as a PDF.

    Args:
        session_id: The session to export.
        output_path: Optional custom path. Defaults to exports directory.

    Returns:
        Path to the generated PDF.
    """
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    transcript = get_transcript(session_id)
    summary = get_summary(session_id)

    if output_path is None:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(EXPORT_DIR / f"session_{session_id}_{timestamp}.pdf")

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle("Header", parent=styles["Heading1"], fontSize=16)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=13)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    speaker_style = ParagraphStyle("Speaker", parent=styles["Normal"], fontSize=10,
                                   leading=14, leftIndent=12)

    elements = []

    # Header
    elements.append(Paragraph("Therapy Session Notes", header_style))
    elements.append(Paragraph(f"Session Date: {session['created_at'][:10]}", body_style))
    duration_mins = round(session.get("duration_seconds", 0) / 60, 1)
    elements.append(Paragraph(f"Duration: {duration_mins} minutes", body_style))
    elements.append(Spacer(1, 0.3 * inch))

    # DAP Summary
    if summary:
        elements.append(Paragraph("DAP Summary", section_style))
        elements.append(Spacer(1, 0.1 * inch))
        # Preserve line breaks in summary
        for line in summary["content"].splitlines():
            if line.strip():
                elements.append(Paragraph(line, body_style))
                elements.append(Spacer(1, 0.05 * inch))
        elements.append(Spacer(1, 0.2 * inch))

    # Transcript
    if transcript:
        elements.append(Paragraph("Session Transcript", section_style))
        elements.append(Spacer(1, 0.1 * inch))
        for seg in transcript:
            mins = int(seg["start_time"] // 60)
            secs = int(seg["start_time"] % 60)
            line = f"<b>[{seg['speaker']} {mins:02d}:{secs:02d}]</b> {seg['text']}"
            elements.append(Paragraph(line, speaker_style))
            elements.append(Spacer(1, 0.03 * inch))

    # Footer note
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        "<i>CONFIDENTIAL — This document contains protected health information.</i>",
        body_style,
    ))

    doc.build(elements)
    return output_path
