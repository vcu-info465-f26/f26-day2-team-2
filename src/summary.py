
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

SUMMARY_PATH = Path(__file__).resolve().parent / "daily_summary.md"


def load_summary():
    """Return the previously saved summary, or an empty string."""
    try:
        return SUMMARY_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def update_summary(generate_summary):
    """Save a new summary only when generation succeeds with valid content."""
    previous_summary = load_summary()

    try:
        new_summary = generate_summary()

        if not isinstance(new_summary, str) or not new_summary.strip():
            logger.warning("Summary response was empty or invalid.")
            return previous_summary

        temp_path = SUMMARY_PATH.with_suffix(".tmp")
        temp_path.write_text(new_summary, encoding="utf-8")
        temp_path.replace(SUMMARY_PATH)

        return new_summary

    except Exception:
        logger.exception(
            "Summary generation failed; preserving the previous summary."
        )
        return previous_summary
