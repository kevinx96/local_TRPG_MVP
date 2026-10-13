"""Design-lead texts for spec 031's old battlefield: fight openers and the marsh sneak (idempotent)."""
from __future__ import annotations

import json
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "host" / "prompt" / "processed"
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
TEXTS = {
    ("bone_field", "fight_skeleton_soldiers"): {"result_text": "剣を抜いて踏み出すと、骸骨兵たちは錆びた剣を構え、かちかちと顎を鳴らした。"},
    ("ghoul_marsh", "fight_ghoul"): {"result_text": "沼へ足を踏み入れると、泥の中から屍鬼が這い出し、濁った目でこちらを見据えた。"},
    ("ghoul_marsh", "sneak_ghoul_marsh"): {"result_texts": {
        "success": "腐った腕の間を縫うように、沼の縁の倒木を渡りきった。屍鬼たちは泥の中で呻くばかりで、こちらに気づかない。",
        "failure": "倒木が音を立てて折れ、膝まで黒い泥に沈んだ。泥の中から伸びた腕が、足首をつかむ。"}},
    ("ghoul_marsh", "marsh_to_chapel"): {"text": "墓守の礼拝堂へ向かう", "intent_keywords": ["墓守の礼拝堂へ向かう", "礼拝堂へ向かう"]},
    ("grave_chapel", "challenge_grave_knight"): {"result_text": "「その剣、試させてもらう」と告げると、骸骨の騎士は静かに立ち上がり、大剣を両手で構え直した。"},
    ("grave_chapel", "fight_grave_knight"): {"result_text": "骸骨の騎士がゆっくりと立ち上がり、大剣を両手で構えた。兜の奥で、青白い光が揺れている。"},
}


def main() -> None:
    for name in PACKS:
        path = DIR / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        locations = {location["id"]: location for location in pack["locations"]}
        for (location_id, action_id), fields in TEXTS.items():
            action = next(a for a in locations[location_id]["actions"] if a["id"] == action_id)
            action.update(json.loads(json.dumps(fields, ensure_ascii=False)))
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[design_031] updated {name}")


if __name__ == "__main__":
    main()
