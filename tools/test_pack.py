import json
from pathlib import Path
import tempfile
import unittest
from pack import select, safe_file, ROOT

class PackTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "profiles/features.json").read_text())

    def test_exclusion_and_inclusion(self):
        self.assertEqual(select(self.config, "balanced", ["fonts"], ["graphics"]), ["core", "fonts", "invoice", "math", "text"])
        with self.assertRaises(ValueError):
            select(self.config, "small", exclude=["core"])
        with self.assertRaises(ValueError):
            select(self.config, "small", exclude=["typo"])

    def test_escape_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "ok.sty").write_text("data")
            (root / "link.sty").symlink_to(root / "ok.sty")
            self.assertEqual(safe_file(root, "ok.sty"), root / "ok.sty")
            for name in ["../ok.sty", "/ok.sty", "..", "link.sty", "a\\b"]:
                with self.assertRaises(ValueError):
                    safe_file(root, name)

if __name__ == "__main__":
    unittest.main()
