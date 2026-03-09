"""Simple feedback system — thumbs up/down per feature area."""

from db import save_feedback, get_connection


def thumbs_up(feature_area: str, session_id: int = None, comment: str = None):
    save_feedback(feature_area, "up", session_id=session_id, comment=comment)


def thumbs_down(feature_area: str, session_id: int = None, comment: str = None):
    save_feedback(feature_area, "down", session_id=session_id, comment=comment)


def get_feedback_summary() -> dict:
    """Get aggregate feedback stats per feature area.

    Returns:
        {"transcription": {"up": 12, "down": 3}, "summary": {"up": 8, "down": 5}, ...}
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT feature_area, rating, COUNT(*) as count FROM feedback GROUP BY feature_area, rating"
    ).fetchall()
    conn.close()

    summary = {}
    for row in rows:
        area = row["feature_area"]
        if area not in summary:
            summary[area] = {"up": 0, "down": 0}
        summary[area][row["rating"]] = row["count"]

    return summary
