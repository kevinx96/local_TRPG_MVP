from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from host.difficulty import overlay_fingerprint
from scripts.scenario import combat_mechanics_v2, holy_sword_049, levels_skills_v2, normal_tuning_052, spring_postgame


class OverlayRevisionNewlineTests(unittest.TestCase):
    def test_migration_manifests_are_utf8_lf_and_repeatable(self):
        modules = (levels_skills_v2, combat_mechanics_v2, spring_postgame, holy_sword_049, normal_tuning_052)
        for module in modules:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                processed = root / "host/prompt/processed"
                (processed / "difficulty").mkdir(parents=True)
                pack = {"meta": {"content_revision": "test"}, "difficulty_overlays": {"normal": []}}
                names = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
                for name in names:
                    (processed / name).write_bytes(json.dumps(pack).encode("utf-8"))
                revisions = {name: {"content_revision": "test", "overlay_sha256": overlay_fingerprint(pack)}
                             for name in names}
                manifest = processed / "difficulty/overlay_revision.json"
                manifest.write_bytes((json.dumps(revisions, indent=2) + "\n").replace("\n", "\r\n").encode("utf-8"))
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(module, "ROOT", root))
                    stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                    if module is spring_postgame:
                        stack.enter_context(patch.object(module, "apply", return_value=None))
                        stack.enter_context(patch("sys.argv", ["spring_postgame"]))
                        for entry in revisions.values():
                            entry["content_revision"] = "2026-10-21-guidance-048"
                    else:
                        stack.enter_context(patch.object(module, "migrate", side_effect=lambda value: value))
                    module.main()
                    first = manifest.read_bytes()
                    module.main()
                self.assertEqual(manifest.read_bytes(), first)
                self.assertNotIn(b"\r", first)
                self.assertFalse(first.startswith(b"\xef\xbb\xbf"))
                self.assertTrue(first.endswith(b"\n"))
                self.assertEqual(json.loads(first), revisions)


if __name__ == "__main__":
    unittest.main()
