
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import summary


class TestUpdateSummary(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.summary_path = Path(self.temp_dir.name) / "daily_summary.md"
        self.summary_path.write_text("Yesterday's summary", encoding="utf-8")
        self.path_patcher = patch.object(summary, "SUMMARY_PATH", self.summary_path)
        self.path_patcher.start()

    def tearDown(self):
        self.path_patcher.stop()
        self.temp_dir.cleanup()

    def test_success_replaces_old_summary(self):
        result = summary.update_summary(lambda: "Today's summary")

        self.assertEqual(result, "Today's summary")
        self.assertEqual(
            self.summary_path.read_text(encoding="utf-8"),
            "Today's summary",
        )

    def test_api_failure_preserves_old_summary(self):
        def failed_api_call():
            raise RuntimeError("API unavailable")

        result = summary.update_summary(failed_api_call)

        self.assertEqual(result, "Yesterday's summary")
        self.assertEqual(
            self.summary_path.read_text(encoding="utf-8"),
            "Yesterday's summary",
        )

    def test_empty_response_preserves_old_summary(self):
        result = summary.update_summary(lambda: "   ")

        self.assertEqual(result, "Yesterday's summary")
        self.assertEqual(
            self.summary_path.read_text(encoding="utf-8"),
            "Yesterday's summary",
        )


if __name__ == "__main__":
    unittest.main()
