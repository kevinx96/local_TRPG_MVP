import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from host import app, combat, state


class DeathLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.saves = patch.object(state, "SAVE_DIR", Path(self.temp.name))
        self.saves.start()
        self.addCleanup(self.saves.stop)

    def session(self, location="forest_wolves"):
        public = state.create_session("host/prompt/processed/dragon_rpg_hybrid.json", character_id="mage")
        session = state.load_session(public["id"])
        session["world_state"] = {"location_id": location}
        state.ensure_world_state(session)
        return session

    def defeat(self, session):
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))
        session["character"]["hp"] = 1
        session["companion"] = None
        for enemy in session["combat"]["enemies"]:
            enemy["skills"] = []
            enemy["combat"] = {"basic_attack": {"name": "致命傷", "damage": "999", "accuracy": 100}}
        session["character"].setdefault("combat", {})["evade"] = 0
        state.save_session(session)
        with patch.object(combat.random, "randint", return_value=1):
            return app.api_combat_action(session["id"], app.CombatActionRequest(action_type="defend"))

    def test_wolf_death_ends_game_and_rejects_further_input(self):
        session = self.session()
        with patch.object(app, "chat_completion") as llm:
            public = self.defeat(session)
            self.assertTrue(public["game_over"])
            self.assertEqual(public["character"]["hp"], 0)
            self.assertEqual(public["choices"], [])
            resolved = app.api_combat_resolve(session["id"])
            self.assertTrue(resolved["game_over"])
            self.assertFalse(resolved["in_combat"])
            with self.assertRaises(HTTPException) as error:
                app.api_turn(session["id"], app.TurnRequest(text="城へ戻る"))
            self.assertEqual(error.exception.status_code, 409)
            llm.assert_not_called()

    def test_missing_defeat_policy_defaults_to_game_over(self):
        session = self.session()
        location = next(loc for loc in session["scenario_pack"]["locations"] if loc["id"] == "forest_wolves")
        location["combat"]["defeat_effects"] = {}
        public = self.defeat(session)
        self.assertTrue(public["game_over"])

    def test_xanxus_defeat_still_reaches_ultimatum(self):
        session = self.session("xanxus_battle")
        public = self.defeat(session)
        self.assertFalse(public["game_over"])
        self.assertEqual(public["character"]["hp"], 1)
        with patch.object(app, "chat_completion") as llm:
            resolved = app.api_combat_resolve(session["id"])
        llm.assert_not_called()
        self.assertEqual(resolved["current_location"], "xanxus_ultimatum")
        self.assertTrue(resolved["choices"])

    def test_ended_game_does_not_recover_choices_from_history(self):
        session = self.session()
        session["game_over"] = {"reason": "敗北", "ending": "death"}
        session["choices"] = [{"text": "城へ戻る"}]
        state.add_assistant_message(session, "次の選択肢：\n1. 周囲を調べる\n2. 城へ戻る")
        self.assertEqual(state.public_session(session)["choices"], [])

    def test_legacy_defeat_is_migrated_once_without_reviving(self):
        session = self.session()
        session["scenario_pack"]["meta"]["content_revision"] = "2026-09-06-api-free-actions"
        session["last_combat_result"] = {"combat_id": "old-death", "outcome": "defeat", "location_id": "forest_wolves"}
        session["combat_blocked_location"] = "forest_wolves"
        session["character"]["hp"] = 1
        session["choices"] = [{"text": "城へ戻る"}]
        state.save_session(session)
        loaded = state.load_session(session["id"])
        self.assertTrue(loaded["game_over"])
        self.assertEqual(loaded["character"]["hp"], 0)
        self.assertEqual(loaded["choices"], [])
        self.assertEqual(state.current_location_id(loaded), "forest_wolves")
        again = state.load_session(session["id"])
        self.assertEqual(again["messages"], loaded["messages"])

    def test_active_old_encounter_uses_updated_defeat_policy(self):
        session = self.session()
        session["scenario_pack"]["meta"]["content_revision"] = "2026-09-06-api-free-actions"
        session["combat_start_requested"] = True
        combat.ensure_combat_started(session)
        session["combat"]["encounter"]["defeat_effects"] = {"hp_change": 1}
        state.save_session(session)
        loaded = state.load_session(session["id"])
        self.assertIn("game_over", loaded["combat"]["encounter"]["defeat_effects"])

    def test_all_scripted_defeats_end_or_have_explicit_continuation(self):
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads((Path("host/prompt/processed") / name).read_text(encoding="utf-8-sig"))
            for loc in pack["locations"]:
                encounter = loc.get("combat") or {}
                if not encounter.get("enemy_ids"):
                    continue
                with self.subTest(pack=name, location=loc["id"]):
                    delta = encounter.get("defeat_effects") or {}
                    if loc["id"] == "xanxus_battle":
                        self.assertEqual(delta.get("current_location"), "xanxus_ultimatum")
                    else:
                        self.assertTrue(delta.get("game_over"))
