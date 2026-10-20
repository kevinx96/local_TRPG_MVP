from __future__ import annotations

import json
import shutil
import subprocess
import unittest
import uuid
import warnings
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from host import app, difficulty, state
from host.scenario_context import load_scenario_pack, normalize_scenario_pack, select_scenario_context
from scripts.scenario.difficulty_modes import migrate

ROOT = Path.cwd()
PACK_ROOT = ROOT / "host/prompt/processed"


def sample():
    return {
        "combat_rules": {"flee_dc": 12},
        "enemies": [
            {"id": "a", "hp": 10, "combat": {"basic_attack": {"damage": "1d6"}},
             "skills": [{"id": "hit", "cost": 2}, {"id": "heal", "cost": 3}]},
            {"id": "b", "hp": 20},
        ],
        "difficulty_overlays": {"normal": []},
    }


def overlay(entity="enemies", identifier="a", path="hp", **operation):
    return {"entity": entity, "id": identifier, "path": path, **operation}


class DifficultyTests(unittest.TestCase):
    def setUp(self):
        self.warnings = warnings.catch_warnings()
        self.warnings.__enter__()
        warnings.simplefilter("error", RuntimeWarning)
        self.addCleanup(self.warnings.__exit__, None, None, None)

    def test_empty_layer_identity_and_deep_copy(self):
        pack = sample()
        for mode in ("baby", "normal"):
            result = difficulty.apply_difficulty(pack, mode)
            self.assertEqual(result, pack)
            result["enemies"][0]["hp"] = 1
            self.assertEqual(pack["enemies"][0]["hp"], 10)

    def test_overlay_operations_and_id_addressing_after_reorder(self):
        pack = sample()
        pack["difficulty_overlays"]["normal"] = [
            overlay(set=7),
            overlay(identifier="b", mul=2),
            overlay(path="skills.@id=heal.cost", add=4),
            overlay(path="combat.basic_attack.damage", set="1d12+str/3"),
        ]
        pack["enemies"].reverse()
        pack["enemies"][1]["skills"].reverse()
        before = deepcopy(pack)
        actual = difficulty.apply_difficulty(pack, "normal")
        self.assertEqual(actual["enemies"][0]["hp"], 40)
        self.assertEqual(actual["enemies"][1]["hp"], 7)
        self.assertEqual(actual["enemies"][1]["skills"][0]["cost"], 7)
        self.assertEqual(actual["enemies"][1]["combat"]["basic_attack"]["damage"], "1d12+str/3")
        self.assertEqual(pack, before)
        self.assertEqual(difficulty.apply_difficulty(pack, "baby"), pack)

    def test_unknown_modes(self):
        for mode in ("", "hard", "NORMAL", None, [], 1):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                difficulty.apply_difficulty(sample(), mode)

    def test_reject_invalid_addresses_operations_and_values(self):
        invalid = [
            overlay(entity="unknown", set=1), overlay(identifier="missing", set=1),
            overlay(path="mp", set=1), overlay(path="combat.absent.damage", set="1d8"),
            overlay(path="id", set="b"), overlay(path="combat.basic_attack.name", set="攻撃"),
            overlay(path="skills", set=[]), overlay(path="skills.0.cost", set=1),
            overlay(path="skills.@id=missing.cost", set=1),
            overlay(path="skills.@id=heal.description", set="説明"),
            overlay(set=True), overlay(set="説明"), overlay(set=float("nan")),
            overlay(add=float("inf")), overlay(add="2"), overlay(set=1, add=1),
            overlay(delete=True), overlay(),
            overlay(path="combat.basic_attack.damage", mul=2),
        ]
        for entry in invalid:
            with self.subTest(entry=entry):
                pack = sample()
                pack["difficulty_overlays"]["normal"] = [entry]
                for mode in ("normal", "baby"):
                    with self.assertRaises(ValueError):
                        difficulty.apply_difficulty(pack, mode)
                with self.assertRaises(ValueError):
                    normalize_scenario_pack(pack)

    def test_reject_ambiguous_ids_and_nested_selectors(self):
        pack = sample()
        pack["enemies"].append(deepcopy(pack["enemies"][0]))
        pack["difficulty_overlays"]["normal"] = [overlay(set=1)]
        with self.assertRaises(ValueError):
            difficulty.apply_difficulty(pack, "normal")
        pack = sample()
        pack["enemies"][0]["skills"].append({"id": "heal", "cost": 8})
        pack["difficulty_overlays"]["normal"] = [overlay(path="skills.@id=heal.cost", set=1)]
        with self.assertRaises(ValueError):
            difficulty.apply_difficulty(pack, "normal")

    def test_repeated_destination_warns_and_applies_in_order(self):
        pack = sample()
        pack["difficulty_overlays"]["normal"] = [overlay(add=2), overlay(mul=3)]
        with self.assertRaises(RuntimeWarning):
            difficulty.validate_difficulty(pack)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", RuntimeWarning)
            result = difficulty.apply_difficulty(pack, "normal")
        self.assertEqual(len(caught), 1)
        self.assertEqual(result["enemies"][0]["hp"], 36)
        pack["difficulty_overlays"]["normal"] = [
            overlay(path="combat.basic_attack.damage", set=5),
            overlay(path="combat.basic_attack.damage", add=2),
        ]
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always", RuntimeWarning)
            result = difficulty.apply_difficulty(pack, "normal")
        self.assertEqual(result["enemies"][0]["combat"]["basic_attack"]["damage"], 7)

    def test_mechanic_channel_can_create_only_authorized_leaf(self):
        pack = sample()
        pack["difficulty_overlays"]["normal"] = [overlay("combat_rules", "$", "evade_model", set="dex")]
        self.assertIn("evade_model", difficulty.MECHANIC_FIELDS["combat_rules"])
        self.assertEqual(difficulty.apply_difficulty(pack, "normal")["combat_rules"]["evade_model"], "dex")
        with patch.dict(difficulty.MECHANIC_FIELDS, {"combat_rules": {"evade_model": ("legacy", "dex")}}):
            result = difficulty.apply_difficulty(pack, "normal")
            self.assertEqual(result["combat_rules"]["evade_model"], "dex")
            self.assertNotIn("evade_model", difficulty.apply_difficulty(pack, "baby")["combat_rules"])
            pack["difficulty_overlays"]["normal"][0]["set"] = "説明"
            with self.assertRaises(ValueError):
                difficulty.apply_difficulty(pack, "normal")
        with patch.dict(difficulty.MECHANIC_FIELDS, {"combat_rules": {"absent.evade_model": ("dex",)}}):
            pack["difficulty_overlays"]["normal"] = [overlay("combat_rules", "$", "absent.evade_model", set="dex")]
            with self.assertRaises(ValueError):
                difficulty.apply_difficulty(pack, "normal")

    def test_named_and_anonymous_effect_paths_survive_reordering(self):
        pack = {"companions": [{"id": "ally", "round_start_effects": [
            {"kind": "heal_player", "amount": 3}, {"kind": "damage_enemy", "name": "援護", "damage": "1d6"},
        ]}], "difficulty_overlays": {"normal": []}}
        addresses = difficulty.numeric_snapshot(pack)["companions"]["ally"]
        for path, value in addresses.items():
            pack["difficulty_overlays"]["normal"].append(overlay("companions", "ally", path, set=8 if isinstance(value, int) else "2d6"))
        pack["companions"][0]["round_start_effects"].reverse()
        result = difficulty.apply_difficulty(pack, "normal")
        self.assertEqual(result["companions"][0]["round_start_effects"][0]["damage"], "2d6")
        self.assertEqual(result["companions"][0]["round_start_effects"][1]["amount"], 8)

    def test_future_exp_table_is_covered(self):
        pack = {"progression": {"exp_table": {"2": 20, "3": 50}}, "difficulty_overlays": {"normal": [
            overlay("progression", "$", "exp_table.2", add=10),
        ]}}
        self.assertEqual(difficulty.numeric_snapshot(pack)["progression"]["$"]["exp_table.2"], 20)
        self.assertEqual(difficulty.apply_difficulty(pack, "normal")["progression"]["exp_table"]["2"], 30)
        self.assertEqual(normalize_scenario_pack(pack)["progression"], pack["progression"])

    def test_migration_is_idempotent_preserves_base_and_both_packs(self):
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads((PACK_ROOT / name).read_text(encoding="utf-8"))
            original = deepcopy(pack)
            original["meta"].pop("difficulty")
            original.pop("difficulty_overlays")
            original["meta"]["content_revision"] = "2026-10-19-ruby-045-npc-combat"
            frozen = deepcopy(original)
            migrated = migrate(original)
            self.assertEqual(original, frozen)
            expected = deepcopy(pack)
            expected["difficulty_overlays"] = {"normal": []}
            expected["meta"]["content_revision"] = "2026-10-20-difficulty-047"
            self.assertEqual(migrated, expected)
            self.assertEqual(migrate(migrated), migrated)
            self.assertEqual(difficulty.numeric_snapshot(original), difficulty.numeric_snapshot(migrated))

    def test_every_frozen_address_resolves_and_preserves_its_value(self):
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads((PACK_ROOT / name).read_text(encoding="utf-8"))
            pack["difficulty_overlays"]["normal"] = [
                overlay(group, identifier, path, set=value)
                for group, records in difficulty.numeric_snapshot(pack).items()
                for identifier, values in records.items()
                for path, value in values.items()
            ]
            self.assertEqual(difficulty.apply_difficulty(pack, "normal"), pack, name)


class DifficultySessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = ROOT / ".tmp-test" / ("difficulty-" + uuid.uuid4().hex)
        self.tmp.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        save_patch = patch.object(state, "SAVE_DIR", self.tmp)
        save_patch.start()
        self.addCleanup(save_patch.stop)
        self.pack = load_scenario_pack(PACK_ROOT / "dragon_rpg.json")

    def create(self, mode=None):
        return state.create_session(str(PACK_ROOT / "dragon_rpg.json"), character_id="hero", gm_mode="full", difficulty=mode)

    def test_new_default_normal_explicit_baby_and_public_labels(self):
        for requested, expected in ((None, "normal"), ("normal", "normal"), ("baby", "baby")):
            public = self.create(requested)
            self.assertEqual(public["difficulty"], expected)
            self.assertEqual(public["difficulty_label"], difficulty.DIFFICULTY_LABELS[expected])
            saved = state.load_session(public["id"])
            self.assertEqual(saved["difficulty"], expected)
            self.assertEqual(saved["scenario_pack"], difficulty.apply_difficulty(self.pack, expected))

    def test_invalid_api_value_is_400_before_opening(self):
        for mode in ("", "hard"):
            with self.assertRaises(ValueError):
                self.create(mode)
            with patch.object(app, "_run_opening") as opening:
                with self.assertRaises(HTTPException) as caught:
                    app.api_create_session(app.CreateSessionRequest(difficulty=mode))
                self.assertEqual(caught.exception.status_code, 400)
                opening.assert_not_called()

    def test_new_session_uses_effective_character_template(self):
        self.pack["difficulty_overlays"]["normal"] = [overlay("characters", "hero", "max_hp", set=99)]
        with patch.object(state, "load_scenario_pack", return_value=self.pack):
            normal, baby = self.create("normal"), self.create("baby")
        self.assertEqual(normal["character"]["max_hp"], 99)
        self.assertNotEqual(baby["character"]["max_hp"], 99)

    def test_legacy_save_is_persisted_baby_without_reapplying_snapshot(self):
        public = self.create()
        saved_path = self.tmp / (public["id"] + ".json")
        saved = json.loads(saved_path.read_text(encoding="utf-8"))
        saved.pop("difficulty")
        saved["scenario_pack"]["enemies"][0]["hp"] = 321
        saved["scenario_pack"]["difficulty_overlays"]["normal"] = [overlay(identifier=saved["scenario_pack"]["enemies"][0]["id"], path="hp", add=100)]
        state.save_session(saved)
        actual = state.load_session(public["id"])
        self.assertEqual(actual["difficulty"], "baby")
        self.assertEqual(actual["scenario_pack"], saved["scenario_pack"])
        self.assertEqual(json.loads(saved_path.read_text(encoding="utf-8"))["difficulty"], "baby")
        self.assertEqual(state.public_session(actual)["difficulty_label"], "やさしい")

    def test_refresh_keeps_mode_and_compares_effective_items(self):
        for mode in ("baby", "normal"):
            public = self.create(mode)
            session = state.load_session(public["id"])
            old = deepcopy(self.pack)
            old["difficulty_overlays"]["normal"] = [overlay("items", "iron_sword", "combat.damage", set="2d6")]
            session["scenario_pack"] = difficulty.apply_difficulty(old, mode)
            sword = next(item for item in session["scenario_pack"]["items"] if item["id"] == "iron_sword")
            session["character"]["inventory"] = [deepcopy(sword)]
            original_actor = deepcopy(session["character"])
            session["area_snapshots"] = {"test": {"state": {"character": deepcopy(original_actor)}}}
            latest = deepcopy(old)
            latest["meta"]["content_revision"] = "2099-01-01-test"
            # Change only normal: baby equipment stays byte-for-byte equal.
            latest["difficulty_overlays"]["normal"][0]["set"] = "3d6"
            with patch.object(state, "load_scenario_pack", return_value=latest):
                self.assertTrue(state._refresh_session_scenario_pack(session))
                self.assertFalse(state._refresh_session_scenario_pack(session))
            self.assertEqual(session["difficulty"], mode)
            self.assertEqual(session["scenario_pack"], difficulty.apply_difficulty(latest, mode))
            expected = "3d6" if mode == "normal" else sword["combat"]["damage"]
            self.assertEqual(session["character"]["inventory"][0]["combat"]["damage"], expected)
            self.assertEqual(session["area_snapshots"]["test"]["state"]["character"]["inventory"][0]["combat"]["damage"], expected)

    def test_no_difficulty_in_model_context(self):
        session = state.load_session(self.create()["id"])
        for mode in ("semi", "full"):
            session["gm_mode"] = mode
            text = json.dumps(state.build_llm_messages(session, {}, "契約"), ensure_ascii=False)
            self.assertNotIn('"difficulty"', text)
            self.assertNotIn("difficulty_overlays", text)
        self.assertNotIn("difficulty", select_scenario_context(session)["meta"])

    def test_editor_save_roundtrip_retains_both_keys(self):
        filename = "scenario.json"
        pack = deepcopy(self.pack)
        pack["difficulty_overlays"]["normal"] = [overlay("items", "iron_sword", "combat.damage", set="2d6")]
        with patch.object(app, "PROCESSED_SCENARIO_DIR", self.tmp):
            app.api_create_scenario(app.ScenarioCreateRequest(filename=filename, scenario=pack))
            loaded = app.api_get_scenario(filename)["scenario"]
            editor_source = (ROOT / "client/editor.js").read_text(encoding="utf-8").replace("init();", "", 1)
            # Exercise the actual editor's load/save shaping before the API roundtrip.
            javascript = """
const vm = require('node:vm');
const fs = require('node:fs');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = {document: {querySelector: () => ({})}};
vm.createContext(context);
vm.runInContext(payload.source, context);
process.stdout.write(JSON.stringify(context.ensureShape(payload.pack)));
"""
            completed = subprocess.run(
                ["node", "-e", javascript],
                input=json.dumps({"source": editor_source, "pack": loaded}),
                text=True, encoding="utf-8", capture_output=True, check=True,
            )
            loaded = json.loads(completed.stdout)
            loaded["meta"]["title"] = "検証"
            saved = app.api_save_scenario(filename, app.ScenarioSaveRequest(scenario=loaded))["scenario"]
            self.assertEqual(saved["meta"]["difficulty"], pack["meta"]["difficulty"])
            self.assertEqual(saved["difficulty_overlays"], pack["difficulty_overlays"])
            normalized = normalize_scenario_pack(saved)
            self.assertEqual(normalized["difficulty_overlays"], pack["difficulty_overlays"])


if __name__ == "__main__":
    unittest.main()
