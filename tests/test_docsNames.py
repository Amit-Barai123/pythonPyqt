import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from services.docsName import generate_path


class TestFilename(unittest.TestCase):
    def test_prefix_is_cleaned_and_filename_is_timestamped(self):
        with tempfile.TemporaryDirectory() as folder:
            path = generate_path(
                folder,
                "Interview Report",
                ".xlsx",
                now=datetime(2026, 11, 12, 10, 40, 0),
            )
            self.assertEqual(path.name, "Interview_Report_20261112_104000.xlsx")

    def test_existing_excel_or_pdf_gets_a_version_suffix(self):
        with tempfile.TemporaryDirectory() as folder:
            expected = Path(folder) / "Project_worksummary_20261112_104000.xlsx"
            expected.touch()
            (Path(folder) / "Project_worksummary_20261112_104000.pdf").touch()
            path = generate_path(
                folder,
                "Project_worksummary",
                ".xlsx",
                companion_extensions=(".pdf",),
                now=datetime(2026, 11, 12, 10, 40, 0),
            )
            self.assertEqual(path.name, "Project_worksummary_20261112_104000_2.xlsx")


if __name__ == "__main__":
    unittest.main()
