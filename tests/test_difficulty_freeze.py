"""Baby is immutable: balance specs must NOT update its numeric snapshot.

Only tasks explicitly authorizing "adjust baby" may change existing values.
Shared new numeric fields require an explicit snapshot update and commit note.
The 047 retry brief places fixtures under host/prompt/processed/difficulty/.
"""
from __future__ import annotations

import json
import subprocess
import unittest
import warnings
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from host.difficulty import (
    NON_BALANCE_FIELDS, NUMERIC_FIELDS, _leaves, _matches, _numeric,
    apply_difficulty, numeric_snapshot, overlay_fingerprint,
)

ROOT = Path.cwd()
PACK_ROOT = ROOT / "host/prompt/processed"
FIXTURES = PACK_ROOT / "difficulty"


class DifficultyFreezeTests(unittest.TestCase):
    def test_baby_numeric_values_and_field_set_are_frozen(self):
        frozen = json.loads((FIXTURES / "baby_numeric_freeze.json").read_text(encoding="utf-8"))
        for name, expected in frozen.items():
            with self.subTest(pack=name), warnings.catch_warnings():
                warnings.simplefilter("error")
                pack = json.loads((PACK_ROOT / name).read_text(encoding="utf-8"))
                actual = numeric_snapshot(apply_difficulty(pack, "baby"))
                self.assertEqual(actual, expected)
                count = lambda snapshot: sum(len(values) for records in snapshot.values() for values in records.values())
                self.assertEqual(count(actual), count(expected))
                if not pack["difficulty_overlays"]["normal"]:
                    self.assertEqual(apply_difficulty(pack, "normal"), apply_difficulty(pack, "baby"))
                if pack["meta"]["content_revision"] == "2026-10-20-difficulty-047":
                    self.assertEqual(pack["difficulty_overlays"], {"normal": []})

    def test_no_unclassified_numeric_leaves(self):
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads((PACK_ROOT / name).read_text(encoding="utf-8"))
            unknown = []
            for group, records in pack.items():
                if group in ("meta", "difficulty_overlays"):
                    continue
                for record in records if isinstance(records, list) else [records]:
                    for path, pattern, value in _leaves(record):
                        if not _numeric(value) or path.split(".")[-1] in ("id", "name", "attribute"):
                            continue
                        absolute = group + (".*." if isinstance(records, list) else ".") + pattern
                        if any(_matches(absolute, excluded) for excluded in NON_BALANCE_FIELDS):
                            continue
                        if not any(_matches(pattern, allowed) for allowed in NUMERIC_FIELDS.get(group, ())):
                            unknown.append(absolute)
            self.assertEqual(unknown, [], name)

    def test_overlay_changes_require_revision_bump(self):
        guard = json.loads((FIXTURES / "overlay_revision.json").read_text(encoding="utf-8"))
        for name, previous in guard.items():
            pack = json.loads((PACK_ROOT / name).read_text(encoding="utf-8"))
            if overlay_fingerprint(pack) != previous["overlay_sha256"]:
                self.assertGreater(pack["meta"]["content_revision"], previous["content_revision"], name)
            self.assertEqual(overlay_fingerprint(pack), previous["overlay_sha256"],
                             "Record the accepted overlay hash together with its new revision")
            self.assertEqual(pack["meta"]["content_revision"], previous["content_revision"])
            # Worktree and committed changes are both checked, without touching the index.
            for ref in ("HEAD", "HEAD^"):
                source = subprocess.run(
                    ["git", "show", f"{ref}:host/prompt/processed/{name}"],
                    capture_output=True, encoding="utf-8",
                )
                if source.returncode:
                    continue
                prior = json.loads(source.stdout)
                if overlay_fingerprint(pack) != overlay_fingerprint(prior):
                    self.assertGreater(pack["meta"]["content_revision"], prior["meta"]["content_revision"], name)

    def test_revision_guard_rejects_changed_overlay_even_with_updated_manifest(self):
        names = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
        baseline = {name: json.loads((PACK_ROOT / name).read_text(encoding="utf-8")) for name in names}
        edited = deepcopy(baseline)
        for pack in edited.values():
            pack["difficulty_overlays"]["normal"] = [
                {"entity": "enemies", "id": pack["enemies"][0]["id"], "path": "hp", "add": 1},
            ]
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            if path == FIXTURES / "overlay_revision.json":
                return json.dumps({name: {
                    "content_revision": pack["meta"]["content_revision"],
                    "overlay_sha256": overlay_fingerprint(pack),
                } for name, pack in edited.items()})
            if path.parent == PACK_ROOT and path.name in edited:
                return json.dumps(edited[path.name])
            return original_read(path, *args, **kwargs)

        def git_source(command, **kwargs):
            name = command[-1].rsplit("/", 1)[-1]
            return SimpleNamespace(returncode=0, stdout=json.dumps(baseline[name]))

        with patch.object(Path, "read_text", read), patch.object(subprocess, "run", side_effect=git_source):
            with self.assertRaises(AssertionError):
                self.test_overlay_changes_require_revision_bump()
            for pack in edited.values():
                pack["meta"]["content_revision"] = "2099-01-01-test"
            self.test_overlay_changes_require_revision_bump()


if __name__ == "__main__":
    unittest.main()
