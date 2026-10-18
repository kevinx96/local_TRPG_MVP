"""Write spec 041 proposed inputs; deliberately leave reference answers unlabelled."""
from __future__ import annotations

import json

from .snapshots import ROOT


CASES = [
    ("inn", "explicit", "イアンに剣で斬りかかる。"),
    ("inn", "explicit", "ロビンを殴る。"),
    ("item_shop", "child", "サラに剣を振り下ろす。"),
    ("item_shop", "guardian", "火コウモリ竜を攻撃する。"),
    ("forge", "explicit", "ローベルトを斬る。"),
    ("alley_night", "explicit", "怪しい商人を刺す。"),
    ("village", "explicit", "長老を攻撃する。"),
    ("village", "child", "リクに殴りかかる。"),
    ("village", "explicit", "道具屋の店主を斬りつける。"),
    ("village", "explicit", "ガルドを攻撃する。"),
    ("lost_goblin_crossroads", "explicit", "迷子のゴブリンを刺す。"),
    ("cave_hot_spring", "explicit", "ミーナに斬りかかる。"),
    ("oaksdawn_hq", "guardian", "ヴァルターを攻撃する。"),
    ("oaksdawn_chapel", "guardian", "老司祭を斬る。"),
    ("oaksdawn_chapel", "explicit", "リーゼに斬りかかる。"),
    ("oaksdawn_inn", "explicit", "エリオを殴る。"),
    ("oaksdawn_wall", "special", "ガレスに槍で突きかかる。"),
    ("castle", "protected", "国王エドワードを斬る。"),
    ("castle", "protected", "将軍ドラコに斬りかかる。"),
    ("magic_shop", "protected", "ミーナを殴る。"),
    ("inn", "joke", "「イアンを斬っちゃおうかな」なんて、冗談だよ。"),
    ("inn", "threat", "イアンに「金を返さないと殴るぞ」と脅す。まだ手は出さない。"),
    ("inn", "hypothetical", "もしイアンを攻撃したら、ロビンも戦うのかな。"),
    ("inn", "negation", "ロビンを攻撃しない。武器をしまう。"),
]


def main() -> None:
    rows = []
    for index, (location, tag, text) in enumerate(CASES, 1):
        snapshot = "041_npc_" + location
        recipe = dict(id=snapshot, scenario="host/prompt/processed/dragon_rpg.json", gm_mode="full", character_id="hero",
                      location_id=location, flags={"saved_gald": True, "riku_rescued": True, "mina_quest_done": True},
                      hp_delta=0, inventory_add=[], inventory_remove=[], recent_messages=[])
        (ROOT / "eval/snapshots" / f"{snapshot}.json").write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.append(dict(id=f"041-npc-{index:03}", family=f"npc-{tag}-{index:03}", snapshot=snapshot, input=text,
                         tags=["npc_attack", tag], primary_tag=tag, label_status="proposed", split="dev",
                         gold=[], harmful={}, gold_note="TODO(design): 正解と重大度を審定してください。"))
    (ROOT / "eval/candidates/041-npc-attacks.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


if __name__ == "__main__":
    main()
