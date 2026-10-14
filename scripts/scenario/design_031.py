"""Design-lead texts for spec 031: old-battlefield fight openers, the marsh sneak, companion roles (idempotent)."""
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

# Every companion states what it does in battle; Robin gets the covering fire she was always described with.
COMPANIONS = {
    "robin": {"description": "闇の森に詳しい女レンジャー。毎ラウンド開始時に、弓の援護射撃で敵一体へ1d4+1の物理ダメージを与える。罠の扱いにも長けている。",
              "round_start_effects": [{"kind": "damage_enemy", "name": "援護射撃", "damage": "1d4+1", "element": "physical",
                                       "random_target": True}]},
    "blue_robed_mage": {"description": "元素魔法を極めた青いローブの魔法使い。2ラウンドごとに、プレイヤーの最大HPの15%を回復する。"},
    "fire_bat_dragon": {"description": "サラが飼っている小さな火竜。毎ラウンド開始時に敵へ2d3の火属性ダメージを与え、プレイヤーのHPを3回復する（虹晶を食べると6回復）。"},
    "mina": {"description": "魔法店の弟子。好奇心が強く、師匠の言いつけを破って封印の洞窟に入り込んだ。2ラウンドごとに、氷の魔法で敵一体へ1d6のダメージを与える。"},
}
RECRUIT_PREVIEWS = {
    "invite_blue_mage": "同行者として迎える（2ラウンドごとにHPを回復）",
    "invite_robin": "ロビンを仲間に誘う（毎ラウンド弓で援護）",
    "borrow_fire_bat_dragon": "懐いてくれるか確かめる（毎ラウンド敵を焼き、HPを回復）",
    "escort_mina": "同行者にする（2ラウンドごとに氷の魔法で援護）",
}


def _walk(actions: list) -> list:
    found = []
    for action in actions:
        found.append(action)
        found += _walk(action.get("children") or [])
    return found


def apply(pack: dict) -> None:
    locations = {location["id"]: location for location in pack["locations"]}
    for (location_id, action_id), fields in TEXTS.items():
        action = next(a for a in locations[location_id]["actions"] if a["id"] == action_id)
        action.update(json.loads(json.dumps(fields, ensure_ascii=False)))
    for companion in pack["companions"]:
        companion.update(json.loads(json.dumps(COMPANIONS.get(companion["id"], {}), ensure_ascii=False)))
    for location in pack["locations"]:
        for action in _walk(location.get("actions", [])):
            if action["id"] in RECRUIT_PREVIEWS:
                action["preview"] = RECRUIT_PREVIEWS[action["id"]]


def main() -> None:
    for name in PACKS:
        path = DIR / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[design_031] updated {name}")


if __name__ == "__main__":
    main()
