import tempfile
import unittest
from pathlib import Path

from sample_data import get_sample_rows
from services.generator import excel_generator, pdf_generator


class GenernatorTests(unittest.TestCase):
    def test_excel_export_creates_folder_and_workbook(self):
        with tempfile.TemporaryDirectory() as temp_root:
            output_folder = Path(temp_root) / "reports"
            workbook_path = excel_generator(
                get_sample_rows(), output_folder, filename_prefix="Interview"
            )
            self.assertTrue(workbook_path.is_file())
            self.assertEqual(workbook_path.parent, output_folder)
            self.assertTrue(workbook_path.name.startswith("Interview_"))
            self.assertGreater(workbook_path.stat().st_size, 0)

            pdf_path = pdf_generator(workbook_path, get_sample_rows())
            self.assertTrue(pdf_path.is_file())
            self.assertEqual(pdf_path.read_bytes()[:5], b"%PDF-")


if __name__ == "__main__":
    unittest.main()
