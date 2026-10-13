from __future__ import annotations

import json
import unittest
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import state
from scripts.balance import checkpoints, pass4, route, sim


class BalancePass4Tests(unittest.TestCase):
    def setUp(self):
        self.targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        self.rows = [dict(route=e, character=c, policy=s["policy"], completion_rate=s["completion_rate"][0])
                     for e, s in self.targets["route_targets"]["routes"].items()
                     for c in self.targets["route_targets"]["characters"]]

    def test_route_targets_read_bounds_spread_and_missing_cells(self):
        self.assertEqual(route.check_results(self.rows, self.targets), [])
        self.rows[0]["completion_rate"] = .80
        self.assertEqual(route.check_results(self.rows, self.targets)[0]["metric"], "class_spread")
        self.rows[0]["completion_rate"] = .901
        self.assertEqual({v["metric"] for v in route.check_results(self.rows, self.targets)},
                         {"completion_rate", "class_spread"})
        self.rows.pop(0)
        self.assertEqual(route.check_results(self.rows, self.targets)[0]["metric"], "missing_or_duplicate")
        self.rows.append(deepcopy(self.rows[0]))
        self.assertEqual(len(route.check_results(self.rows, self.targets)), 2)

    def test_route_uses_configured_targets_and_policy(self):
        self.targets["route_targets"]["routes"]["dragon_valley_loc"]["completion_rate"] = [.60, .80]
        self.assertEqual(len(route.check_results(self.rows, self.targets)), 4)
        self.rows[0]["policy"] = "attack_only"
        self.assertEqual(route.check_results(self.rows, self.targets)[0]["metric"], "missing_or_duplicate")

    def test_resource_metrics_report_only_unless_enabled_and_overrides_preserved(self):
        row = dict(encounter="merchant_battle", encounter_class="boss", character="hero",
                   policy="heuristic", defense_mode="flat", win_rate=.7, hp_left_mean=.8, rounds_median=3)
        self.assertEqual(sim.check_results([row], self.targets, check_resource_metrics=True), [])
        row.update(hp_left_mean=None, rounds_median=100)
        self.assertEqual(sim.check_results([row], self.targets), [])
        self.assertEqual({v["metric"] for v in sim.check_results([row], self.targets, check_resource_metrics=True)},
                         {"hp_left", "rounds"})
        row["win_rate"] = .9
        self.assertEqual(sim.check_results([row], self.targets)[0]["metric"], "win_rate")
        row["policy"] = "attack_only"
        self.assertEqual(sim.check_results([row], self.targets)[0]["metric"], "attack_only_win_rate")

    def test_cli_passes_resource_check_switch(self):
        with patch.object(sim, "simulate", return_value={}), patch.object(sim, "check_results", return_value=[]) as check, patch("builtins.print"):
            for enabled in (False, True):
                args = ["--check", "--n", "1", "--encounters", "forest_wolves", "--characters", "hero"]
                self.assertEqual(sim.main(args + (["--check-resource-metrics"] if enabled else [])), 0)
                self.assertEqual(check.call_args.kwargs["check_resource_metrics"], enabled)


    def test_route_cli_reads_custom_targets_and_returns_failure(self):
        with tempfile.TemporaryDirectory(dir=checkpoints.ROOT / ".tmp-test") as directory:
            target = Path(directory) / "targets.json"
            output = Path(directory) / "out.json"
            self.targets["route_targets"]["routes"] = {
                "goblin_fort_fourth": {"policy": "heuristic", "completion_rate": [.4, .75]}}
            target.write_text(json.dumps(self.targets), encoding="utf-8")
            def simulated(pack, cp, character, **kwargs):
                return dict(route=kwargs["encounter"], character=character, policy="heuristic", completion_rate=.8)
            with patch.object(route, "simulate_route", side_effect=simulated), patch("builtins.print"):
                self.assertEqual(route.main(["--check", "--n", "1", "--targets", str(target),
                                             "--output", str(output)]), 1)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(result["violations"]), 4)
            self.assertEqual({r["route"] for r in result["rows"]}, {"goblin_fort_fourth"})

    def test_inn_recovery_cost_and_real_reward_replay(self):
        pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        original = deepcopy(pack)
        herb = next(i["name"] for i in pack["items"] if i["id"] == "herb")
        candidate = pass4.apply(pack, {"inn_restore": True, "rewards": {"slime": {herb: 3}}})
        self.assertEqual(pack, original)
        self.assertEqual(candidate, pass4.apply(candidate, {"inn_restore": True}))
        session = checkpoints.fresh_session(candidate, "hero")
        session["character"].update(hp=1, mp=0, sp=0, gold=10)
        checkpoints.replay_step(session, "go_castle_town")
        checkpoints.replay_step(session, "go_inn")
        checkpoints.replay_step(session, "rest_at_inn")
        self.assertEqual(session["character"]["gold"], 0)
        for r in ("hp", "mp", "sp"):
            self.assertEqual(session["character"][r], session["character"]["max_" + r])
        with self.assertRaisesRegex(ValueError, "Unavailable checkpoint action"):
            checkpoints.replay_step(session, "rest_at_inn")
        checkpoints.replay_step(session, "return_castle_from_inn")
        checkpoints.replay_step(session, "go_dark_forest:success")
        before = route.resources(session)["inventory"].get(herb, 0)
        checkpoints.replay_step(session, "@victory")
        self.assertEqual(route.resources(session)["inventory"][herb], before + 3)

    def test_endpoint_boss_resources_recorded_for_fort(self):
        pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        for enemy in pack["enemies"]:
            enemy.update(hp=1, max_hp=1)
        cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
        row = route.simulate_route(pack, cp, "hero", encounter="goblin_fort_fourth", n=1)
        self.assertEqual(row["boss_arrivals"], 1)
        self.assertIsNotNone(row["boss_resources_mean"])


if __name__ == "__main__":
    unittest.main()
