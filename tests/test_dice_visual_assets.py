from __future__ import annotations

import hashlib
import json
import re
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DiceVisualAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / "assets/candidates/042/generation.json").read_text(encoding="utf-8"))
        cls.entries = cls.catalog["images"]

    def test_three_materials_have_two_candidates_and_a_matched_cracked_variant(self):
        self.assertEqual(len(self.entries), 10)
        by_id = {entry["id"]: entry for entry in self.entries}
        for material in ("bone", "ruby", "iron"):
            for variant in ("01", "02", "cracked"):
                entry = by_id[f"dice_{material}_{variant}"]
                path = ROOT / entry["file"]
                header = path.read_bytes()[:33]
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", header[16:24]), (512, 512))
                self.assertEqual(header[24:26], bytes([8, 6]), "8-bit RGBA required")
            self.assertEqual(by_id[f"dice_{material}_cracked"]["reference_images"],
                             [by_id[f"dice_{material}_01"]["original"]])
            self.assertNotEqual((ROOT / by_id[f"dice_{material}_01"]["file"]).read_bytes(),
                                (ROOT / by_id[f"dice_{material}_cracked"]["file"]).read_bytes())
        tray = (ROOT / by_id["dice_tray"]["file"]).read_bytes()
        self.assertEqual(struct.unpack(">II", tray[16:24]), (800, 400))
        self.assertEqual(tray[24:26], bytes([8, 6]))

    def test_runtime_webp_has_alpha_correct_dimensions_and_stays_under_budget(self):
        runtime = [ROOT / entry["runtime"] for entry in self.entries if entry.get("runtime")]
        self.assertEqual(len(runtime), 7)
        for path in runtime:
            with self.subTest(path=path.name):
                header = path.read_bytes()[:30]
                self.assertEqual(header[:4], b"RIFF")
                self.assertEqual(header[8:16], b"WEBPVP8X")
                self.assertTrue(header[20] & 0x10, "WebP transparency must be retained")
                size = (1 + int.from_bytes(header[24:27], "little"), 1 + int.from_bytes(header[27:30], "little"))
                self.assertEqual(size, (800, 400) if path.stem == "dice_tray" else (512, 512))
        total = sum(path.stat().st_size for path in runtime)
        self.assertEqual(total, self.catalog["runtime_bytes"])
        self.assertLess(total, 1_500_000)
        css = (ROOT / "client/styles.css").read_text(encoding="utf-8")
        referenced = set(re.findall(r"/static/images/(dice_[a-z_]+\.webp)", css))
        self.assertEqual(referenced, {path.name for path in runtime})

    def test_manifest_registers_artifacts_with_only_selected_ruby_images_approved(self):
        manifest = json.loads((ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
        records = {entry["file"]: entry for entry in manifest["images"] if entry.get("task") == "042"}
        self.assertEqual(len(records), 27)
        for entry in self.entries:
            self.assertTrue(entry["prompt"])
            self.assertIn(entry["original"], records)
            self.assertIn(entry["file"], records)
            for artifact in entry["artifacts"]:
                with self.subTest(file=artifact["file"]):
                    record = records[artifact["file"]]
                    data = (ROOT / artifact["file"]).read_bytes()
                    selected = entry["id"] in {"dice_ruby_01", "dice_ruby_cracked"}
                    self.assertEqual(record["approved"], selected)
                    if selected:
                        self.assertEqual(record["selection_reason"], "设计负责人定稿")
                    self.assertEqual(record["bytes"], len(data))
                    self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())
                    self.assertEqual(record["alpha_extrema"], [0, 255])
                    self.assertEqual(record["prompt"], entry["prompt"])
        self.assertEqual(manifest["batches"]["042"]["default"], "client/images/dice_ruby.webp")


if __name__ == "__main__":
    unittest.main()
