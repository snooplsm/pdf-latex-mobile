import runpy
from pathlib import Path
import tempfile
import unittest

compare = runpy.run_path(str(Path(__file__).with_name("mobile-parity.py")))["compare"]

class ParityTests(unittest.TestCase):
    def test_requires_four_identical_raw_pdfs(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = {}
            for name in ("android-1", "android-2", "ios-1", "ios-2"):
                path = Path(directory) / (name + ".pdf")
                path.write_bytes(b"%PDF-1.5\nidentical bytes\n%%EOF\n")
                paths[name] = path
            self.assertEqual(len(set(compare(paths).values())), 1)
            paths["ios-2"].write_bytes(b"%PDF-1.5\none different byte\n%%EOF\n")
            with self.assertRaises(ValueError):
                compare(paths)
            paths["ios-2"].write_bytes(b"not a PDF")
            with self.assertRaises(ValueError):
                compare(paths)
            with self.assertRaises(ValueError):
                compare({"android-1": paths["android-1"]})
