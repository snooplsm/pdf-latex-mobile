import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from sizes import measure, write_report

class SizeTests(unittest.TestCase):
    def test_uses_actual_zip_and_per_abi_sizes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.aar"
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as aar:
                aar.writestr("jni/arm64-v8a/liblatex_mobile.so", b"x" * 1000)
                aar.writestr("jni/x86_64/liblatex_mobile.so", b"x" * 2000)
                aar.writestr("assets/texbundle/manifest.json", json.dumps({"features": ["text"], "bundle_sha256": "abc"}))
            result = measure(path)
            self.assertEqual(result["aar_bytes"], path.stat().st_size)
            self.assertEqual(result["native_bytes_by_abi"], {"arm64-v8a": 1000, "x86_64": 2000})
            self.assertEqual(len(result["sha256"]), 64)

    def test_missing_artifacts_are_not_estimated(self):
        with self.assertRaises(ValueError):
            write_report([], Path("unused"), Path("unused"))

if __name__ == "__main__":
    unittest.main()
