from __future__ import annotations

from scripts.scenario.holy_sword_049 import migrate as holy_sword
from scripts.scenario.levels_skills_v2 import migrate as levels

import json
import unittest
from copy import deepcopy

from host import app, combat, state
from scripts.balance import checkpoints
from scripts.playtest.explore import offline_runtime
from scripts.scenario.tutorial_slime import PACKS, apply


class TutorialSlimeTests(unittest.TestCase):
    def setUp(self):
        runtime = offline_runtime(7)
        runtime.__enter__()
        self.addCleanup(runtime.__exit__, None, None, None)
        public = app.api_create_session(app.CreateSessionRequest(character_id="hero"))
        self.session_id = public["id"]
        session = state.load_session(self.session_id)
        state.apply_state_delta(session, {"current_location": "dark_forest_loc"}, allow_world_transition=True)
        state.save_session(session)

    def start(self):
        app.api_turn(self.session_id, app.TurnRequest(text="スライムと戦う", action_id="attack_slime"))
        return state.load_session(self.session_id)

    def act(self, **kwargs):
        return app.api_combat_action(self.session_id, app.CombatActionRequest(**kwargs))

    def count(self, session, identifier):
        return sum(item.get("quantity", 1) for item in session["character"]["inventory"] if item.get("id") == identifier)

    def test_migration_is_idempotent_on_both_packs(self):
        for name in PACKS:
            pack = json.loads(checkpoints.DEFAULT_SCENARIO.with_name(name).read_text(encoding="utf-8"))
            again = deepcopy(pack)
            apply(again)
            again = holy_sword(levels(again))
            self.assertEqual(again, pack, name)

    def test_potion_is_given_silently_once(self):
        session = self.start()
        self.assertEqual(self.count(session, "travel_potion"), 1)
        self.assertNotIn("silent", next(i for i in session["character"]["inventory"] if i.get("id") == "travel_potion"))
        self.assertNotIn("旅の治療薬", json.dumps(session.get("system_logs", []), ensure_ascii=False))
        self.assertIn("旅の治療薬", session["known_item_names"])
        self.assertTrue(session["flags"]["tutorial_potion_given"])

    def test_potion_also_arrives_when_combat_starts_without_the_choice(self):
        session = state.load_session(self.session_id)
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))
        self.assertEqual(self.count(session, "travel_potion"), 1)
        session["combat"] = None
        session["combat_start_requested"] = True
        combat.ensure_combat_started(session)
        self.assertEqual(self.count(session, "travel_potion"), 1)

    def test_acid_fires_once_on_round_one_and_ignores_defense(self):
        session = self.start()
        session["character"].setdefault("combat", {})["defense"] = 50
        state.save_session(session)
        hp = session["character"]["hp"]
        public = self.act(action_type="defend")
        session = state.load_session(self.session_id)
        self.assertEqual(hp - session["character"]["hp"], 8)
        self.assertTrue(public["combat"]["tutorial"]["enemy_skill_used"])
        self.assertIn("防御無視", json.dumps(public["combat"], ensure_ascii=False))
        for _ in range(4):
            if not combat.combat_is_active(session):
                break
            self.act(action_type="defend")
            session = state.load_session(self.session_id)
        enemy = session["combat"]["enemies"][0]
        self.assertEqual(enemy["skill_uses"], {"slime_acid": 1})

    def test_tutorial_flow_tracks_player_action_types(self):
        self.start()
        public = self.act(action_type="attack", target_id=self.target())
        self.assertEqual(public["combat"]["tutorial"]["player_actions"], ["attack"])
        public = self.act(action_type="item", action_id="travel_potion")
        self.assertEqual(public["combat"]["tutorial"]["player_actions"], ["attack", "item"])
        session = state.load_session(self.session_id)
        self.assertEqual(self.count(session, "travel_potion"), 0)

    def target(self):
        return state.load_session(self.session_id)["combat"]["enemies"][0]["id"]

    def test_regular_slime_is_untouched(self):
        pack = json.loads(checkpoints.DEFAULT_SCENARIO.read_text(encoding="utf-8"))
        slime = next(enemy for enemy in pack["enemies"] if enemy["id"] == "slime")
        self.assertEqual(slime["skills"], [])
        self.assertEqual(slime["combat"]["basic_attack"]["damage"], "1d6")


if __name__ == "__main__":
    unittest.main()
