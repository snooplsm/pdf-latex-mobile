import json
from pathlib import Path
import tempfile
import unittest
from pack import select, safe_file, ROOT, disable_restricted_hyphenation

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

class HyphenationPolicyTests(unittest.TestCase):
    def test_disabled_languages_keep_identifiers_without_patterns(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "language.dat").write_text("english hyphen.tex\nczech loadhyph-cs.tex\n=czechalias\nindonesian loadhyph-id.tex\nmacedonian loadhyph-mk.tex\nlatvian loadhyph-lv.tex\narmenian loadhyph-hy.tex\ngerman loadhyph-de.tex\nnohyphenation zerohyph.tex\ndumylang dumyhyph.tex\n")
            for code in ("cs", "id", "mk", "lv", "hy", "de"):
                (root / f"hyph-{code}.tex").write_text("patterns")
                (root / f"loadhyph-{code}.tex").write_text("loader")
            disable_restricted_hyphenation(root)
            config = (root / "language.dat").read_text()
            self.assertEqual(config.count("lm-nohyphen.tex"), 7)
            self.assertIn("=czechalias", config)
            self.assertIn("german loadhyph-de.tex", config)
            self.assertTrue((root / "hyph-de.tex").exists())
            for code in ("cs", "id", "mk", "lv", "hy"):
                self.assertFalse((root / f"hyph-{code}.tex").exists())
                self.assertFalse((root / f"loadhyph-{code}.tex").exists())
            self.assertNotIn("\\patterns", (root / "lm-nohyphen.tex").read_text())
