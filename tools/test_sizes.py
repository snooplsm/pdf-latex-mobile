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
                aar.writestr("jni/armeabi-v7a/liblatex_mobile.so", b"x" * 500)
                aar.writestr("jni/arm64-v8a/liblatex_mobile.so", b"x" * 1000)
                aar.writestr("jni/x86_64/liblatex_mobile.so", b"x" * 2000)
                aar.writestr("assets/texbundle/manifest.json", json.dumps({"features": ["text"], "bundle_sha256": "abc"}))
            result = measure(path)
            self.assertEqual(result["aar_bytes"], path.stat().st_size)
            self.assertEqual(result["native_bytes_by_abi"], {"armeabi-v7a": 500, "arm64-v8a": 1000, "x86_64": 2000})
            self.assertEqual(len(result["sha256"]), 64)
            split_root = Path(directory) / "splits"
            split = split_root / "arm64-v8a" / path.name
            split.parent.mkdir(parents=True)
            with zipfile.ZipFile(path) as original, zipfile.ZipFile(split, "w", zipfile.ZIP_DEFLATED) as target:
                for entry in original.infolist():
                    if not entry.filename.startswith("jni/") or entry.filename.startswith("jni/arm64-v8a/"):
                        target.writestr(entry.filename, original.read(entry))
            report = Path(directory) / "sizes.md"
            metadata = Path(directory) / "sizes.json"
            write_report([path], report, metadata, split_root)
            saved = json.loads(metadata.read_text())
            self.assertEqual(saved["single_abi_artifacts"][path.name]["arm64-v8a"]["aar_bytes"], split.stat().st_size)
            with zipfile.ZipFile(split, "a") as target:
                target.writestr("jni/x86_64/extra.so", b"unexpected")
            with self.assertRaises(ValueError):
                write_report([path], report, metadata, split_root)

    def test_missing_artifacts_are_not_estimated(self):
        with self.assertRaises(ValueError):
            write_report([], Path("unused"), Path("unused"))

if __name__ == "__main__":
    unittest.main()
