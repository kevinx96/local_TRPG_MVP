from __future__ import annotations

import hashlib
import json
import shutil
import unittest
import uuid
from copy import deepcopy

from host import combat, free_actions, state
from host.scenario_context import current_actions_for_session, fallback_choices_for_session
from scripts.eval.benchmark_v2 import recipes as frozen_recipes
from scripts.eval.benchmark_v2_current import CURRENT_SCENARIO, current_copy, generate
from scripts.eval.snapshots import ROOT, build_snapshot, isolated_engine, load_snapshot


class BenchmarkPinningTests(unittest.TestCase):
    def test_frozen_scenario_and_all_benchmark_recipes_are_pinned(self):
        frozen = ROOT / "eval/benchmark/scenario_frozen/dragon_rpg@f41af9d.json"
        self.assertEqual(hashlib.sha256(frozen.read_bytes()).hexdigest(),
                         "73a484bc75f75245a5773d74cad45facaa8c2150678fae2e178e7e6a7bba83ca")
        rows = [json.loads(line) for line in (ROOT / "eval/benchmark/intent_v2.jsonl").read_text(encoding="utf-8").splitlines()]
        for identifier in {row["snapshot"] for row in rows}:
            recipe = json.loads((ROOT / "eval/snapshots" / f"{identifier}.json").read_text(encoding="utf-8"))
            self.assertEqual(recipe["scenario"], frozen.relative_to(ROOT).as_posix())
        for recipe in frozen_recipes().values():
            self.assertEqual(recipe["scenario"], frozen.relative_to(ROOT).as_posix())
        for path in (ROOT / "eval/snapshots").glob("v2_scenario_*.json"):
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["scenario"], CURRENT_SCENARIO)

    def test_current_generator_preserves_labels_and_does_not_mutate_sources(self):
        directory = ROOT / ".tmp-test" / f"pinning-{uuid.uuid4().hex}"
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        (directory / "eval/snapshots").mkdir(parents=True)
        (directory / "eval/benchmark").mkdir()
        source = ROOT / "eval/benchmark/intent_v2.jsonl"
        shutil.copyfile(source, directory / "eval/benchmark/intent_v2.jsonl")
        rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
        recipes = {}
        for identifier in {row["snapshot"] for row in rows}:
            path = ROOT / "eval/snapshots" / f"{identifier}.json"
            shutil.copyfile(path, directory / "eval/snapshots" / path.name)
            recipes[identifier] = json.loads(path.read_text(encoding="utf-8"))
        originals = deepcopy((rows, recipes))
        copied_rows, copied_recipes = current_copy(rows, recipes)
        self.assertEqual((rows, recipes), originals)
        self.assertEqual(generate(directory), (len(rows), len(recipes)))
        outputs = [directory / "eval/candidates/intent_v2_current.jsonl",
                   *(directory / "eval/snapshots").glob("v2cur_*.json")]
        first = {path: path.read_bytes() for path in outputs}
        generate(directory)
        self.assertEqual(first, {path: path.read_bytes() for path in outputs})
        for old, new in zip(rows, copied_rows):
            self.assertEqual(new["label_status"], "needs_review")
            self.assertEqual({k: v for k, v in old.items() if k not in {"id", "snapshot", "label_status"}},
                             {k: v for k, v in new.items() if k not in {"id", "snapshot", "label_status"}})
            recipe = copied_recipes[new["snapshot"]]
            self.assertEqual(recipe["scenario"], CURRENT_SCENARIO)
            self.assertEqual({k: v for k, v in recipe.items() if k not in {"id", "scenario"}},
                             {k: v for k, v in recipes[old["snapshot"]].items() if k not in {"id", "scenario"}})
        for path in outputs:
            self.assertEqual(path.read_bytes(), (ROOT / path.relative_to(directory)).read_bytes())
        self.assertEqual(source.read_bytes(), (directory / "eval/benchmark/intent_v2.jsonl").read_bytes())


class SecretActionTests(unittest.TestCase):
    def session(self, filename="dragon_rpg.json", location="castle_report", character="hero"):
        session = build_snapshot(dict(id="secret-test", scenario=f"host/prompt/processed/{filename}",
                                      gm_mode="full", character_id=character, location_id="castle"))
        record = next(l for l in session["scenario_pack"]["locations"] if l["id"] == location)
        session["world_state"] = dict(scene_id=record["scene_id"], location_id=location)
        return session

    def assert_visibility(self, session, action_id, visible):
        action = next(a for a in state._iter_actions(current_actions_for_session(session)) if a["id"] == action_id)
        messages = json.dumps(free_actions.build_plan_messages(session, "少し考えよう。"), ensure_ascii=False)
        choices = json.dumps(state.public_session(session)["choices"], ensure_ascii=False)
        for surface in (messages, choices):
            self.assertEqual(action_id in surface, visible)
            self.assertEqual(action["text"] in surface, visible)

    def test_all_exploration_secrets_hide_and_reappear_in_both_packs(self):
        cases = [
            ("castle_report", "report_with_evidence", {"heard_treaty_lore": True, "noticed_general_frost": True}, None),
            ("inn", "ask_robin_stolen_scale", {"recruited_robin": True, "cleared_goblin_fort": True}, None),
            ("ignis_purified", "ask_ignis_aid", {"heard_ignis_testimony": True}, None),
            ("alley_night", "buy_white_scale", {}, 60),
        ]
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            for location, identifier, flags, gold in cases:
                with self.subTest(pack=filename, action=identifier):
                    session = self.session(filename, location)
                    session["character"]["gold"] = 0
                    session["choices"] = fallback_choices_for_session(session)
                    self.assert_visibility(session, identifier, False)
                    session["flags"].update(flags)
                    if gold is not None:
                        session["character"]["gold"] = gold
                    self.assert_visibility(session, identifier, True)
                    session["flags"].clear()
                    session["character"]["gold"] = 0
                    self.assert_visibility(session, identifier, False)

    def test_secret_nested_group_and_ordinary_disabled_action(self):
        session = self.session(location="village")
        location = state._current_location_record(session)
        group = next(a for a in location["actions"] if a["id"] == "ask_elder_weakness")
        group["children"][0].update(secret=True, requirements={"flag": "heard_treaty_lore"})
        ordinary = next(a for a in location["actions"] if a["id"] == "go_dragon_valley")
        ordinary["requirements"] = {"flag": "heard_treaty_lore"}
        session["choices"] = fallback_choices_for_session(session)
        self.assert_visibility(session, "ask_elder_treaty", False)
        self.assertNotIn("ask_elder_weakness", json.dumps(state.public_session(session)["choices"]))
        context = json.loads(free_actions.build_plan_messages(session, "")[1]["content"])
        self.assertFalse(next(a for a in context["actions"] if a["id"] == "go_dragon_valley")["enabled"])
        session["flags"]["heard_treaty_lore"] = True
        self.assert_visibility(session, "ask_elder_treaty", True)
        group.update(secret=True, requirements={"flag": "noticed_general_frost"})
        self.assert_visibility(session, "ask_elder_treaty", False)
        session["flags"]["noticed_general_frost"] = True
        self.assert_visibility(session, "ask_elder_treaty", True)

    def test_elder_leaf_is_already_visible_and_executable(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            session = self.session(filename, "village", "mage")
            context = json.loads(free_actions.build_plan_messages(session, "長老に邪竜の弱点を聞く")[1]["content"])
            actions = {a["id"]: a for a in context["actions"]}
            self.assertTrue(actions["ask_elder_treaty"]["enabled"])
            self.assertNotIn("ask_elder_weakness", actions)
            resolution = state.resolve_player_intent(session, action_id="ask_elder_treaty")
            self.assertEqual(resolution["status"], "resolved")
            with isolated_engine("elder-action"):
                state.apply_action_result(session, resolution["action"], {})
            self.assertTrue(session["flags"]["heard_treaty_lore"])

    def test_purification_secrets_use_combat_availability(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            session = self.session(filename, "dragon_valley_loc", "cleric")
            with isolated_engine("secret-combat"):
                combat.ensure_combat_started(session)
            specials = session["combat"]["encounter"]["special_actions"]
            identifiers = {"purify_ignis_holy_water", "purify_ignis_prayer"}
            self.assertTrue(all(a.get("secret") is True for a in specials if a["id"] in identifiers))
            def available():
                return {a["id"] for a in combat.public_combat(session)["actions"]}
            self.assertFalse(identifiers & available())
            session["flags"]["heard_treaty_lore"] = True
            session["character"]["mp"] = 6
            session["character"]["inventory"].append(dict(id="holy_water", name="聖水", quantity=1))
            for enemy in session["combat"]["enemies"]:
                enemy["hp"] = 1
            self.assertTrue(identifiers <= available())
            for surface in (free_actions.build_plan_messages(session, "少し考えよう。"), state.public_session(session)["choices"]):
                self.assertFalse(any(identifier in json.dumps(surface) for identifier in identifiers))

    def test_existing_requirement_reason_is_preserved(self):
        session = load_snapshot("v2_village_mage")
        action = next(a for a in current_actions_for_session(session) if a["id"] == "buy_ice_amulet")
        expected = state.choice_requirement_status(action, session["character"])
        self.assertFalse(expected[0])
        self.assertEqual(state.action_requirement_status(action, session), expected)


if __name__ == "__main__":
    unittest.main()
