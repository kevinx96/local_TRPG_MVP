from __future__ import annotations

import json
import random
import unittest
from unittest.mock import patch

from host import combat, state
from scripts.balance import checkpoints, class_aware, route


class ClassAwareRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))

    def session(self, location: str, character: str = "thief", **attributes: int):
        session = checkpoints.fresh_session(self.pack, character)
        state.commit_world_position(session, location_id=location)
        session["character"]["attributes"].update(attributes)
        session["character"].update(hp=20, max_hp=20)
        return session

    def test_check_distribution_uses_full_attribute_and_naturals(self):
        session = self.session("valley_entrance", dex=4)
        result = class_aware.check_distribution(session, "1d20+dex", 14)
        probabilities = {k: v[0] for k, v in result.items()}
        self.assertEqual(probabilities, {"critical_failure": .05, "failure": .4, "success": .5, "critical_success": .05})
        self.assertEqual(result["success"][1] + 4, 14)
        plain = class_aware.check_distribution(session, "1d20+dex", 14, critical=False, natural_one_fails=True)
        self.assertAlmostEqual(plain["success"][0], .55)
        self.assertAlmostEqual(plain["failure"][0], .45)
        self.assertAlmostEqual(class_aware.check_distribution(session, "1d30", 4, critical=False)["success"][0], 27 / 30)

    def test_resource_score_counts_consumables_and_death(self):
        session = self.session("valley_entrance")
        actor = session["character"]
        actor.update(hp=10, max_hp=20, mp=3, max_mp=6, sp=7, max_sp=14, inventory=[])
        self.assertAlmostEqual(class_aware.resource_score(session), .5)
        actor["inventory"] = [{"name": "薬草", "quantity": 2, "combat": {"kind": "heal", "healing": "10", "consumable": True}},
                              {"name": "氷の護符", "combat": {"kind": "damage", "damage": "1d8", "consumable": False}}]
        self.assertAlmostEqual(class_aware.resource_score(session), (1.5 + .5 + .5) / 3)
        actor["hp"] = 0
        self.assertEqual(class_aware.resource_score(session), 0)

    def test_check_value_is_probability_weighted_with_failure_combat(self):
        session = self.session("valley_entrance", dex=4)
        seen = []

        def fake_combat(evaluator, s, rest=()):
            seen.append(bool(s.get("enemy_first_requested")))
            return .25 if s.get("enemy_first_requested") else .5

        with patch.object(class_aware.Evaluator, "combat_value", fake_combat):
            values = class_aware.Evaluator(depth=0).values(session, "valley_entrance")
        score = class_aware.resource_score(session)
        self.assertAlmostEqual(values["fight"], .5)
        self.assertAlmostEqual(values["sneak"], .55 * score + .45 * .25)
        self.assertIn(True, seen)

    def test_retry_check_value_and_lethal_attempts(self):
        session = self.session("burning_house", str=8, dex=16)
        evaluator = class_aware.Evaluator(["riku"], depth=0)
        values = evaluator.values(session, "burning_house")
        self.assertEqual(set(values), {"beam", "climb"})
        score = class_aware.resource_score(session)
        # Past the lookahead a still-blocked node is worth 0.
        self.assertAlmostEqual(values["climb"], .95 * score)
        self.assertAlmostEqual(values["beam"], .8 * score)
        hurt = class_aware.clone(session)
        hurt["character"]["hp"] -= 3
        deeper = class_aware.Evaluator(["riku"], depth=1).values(session, "burning_house")
        self.assertAlmostEqual(deeper["climb"], .95 * score + .05 * .95 * class_aware.resource_score(hurt))
        self.assertLess(deeper["beam"], deeper["climb"])
        session["character"]["hp"] = 4
        self.assertEqual([o[0] for o in class_aware.node_options(session, "burning_house", frozenset({"riku"}))], ["climb"])
        session["character"]["hp"] = 3
        self.assertEqual(class_aware.node_options(session, "burning_house", frozenset({"riku"})), [])
        self.assertEqual([o[0] for o in class_aware.node_options(session, "burning_house", frozenset())], ["leave"])

    def test_side_quest_toggles_skip_option(self):
        session = self.session("forest_wolves")
        self.assertEqual([o[0] for o in class_aware.node_options(session, "forest_wolves", frozenset())], ["abandon"])
        self.assertEqual([o[0] for o in class_aware.node_options(session, "forest_wolves", frozenset({"gald"}))],
                         ["fight", "distract", "sneak"])

    def test_policy_reads_no_rng_and_depends_only_on_visible_state(self):
        session = self.session("valley_entrance")
        before = class_aware.visible_key(session)
        results = []
        for seed in (1, 999):
            rng = random.Random(seed)
            rng_state = rng.getstate()
            with patch.object(combat, "random", rng), patch.object(state, "random", rng):
                results.append(class_aware.Evaluator(n=4).values(session, "valley_entrance"))
            self.assertEqual(rng.getstate(), rng_state)
        self.assertEqual(results[0], results[1])
        self.assertEqual(class_aware.visible_key(session), before)
        changed = class_aware.clone(session)
        changed["character"]["hp"] = 5
        self.assertNotEqual(class_aware.visible_key(changed), before)

    def test_same_seed_gives_same_choices(self):
        with patch.object(class_aware, "ESTIMATE_N", 4):
            runs = [class_aware.trial(self.pack, self.cp, "mage", 11, quests=("gald", "riku")) for _ in range(2)]
        self.assertEqual([(c["node"], c["option"]) for c in runs[0]["choices"]],
                         [(c["node"], c["option"]) for c in runs[1]["choices"]])
        self.assertEqual(runs[0]["completed"], runs[1]["completed"])

    def test_backbone_with_forced_checks_reproduces_hp70(self):
        for character in ("hero", "thief"):
            with self.subTest(character=character):
                hp70 = route.simulate_route(self.pack, self.cp, character, n=4, seed=5, rest_policy="hp70")
                replay = route.simulate_route(self.pack, self.cp, character, n=4, seed=5, rest_policy="class_aware",
                                              quests=(), decisions="backbone", dice="forced")
                for key in ("completion_rate", "failure_counts", "boss_resources_mean", "battle_reached", "rest_counts"):
                    self.assertEqual(hp70[key], replay[key])

    def test_three_policies_and_all_side_quests_run(self):
        with patch.object(class_aware, "ESTIMATE_N", 2):
            for rest_policy in ("none", "hp70", "class_aware"):
                with self.subTest(rest_policy=rest_policy):
                    row = route.simulate_route(self.pack, self.cp, "hero", n=1, seed=3, rest_policy=rest_policy,
                                               quests=("gald", "riku"))
                    self.assertIn(row["completion_rate"], (0, 1))
                    if rest_policy == "class_aware":
                        self.assertIn("lost_goblin_crossroads", row["choice_stats"]["decisions"])
            result = class_aware.trial(self.pack, self.cp, "hero", 3, quests=class_aware.QUEST_ORDER)
        visited = {c["node"] for c in result["choices"]}
        self.assertIn("goblin_fort", visited)
        self.assertTrue(result["completed"] or result["failed_at"])

    def test_choice_stats_counts_decisions_and_first_choice(self):
        stats = class_aware.choice_stats([
            dict(choices=[dict(node="burning_house", option="climb"), dict(node="burning_house", option="climb")]),
            dict(choices=[dict(node="burning_house", option="beam")]),
        ])
        self.assertEqual(stats["decisions"], {"burning_house": {"climb": 2, "beam": 1}})
        self.assertEqual(stats["first_choice_per_trial"], {"burning_house": {"climb": 1, "beam": 1}})


if __name__ == "__main__":
    unittest.main()
