from __future__ import annotations

import unittest
from unittest.mock import patch

from host import state
from scripts.balance import ch34, checkpoints, route


class Chapter34RestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)

    def session(self, location):
        session = checkpoints.fresh_session(self.pack, "hero")
        state.commit_world_position(session, location_id=location)
        session["character"].update(max_hp=100, hp=69, mp=0, sp=0, gold=10)
        return session

    def test_rest_threshold_cost_and_unaffordable_stop(self):
        for location, (action, cost) in route.REST_ACTIONS.items():
            for hp, gold, expected in ((69, cost, True), (70, cost, False), (100, cost, False),
                                       (69, cost - 1, False)):
                if gold < 0:
                    continue
                with self.subTest(location=location, hp=hp, gold=gold):
                    session = self.session(location)
                    session["character"].update(hp=hp, gold=gold)
                    rest = route.rest_if_needed(session)
                    self.assertEqual(rest is not None, expected)
                    self.assertEqual(session["character"]["gold"], gold - (cost if expected else 0))
                    if expected:
                        self.assertEqual(rest["action"], action)
                        self.assertGreater(session["character"]["hp"], hp)
        session = self.session("cave_hot_spring")
        route.rest_if_needed(session)
        session["character"]["hp"] = 1
        self.assertIsNone(route.rest_if_needed(session))

    def test_spring_ambush_battles_and_defeat_are_not_skipped(self):
        for defeated in (False, True):
            session = self.session("elf_spring")
            def fight(session, policy, rng, **kwargs):
                location = state.current_location_id(session)
                if location == "forest_wolves":
                    return {"encounter": location, "status": "victory", "continue": True}
                checkpoints.replay_step(session, "@defeat" if defeated else "@victory")
                if location == "slime_king_battle" and not defeated:
                    session["character"]["hp"] = 1
                return {"encounter": location, "status": "defeat" if defeated else "victory", "continue": not defeated}
            with patch.object(checkpoints, "fresh_session", return_value=session), patch.object(route, "fight", side_effect=fight):
                result = route.trial(self.pack, [dict(location="elf_spring", step="continue_from_elf_spring")],
                                     "forest_wolves", "hero", 1, rest_policy="hp70")
            self.assertEqual(result["completed"], not defeated)
            self.assertEqual(result["paid_rests"], 0)
            self.assertEqual(len(result["rests"]), 1 if defeated else 2)
            self.assertEqual([b["encounter"] for b in result["battles"]],
                             ["slime_ambush_one"] if defeated else
                             ["slime_ambush_one", "slime_ambush_two", "slime_king_battle", "forest_wolves"])

    def test_no_rest_is_reference_and_paid_rest_is_judged(self):
        rows = [dict(preparation="no_rest", character="hero", completion_rate=0),
                dict(preparation="paid_rest", character="hero", completion_rate=.54)]
        self.assertEqual(ch34.violations(dict(encounters=[], routes=rows)),
                         [dict(route="paid_rest", character="hero", value=.54, target=[.55, .90])])
        rows[1]["completion_rate"] = .55
        self.assertEqual(ch34.violations(dict(encounters=[], routes=rows)), [])

    def test_paid_route_visits_refuge_without_forcing_rest(self):
        cp = checkpoints.generate()
        with patch.object(route, "trial", return_value=dict(completed=True, failed_at=None, boss_arrival=None,
                         battles=[], rests=[])) as trial:
            route.simulate_route(self.pack, cp, "hero", n=1, rest_policy="hp70")
        sources = trial.call_args.args[1]
        self.assertIn(dict(location="village_frozen_clue", step="visit_village"), sources)
        self.assertIn(dict(location="village", step="return_frozen_clue"), sources)
        self.assertNotIn("rest_at_refuge", [s["step"] for s in sources])


if __name__ == "__main__":
    unittest.main()
