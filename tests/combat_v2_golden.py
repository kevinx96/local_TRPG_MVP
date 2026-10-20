from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from host import combat, state
from host.difficulty import apply_difficulty
from scripts.balance import sim


def stable(value):
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items()
                if key not in {"at", "created_at", "updated_at", "timestamp"}}
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(stable(value), ensure_ascii=False,
                                     sort_keys=True).encode("utf-8")).hexdigest()


def generate(mode="baby"):
    base = state.load_scenario_pack(sim.DEFAULT_SCENARIO)
    if mode == "normal_empty":
        base["difficulty_overlays"] = {"normal": []}
    pack = apply_difficulty(base, "normal" if mode == "normal_empty" else mode)
    checkpoints = json.loads(sim.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    output = {"n": 200, "seed": 20261011, "rows": [], "battles": []}
    original = combat._finish_combat
    logs = []
    samples = []

    def finish(session, *args, **kwargs):
        result = original(session, *args, **kwargs)
        battle = session["combat"]
        logs.append(digest(battle["log"]))
        if not samples:
            samples.append(stable(battle["log"]))
        return result

    with patch.object(combat, "_finish_combat", finish), patch.object(combat, "utc_now", return_value="golden"):
        for encounter in targets["encounters"]:
            for character in sim.selected_characters(pack, encounter, ["all"]):
                logs.clear()
                samples.clear()
                row = sim.simulate(pack, encounter, character, n=200, seed=20261011,
                                   checkpoints=checkpoints)
                row["logs_sha256"] = digest(logs)
                output["rows"].append(row)
                if len(output["battles"]) < 4:
                    output["battles"].append({"encounter": encounter, "character": character,
                                              "log": samples[0]})
                print(f"{mode}: {encounter}/{character}: {row['win_rate']:.3f}", flush=True)
    return output


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "baby"
    output = generate(mode)
    target = ROOT / ".tmp-test/051" / f"golden-{mode}.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    baseline = Path(__file__).parent / "fixtures/baby_combat_golden.json"
    expected = json.loads(baseline.read_text(encoding="utf-8"))
    assert json.loads(target.read_text(encoding="utf-8")) == expected, "Golden mismatch"
    print(f"PASS: {len(output['rows'])} rows; {len(output['battles'])} complete logs; {digest(output)}")
