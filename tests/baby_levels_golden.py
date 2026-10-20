from __future__ import annotations

import json
import hashlib
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from host import state
from host.difficulty import apply_difficulty

OUT = ROOT / ".tmp-test/050"


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items()
                if k not in {"at", "created_at", "updated_at", "timestamp", "id"}}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def generate():
    result = {}
    saves = OUT / "baseline-saves"
    saves.mkdir(exist_ok=True)
    with patch.object(state, "SAVE_DIR", saves):
        for cid in ("hero", "cleric", "mage", "thief"):
            public = state.create_session(character_id=cid, difficulty="baby")
            s = state.load_session(public["id"])
            rows = []
            for flag in ("passed_forest_wolves", "cleared_goblin_fort", "reached_village", "nest_event_seen"):
                state.apply_state_delta(s, {"flags_set": [flag]})
                rows.append(stable({"character": deepcopy(s["character"]), "events": deepcopy(s["event_log"])}))
            if cid == "mage":
                state.apply_state_delta(s, {"clear_skills": True})
            state.save_session(s)
            loaded = state.load_session(s["id"])
            rows.append(stable({"character": loaded["character"], "events": loaded["event_log"]}))
            result[cid] = rows
    return result


if __name__ == "__main__":
    result = generate()
    target = Path(__file__).parent / "fixtures/baby_levels_golden.json"
    if "--verify" in sys.argv:
        assert result == json.loads(target.read_text(encoding="utf-8"))
        print("baby levels: four classes, four milestones, curse, save/load identical")
    else:
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        base = state.load_scenario_pack(state.DEFAULT_SCENARIO)
        (OUT / "baby-pack-before.json").write_text(json.dumps(apply_difficulty(base, "baby"), ensure_ascii=False), encoding="utf-8")
    print(hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True).encode()).hexdigest())
