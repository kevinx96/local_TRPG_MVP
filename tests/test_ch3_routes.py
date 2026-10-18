from __future__ import annotations

import unittest
from copy import deepcopy

from host import combat, state
from scripts.balance import ch3_routes, checkpoints, route
from scripts.playtest import explore, metrics


class ChapterThreeRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cp = checkpoints.generate()
        cls.start = ch3_routes.starting_checkpoint(cls.pack, cp, "hero")

    def test_checkpoint_is_replayable_and_preparation_is_paid(self):
        session = checkpoints.fresh_session(self.pack, "hero")
        from scripts.balance.rewards import consume_boosts

        for source in self.start["checkpoint_sources"]:
            self.assertEqual(state.current_location_id(session), source["location"])
            checkpoints.replay_step(session, source["step"])
            consume_boosts(session)
        self.assertEqual(route.resources(session), route.resources(self.start))
        self.assertEqual(session["character"]["gold"], 240)
        for path in ("battlefield", "gorge"):
            condition = dict(path=path, prepared=True, cursed=False, companion="none")
            staged = ch3_routes.prepare(self.start, condition)
            self.assertEqual(staged["character"]["gold"], 45)
            self.assertTrue(staged["flags"]["forged_dawn_weapon"])
            self.assertIn("暁光の剣", staged["character"]["equipment"])
            self.assertIn("守護団の鎖帷子", staged["character"]["equipment"])
            self.assertEqual(state.current_location_id(staged), "old_battlefield" if path == "battlefield" else "gorge_entrance")
        self.assertEqual(self.start["character"]["gold"], 240)

    def test_matrix_covers_required_cells_and_other_companions(self):
        conditions = ch3_routes.conditions()
        self.assertEqual(len(conditions), 51)
        for path, counter in ch3_routes.COUNTERS.items():
            for prepared in (False, True):
                for cursed in ((False, True) if path == "battlefield" else (False,)):
                    group = [c for c in conditions if (c["path"], c["prepared"], c["cursed"]) == (path, prepared, cursed)]
                    self.assertEqual({c["companion"] for c in group}, set(ch3_routes.COMPANIONS))
                    self.assertIn(counter, ch3_routes.COMPANIONS)

    def test_village_keeps_authored_warlock_departure(self):
        staged = ch3_routes.prepare(self.start, dict(path="village", prepared=False, cursed=False, companion="blue_robed_mage"))
        self.assertIsNone(staged["companion"])
        self.assertTrue(staged["flags"]["warlock_disappeared_at_village"])

    def test_trials_continue_through_ignis_and_are_reproducible(self):
        for path in metrics.ROUTES:
            condition = dict(path=path, prepared=False, cursed=False, companion="none")
            staged = ch3_routes.prepare(self.start, condition)
            before = deepcopy(staged)
            first = ch3_routes.trial(staged, condition, 37)
            second = ch3_routes.trial(staged, condition, 37)
            for result in (first, second):
                for step in result["steps"]:
                    step["roll"].pop("created_at", None)
            self.assertEqual(first, second)
            self.assertEqual(staged, before)
            self.assertTrue(first["battles"])
            if first["completed"]:
                self.assertEqual(first["battles"][-1]["encounter"], "dragon_valley_loc")
                self.assertEqual(first["battles"][-1]["status"], "victory")
            else:
                self.assertEqual(first["terminal"], "defeat")
            self.assertIn("go_dragon_valley", [s["action"] for s in first["steps"]])

    def test_comparison_detects_locked_old_route_gap_and_wrong_counter(self):
        rows = []
        for character in ch3_routes.CHARACTERS:
            for condition in ch3_routes.conditions():
                rate = .5 if condition["path"] == "village" else .7 if condition["path"] == "battlefield" else .6
                if condition["companion"] == "robin":
                    rate += .1
                rows.append(dict(character=character, **condition, success_rate=rate))
        comparison = ch3_routes.comparisons(rows)
        self.assertTrue(all(not r["passed"] for r in comparison["route_gaps"]))
        self.assertTrue(all(r["universal_best"] == ["battlefield"] for r in comparison["rankings"]))
        self.assertTrue(all(not r["passed"] and r["best_other"] == "robin" for r in comparison["counters"]))

    def test_full_combat_log_survives_old_limits(self):
        session = checkpoints.fresh_session(self.pack, "hero")
        session["world_state"] = {"location_id": "dark_forest_loc"}
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))
        initial = len(session["combat"]["log"])
        for _ in range(100):
            combat._log(session, "player", "stance", "防御態勢を取り、次の攻撃に備えた。")
        public = combat.public_combat(session)
        self.assertEqual(len(public["log"]), initial + 100)
        public["log"][0]["text"] = "変更"
        self.assertNotEqual(public["log"][0]["text"], session["combat"]["log"][0]["text"])


    def test_counter_ties_fail_strict_second_round_target(self):
        rows = [dict(character=character, **condition, success_rate=.8)
                for character in ch3_routes.CHARACTERS for condition in ch3_routes.conditions()]
        self.assertTrue(all(not r["passed"] and r["margin_pp"] == 0 for r in ch3_routes.comparisons(rows)["counters"]))

    def test_outside_three_point_boundary_and_original_control_cohorts(self):
        from scripts.balance.ch3_outside import comparisons

        rows = [dict(location="dragon_valley_loc", character="hero", companion=cid,
                     win_rate=.93 if cid == "paladin_liese" else .9601 if cid == "hydromancer_elio" else .9)
                for cid in ch3_routes.COMPANIONS]
        liese, elio = comparisons(rows)
        self.assertTrue(liese["passed"])
        self.assertFalse(elio["passed"])
        self.assertEqual(elio["best"], "paladin_liese")

    def test_tuning_only_accepts_authorized_ranges(self):
        import argparse
        from scripts.balance.ch3_tuning import parse_variant

        self.assertEqual(parse_variant("liese:2d4:0.18")["heal_ratio"], .18)
        self.assertEqual(parse_variant("elio:2d6:2")["period"], 2)
        for value in ("liese:2d4:0.14", "liese:2d7:0.25", "elio:2d6:1", "robin:2d4:2"):
            with self.assertRaises(argparse.ArgumentTypeError):
                parse_variant(value)

    def test_critical_grid_covers_sub_percent_healing_changes(self):
        import math
        from scripts.balance.ch3_tuning import critical_ratios

        ratios = critical_ratios()
        self.assertTrue(all(.15 <= ratio <= .25 for ratio in ratios))
        profiles = {tuple(math.floor(hp * ratio + .5) for hp in (28, 32, 36)) for ratio in ratios}
        self.assertTrue({(6, 7, 7), (7, 7, 8), (7, 8, 8)} <= profiles)
        for index in range(10001):
            ratio = .15 + index/100000
            self.assertIn(tuple(math.floor(hp * ratio + .5) for hp in (28, 32, 36)), profiles)


class PlaytestMetricTests(unittest.TestCase):
    def test_scripted_death_is_distinct_from_completed_ending(self):
        public = dict(game_over=dict(ending="defied_xanxus", reason="Xanxus"),
                      current_location="xanxus_ultimatum", retry_count=0)
        death = explore.ending_record(public, {}, 20)
        self.assertFalse(death["completed"])
        self.assertFalse(death["combat_defeat"])
        public["game_over"] = dict(ending="ignis_defeated", title="冒険完了")
        self.assertTrue(explore.ending_record(public, {}, 21)["completed"])

    def test_seed_rotation_is_stable_for_subsets(self):
        self.assertEqual([explore.preferred_route(s) for s in explore.SEEDS],
                         ["village", "battlefield", "village", "gorge", "battlefield", "gorge", "village", "battlefield"])

    def test_pure_movement_retains_checks_rewards_and_choices_with_flags(self):
        self.assertTrue(metrics.pure_movement(dict(effects=[{"current_location": "village"}, {"background_image": "x"}])))
        for entry in (dict(roll={"dc": 13}), dict(once="visited"), dict(effects=[{"current_location": "village"}, {"set_flag": "clue"}])):
            action = dict(effects=[{"current_location": "village"}])
            action.update(entry)
            self.assertFalse(metrics.pure_movement(action))

    def test_route_priority_applies_only_before_first_chapter_three_entry(self):
        pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        session = checkpoints.fresh_session(pack, "hero")
        session["world_state"] = {"location_id": "forest_exit"}
        self.assertEqual(explore.chapter3_action(session, "village"), "leave_forest_for_village")
        session["visited_locations"] = ["village_approach", "village"]
        self.assertIsNone(explore.chapter3_action(session, "village"))
        session["world_state"] = {"location_id": "bone_field"}
        self.assertEqual(explore.chapter3_action(session, "village"), "sneak_bone_field")
        session["world_state"] = {"location_id": "cave_hot_spring"}
        self.assertEqual(explore.chapter3_action(session, "village"), "follow_hot_spring_water")

    def test_overlap_uses_successful_runs_and_location_option_pairs(self):
        pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        base = dict(character="hero", seed=1, completed=True, ending="ignis_defeated", first_death=None, retry_count=0,
            chapter3_routes=["village"], clue_flags=["heard_guardian_refusal"], final_clue_flags=[],
            invariants=dict(exceptions=0, noncombat_dead_ends=0, fallback_narrations=0),
            visited_locations=["castle", "village"], scenario_choices=[
                dict(location="castle", action_id="a", pure_movement=False),
                dict(location="village", action_id="move", pure_movement=True)])
        other = deepcopy(base)
        other.update(seed=2, visited_locations=["castle", "forest_exit"])
        other["scenario_choices"] += [dict(location="village", action_id="a", pure_movement=False)]
        failed = deepcopy(base)
        failed.update(seed=3, completed=False)
        summary = metrics.summarize([base, other, failed], pack)
        self.assertEqual(summary["overlap"]["choices"]["pairs"], 1)
        self.assertEqual(summary["overlap"]["choices"]["mean"], .5)
        self.assertAlmostEqual(summary["overlap"]["locations"]["mean"], 1/3)
        self.assertEqual(summary["clue_counts"]["heard_guardian_refusal"], 3)
        self.assertEqual(summary["route_counts_by_character"]["hero"], dict(village=3, battlefield=0, gorge=0))
        self.assertEqual(summary["final_clue_counts"]["heard_guardian_refusal"], 0)
        self.assertIn("read_miner_diary", metrics.clue_flags(pack))
        self.assertIn("saw_white_claw", metrics.clue_flags(pack))
        self.assertEqual(metrics.jaccard(set(), set()), 1)
        self.assertIsNone(metrics.summarize([base], pack)["overlap"]["choices"]["mean"])


if __name__ == "__main__":
    unittest.main()
