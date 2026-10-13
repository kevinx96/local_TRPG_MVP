from __future__ import annotations

import json
import unittest
from copy import deepcopy

from host import free_actions, state
from scripts.balance import checkpoints
from scripts.eval import choice_visibility


class ChoiceVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.session = checkpoints.fresh_session(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO), "hero")

    def public_choices(self, requirement, **extra):
        self.session["choices"] = [dict(text="虹晶の欠片を武器に仕立ててもらう", preview="虹晶の剣",
                                        risk="1d20判定（DC10）", requirements=requirement,
                                        intent_keywords=["虹晶の欠片"], effects=[{"add_item": "虹晶の剣"}], **extra)]
        return state.public_session(self.session)["choices"]

    def test_unknown_response_contains_no_original_text_or_metadata(self):
        for requirement in ({"flag": "heard_seal_lore"}, {"not_flag": "heard_king_info"},
                            {"flags_count_gte": {"flags": ["a", "b"], "count": 2}},
                            {"companion_id": "robin"}, {"has_item": "虹晶の欠片"}):
            self.session["flags"]["heard_king_info"] = True
            with self.subTest(requirement=requirement):
                self.assertEqual(self.public_choices(requirement), [
                    {"text": "？？？", "enabled": False, "visibility": "unknown",
                     "disabled_reason": "まだ知らない何かが必要なようだ。"}])
                self.assertNotIn("虹晶", json.dumps(state.public_session(self.session), ensure_ascii=False))
                self.assertEqual(self.session["choices"][0]["requirements"], requirement)

    def test_known_requirements_and_aliases(self):
        self.session["character"]["gold"] = 10
        for requirement in ({"gold_gte": 20}, {"min_gold": 20}, {"gold_lte": 0}, {"max_gold": 0},
                            {"attribute": "str", "gte": 99}, {"attr": "wis", "gt": 99},
                            {"attribute": "dex", "min": 99}, {"hp_gte": 99}, {"mp_gte": 99}, {"sp_gte": 99},
                            {"lacks_item": "薬草"}, {"not_item": "薬草"}, {"missing_item": "薬草"}):
            with self.subTest(requirement=requirement):
                choice = self.public_choices(requirement)[0]
                self.assertEqual(choice["visibility"], "known")
                self.assertFalse(choice["enabled"])
                self.assertIn("虹晶", choice["text"])
                self.assertTrue(choice["disabled_reason"])

    def test_item_history_survives_event_log_compaction(self):
        state.apply_state_delta(self.session, {"inventory_add": [{"name": "聖水"}]})
        state.apply_state_delta(self.session, {"inventory_remove": [{"name": "聖水"}]})
        for _ in range(245):
            state.record_state_event(self.session, "flag_set", "", {}, visible=False)
        self.assertFalse(any(e["kind"] == "item_added" for e in self.session["event_log"]))
        for alias in ("has_item", "inventory_has", "requires_item"):
            self.assertEqual(self.public_choices({alias: "鉄の剣"})[0]["visibility"], "available")
            self.assertEqual(self.public_choices({alias: "聖水"})[0]["visibility"], "known")
        self.session.pop("known_item_names", None)
        self.session["event_log"].append({"kind": "item_added", "data": {"item": "聖水"}})
        self.assertEqual(self.public_choices({"has_item": "聖水"})[0]["visibility"], "known")

    def test_only_failed_branches_classify_and_character_takes_precedence(self):
        for requirement in ([{"character_id": "mage"}, {"gold_gte": 99}],
                            {"any": [{"character_id": "mage"}, {"flag": "a"}]}):
            self.assertEqual(self.public_choices(requirement), [])
        for requirement in ({"all": [{"character_id": "hero"}, {"gold_gte": 99}]},
                            {"all": [{"any": [{"character_id": "mage"}, {"character_id": "hero"}]}, {"gold_gte": 99}]}):
            self.assertEqual(self.public_choices(requirement)[0]["visibility"], "known")
        self.session["flags"]["heard_seal_lore"] = True
        requirement = {"any": [{"flag": "heard_seal_lore"}, {"has_item": "虹晶の欠片"}]}
        self.assertEqual(self.public_choices(requirement)[0]["visibility"], "available")

    def test_filters_and_nested_visible_count(self):
        self.assertEqual(self.public_choices({"flag": "a"}, secret=True), [])
        self.assertEqual(self.public_choices({}, visible_after="a"), [])
        self.session["flags"]["a"] = True
        self.assertEqual(self.public_choices({}, hidden_after="a"), [])
        self.session["choices"] = [{"text": "イアンと会話する", "children": [
            {"text": "邪竜を倒すアドバイスを求める", "requirements": {"character_id": "mage"}},
            {"text": "虹晶の欠片", "requirements": {"has_item": "虹晶の欠片"}},
            {"text": "宿で休む（10G）", "requirements": {"gold_gte": 10}},
            {"text": "泉の封印について尋ねる", "requirements": {"flag": "b"}, "secret": True}]}]
        result = state.public_session(self.session)["choices"]
        self.assertEqual([c["visibility"] for c in result[0]["children"]], ["unknown", "known"])
        self.assertEqual(len(result[0]["children"]), 2)
        self.assertNotIn("虹晶", json.dumps(result, ensure_ascii=False))
        self.session["choices"][0]["children"] = self.session["choices"][0]["children"][:1]
        self.assertEqual(state.public_session(self.session)["choices"], [])

    def test_planner_and_executable_actions_do_not_use_ui_redaction(self):
        state.commit_world_position(self.session, location_id="magic_shop")
        before = deepcopy(state.current_actions_for_session(self.session))
        planner = free_actions.build_plan_messages(self.session, "周囲を見る")
        self.assertTrue(any(c["text"] == "？？？" for c in state.public_session(self.session)["choices"]))
        self.assertEqual(planner, free_actions.build_plan_messages(self.session, "周囲を見る"))
        self.assertEqual(before, state.current_actions_for_session(self.session))
        actions = json.loads(planner[1]["content"])["actions"]
        self.assertIn("虹晶", next(a["text"] for a in actions if a["id"] == "forge_prism_weapon"))
        self.assertFalse(any(a["id"] == "ask_seal_lore" for a in actions))

    def test_first_arrival_audit_uses_shortest_route_and_public_redaction(self):
        pack = deepcopy(self.session["scenario_pack"])
        allowed = {"castle": {"ask_king_info", "check_supplies", "go_castle_town"},
                   "castle_town": {"go_magic_shop", "return_castle_from_town"},
                   "magic_shop": {"ask_seal_lore", "forge_prism_weapon", "return_castle_from_magic_shop"}}
        pack["locations"] = [loc for loc in pack["locations"] if loc["id"] in allowed]
        for loc in pack["locations"]:
            loc["actions"] = [a for a in loc["actions"] if a["id"] in allowed[loc["id"]]]
        arrivals = choice_visibility.first_arrivals(pack, "hero")
        self.assertEqual(set(arrivals), set(allowed))
        self.assertEqual(arrivals["magic_shop"]["path"], ["go_castle_town", "go_magic_shop"])
        result = choice_visibility.inspect_arrival(pack, arrivals["magic_shop"], choice_visibility.names(pack))
        self.assertTrue(any(c["visibility"] == "unknown" for c in result["choices"]))
        self.assertNotIn("虹晶", json.dumps(result, ensure_ascii=False))
        self.assertNotIn("泉の封印", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
