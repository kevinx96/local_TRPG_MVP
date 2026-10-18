"""Spec 041: matched Lv5 resource checkpoints and un-rested Ignis -> Gareth trials."""
from __future__ import annotations

import argparse
import json
import random
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import combat, state
from . import checkpoints, sim


def battle(session: dict[str, Any], rng: random.Random) -> bool:
    combat.ensure_combat_started(session)
    while combat.combat_is_active(session):
        action, target = sim.choose_action(session, "heuristic", purify=False)
        combat.perform_combat_action(session, action["type"], action["id"], target, rng=rng)
    return session["combat"]["status"] == "victory"


def run(n: int, seed: int = 20261019) -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    # Gareth uses the Lv5 Ignis checkpoint; Draco keeps its established Lv5 preparation.
    source = deepcopy(cp["encounters"]["dragon_valley_loc"])
    for location in ("dragon_valley_return",):
        cp["encounters"][location] = deepcopy(source)
    rows = []
    for character in ("hero", "cleric", "mage", "thief"):
        entry = source["characters"][character]
        if entry.get("level") != 5:
            raise ValueError(f"Expected Lv5: {character}/{entry.get('level')}")
        row: dict[str, Any] = dict(character=character, level=5, n=n)
        for encounter in ("dragon_valley_loc", "dragon_valley_return", "draco_battle"):
            result = sim.simulate(pack, encounter, character, n=n, seed=seed, checkpoints=cp, purify=False)
            row[encounter] = result["win_rate"]
        first_wins = consecutive_wins = 0
        rng = random.Random()
        with patch.object(combat, "random", rng):
            template = sim.prepare_session(pack, "dragon_valley_loc", character, cp)
            for index in range(n):
                rng.seed(sim.trial_seed(seed, "ignis_then_gareth", character, index))
                session = deepcopy(template)
                if not battle(session, rng):
                    continue
                first_wins += 1
                # Apply the actual Ignis rewards; no healing, item use, shopping or rest between fights.
                session["scenario_pack"] = pack
                state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
                combat.clear_combat_after_resolution(session)
                state.commit_world_position(session, location_id="dragon_valley_return")
                session["combat_start_requested"] = True
                consecutive_wins += int(battle(session, rng))
        row.update(ignis_survivors=first_wins, consecutive_wins=consecutive_wins,
                   consecutive_rate=consecutive_wins / n,
                   conditional_rate=consecutive_wins / first_wins if first_wins else 0)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    means = {encounter: sum(row[encounter] for row in rows) / len(rows)
             for encounter in ("dragon_valley_loc", "dragon_valley_return", "draco_battle")}
    return dict(n=n, seed=seed, rows=rows, means=means,
                target_met=means["draco_battle"] < means["dragon_valley_return"] < means["dragon_valley_loc"],
                checkpoint="Gareth copies dragon_valley_loc; Draco uses draco_battle; all Lv5 with full HP/MP/SP and the existing checkpoint loadout",
                enemies=[enemy for enemy in pack["enemies"] if enemy["id"].startswith("dragon_knight_")])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/041-balance.json")
    args = parser.parse_args()
    result = run(args.n)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
