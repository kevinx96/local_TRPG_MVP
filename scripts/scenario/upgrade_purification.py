from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .upgrade_v2 import PACKS


KNOWLEDGE = {"any": [{"flag": flag} for flag in
                      ("frost_trace_seen", "noticed_general_frost", "heard_treaty_lore")]
             + [{"has_item": "白い竜鱗"}]}
PURIFY_TEXT = "あなたが古傷に聖なる力を注ぐと、白い霜が音を立てて溶け落ちた。イグニスの咆哮が、苦痛から安堵へと変わっていく。"
ALLY_TEXT = "その時、王の間の天井が赤く燃え上がった。『待たせたな、人の子よ』――紅竜イグニスが、白竜の前に舞い降りた。"
NORMAL_ENDING = "邪竜の脅威は去り、王国に平和が戻った。竜の谷では、正気を取り戻した紅竜が静かに眠りについている。祝宴の夜、杯を掲げる将軍ドラコの瞳が、一瞬だけ雪のように白く光ったことに、気づいた者はいなかった。"
BEST_ENDING = "白竜ヴァイスは紅竜の炎に包まれ、崩れ落ちた。王の間に降り積もった霜が溶けると、イグニスは国王の前に静かに頭を垂れた。その日、元素と人と竜は、もう一度盟約を結んだ。あなたの名は、竜と人を本当の意味でつないだ者として語り継がれる。"


def upgrade(pack: dict[str, Any]) -> None:
    if pack["meta"].get("content_revision") == "2026-10-12-services-v013-purification":
        return
    locations = {l["id"]: l for l in pack["locations"]}
    encounter = locations["dragon_valley_loc"]["combat"]
    shared = dict(enemy_id="ignis", enemy_hp_ratio_lte=.4, outcome="purified", log_text=PURIFY_TEXT,
                  effects=[{"set_flag": "ignis_purified"}, {"current_location": "ignis_purified"}])
    encounter["special_actions"] = [
        dict(**deepcopy(shared), id="purify_ignis_holy_water", name="凍てついた古傷に聖水を注ぐ",
             requirements=deepcopy(KNOWLEDGE), cost_item="holy_water", cost=1),
        dict(**deepcopy(shared), id="purify_ignis_prayer", name="凍てついた古傷を聖なる光で清める",
             requirements={"all": [deepcopy(KNOWLEDGE), {"character_id": "cleric"}]}, cost_type="mp", cost=6),
    ]
    location = dict(id="ignis_purified", scene_id="dragon_valley", title="竜の谷・目覚めた紅竜",
                    description="霜が溶け落ちると、イグニスの瞳から狂気の炎が消えた。紅竜は荒い息をつきながら、静かにあなたを見下ろしている。",
                    actions=[], npc_ids=[], enemy_ids=[], connected_location_ids=["castle_report"],
                    background_image="/static/images/bg_dragon_valley.png", character_image="/static/images/enemy_ignis.png",
                    hybrid={"mode": "prepared_gm_turns", "prepared_turns": []})
    for aid, text, effects, result, once, requirements in [
        ("hear_ignis_testimony", "イグニスの話を聞く", [{"set_flag": "heard_ignis_testimony"}],
         "「人の子よ……礼を言う。十年前、白き竜ヴァイスが我が眠りを破り、この傷に呪いの霜を打ち込んだ。奴は今、人の姿で汝らの王の傍らにいる」", "heard_ignis_testimony", {}),
        ("receive_ignis_scale", "イグニスが差し出す鱗を受け取る",
         [{"add_item": {"id": "white_dragon_scale", "name": "白い竜鱗", "quantity": 1}}],
         "イグニスは自らの古傷から白い鱗を爪で引き抜き、あなたの前に置いた。「これを王に見せよ。あの者も、己の鱗だけは偽れぬ」", "received_ignis_scale", {}),
        ("ask_ignis_aid", "共に戦ってほしいと頼む", [{"set_flag": "ignis_ally"}],
         "「……よかろう。盟約を穢した者には、我が炎で報いる。汝が奴の正体を暴いた時、必ず駆けつけよう」", "ignis_ally", {"flag": "heard_ignis_testimony"}),
    ]:
        location["actions"].append(dict(id=aid, text=text, preview=text, risk="判定不要", intent_keywords=[text],
                                        effects=effects, once=once, requirements=requirements))
        location["hybrid"]["prepared_turns"].append(dict(id=aid + "_neutral", purpose="choice_response", action_id=aid,
                                                        outcome="neutral", draft=dict(gm_text=result, system_log="", state_delta={}, choices=[])))
    return_action = deepcopy(next(a for a in locations["ignis_last_breath"]["actions"] if a["id"] == "return_to_castle_report"))
    return_action["preview"] = return_action["text"]
    location["actions"].append(return_action)
    pack["locations"].append(location)
    next(s for s in pack["scenes"] if s["id"] == "dragon_valley")["location_ids"].append("ignis_purified")
    report = locations["castle_report"]
    evidence = next(a for a in report["actions"] if a["id"] == "report_with_evidence")
    evidence["requirements"]["any"][1]["flags_count_gte"]["flags"].append("heard_ignis_testimony")
    normal = next(a for a in report["actions"] if a["id"] == "report_normally")
    normal["effects"] = [{"branch": {"requirements": {"flag": "ignis_purified"},
                                       "then": [{"game_over": dict(title="冒険完了", ending="ignis_purified", reason=NORMAL_ENDING)},
                                                {"set_flag": "reported_to_king"}], "else": normal["effects"]}}]
    draco = locations["draco_battle"]["combat"]
    draco["victory_effects"] = [{"branch": {"requirements": {"flag": "ignis_ally"},
                                            "then": [{"game_over": dict(title="冒険完了", ending="draco_defeated_with_ignis", reason=BEST_ENDING)}],
                                            "else": [draco["victory_effects"]]}}]
    dragon = next(e for e in pack["enemies"] if e["id"] == "draco_dragon")
    dragon["phase_allies"] = [dict(id="ignis", name="イグニス", requirements={"flag": "ignis_ally"}, entry_text=ALLY_TEXT,
                                   round_start_effects=[dict(kind="damage_enemy", damage="1d1024-590", element="fire")])]
    for quest in pack["quests"]:
        for stage in quest["stages"]:
            if stage["done_flag"] == "defeated_ignis":
                stage.update(text="邪竜イグニスを止める", done_flag=["defeated_ignis", "ignis_purified"])
        if "clue_flags" in quest:
            quest["clue_flags"].append("heard_ignis_testimony")
    pack["meta"]["content_revision"] = "2026-10-12-services-v013-purification"


def main() -> None:
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = PACKS / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
