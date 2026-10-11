from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .upgrade_forest import ROOT, action, observe, upsert

MOSS_TEXT = "岩陰に、淡く光る苔が生えていた。少し摘み取っておこう。"
MINA_FORGE = "「師匠の代わりに私がやります！助けてもらったお礼です」"


def upgrade(pack: dict[str, Any]) -> None:
    if pack["meta"].get("forest_sidequests"):
        return
    pack["meta"].update(forest_sidequests=True, content_revision="2026-10-12-v015-sidequests")
    loc = {l["id"]: l for l in pack["locations"]}
    shops = {s["id"]: s for s in pack["shops"]}
    for identifier, name, description in [
        ("mina", "見習い魔法使いミーナ", "魔法店の弟子。好奇心が強く、師匠の言いつけを破って封印の洞窟に入り込んだ。"),
        ("gald", "行商人ガルド", "各地を巡る陽気な行商人。森で狼の群れに追われていた。")]:
        upsert(pack["npcs"], dict(id=identifier, name=name, description=description, image=f"/static/images/npc_{identifier}.png"))
    upsert(pack["companions"], dict(id="mina", name="見習い魔法使いミーナ", image="/static/images/npc_mina.png",
        description="魔法店の弟子。好奇心が強く、師匠の言いつけを破って封印の洞窟に入り込んだ。",
        round_start_effects=[dict(kind="damage_enemy", every_n_rounds=2, damage="1d6", element="ice", random_target=True)]))
    loc["magic_shop"]["actions"] += [
        action("ask_mina_missing", "最近変わったことは？", [{"set_flag": "mina_missing_heard"}, {"set_flag": "heard_seal_lore"}],
               once="asked_mina_missing", result_text="「弟子のミーナが戻らない。泉の封印の話をした翌日からだ……」"),
        action("report_mina_safe", "ミーナを無事に連れ帰ったと伝える", [{"add_item": {"name": "MP回復薬", "quantity": 2}}, {"set_flag": "mina_quest_done"},
               {"branch": {"requirements": {"companion_id": "mina"}, "then": [{"clear_companion": True}]}}],
               visible_after="mina_rescued", once="mina_quest_done", result_text="「……世話をかけたな。礼を言う」")]
    loc["elf_spring"].setdefault("objects", []).append(observe("small_footprints", "泉のほとりの小さな足跡",
        "小さな足跡が、泉の裏の岩壁へと続いている。", [{"set_flag": "mina_tracks_found"}], {"dice_type": "1d20+wis", "dc": 10}))
    hot = loc["cave_hot_spring"]
    hot["npc_ids"] = ["mina"]
    hot["npc_requirements"] = {"mina": {"not_flag": "mina_rescued"}}
    loc["magic_shop"]["npc_ids"].append("mina")
    loc["magic_shop"]["npc_requirements"] = {"mina": {"flag": "mina_quest_done"}}
    hot["actions"] += [
        action("talk_mina", "少女に話しかける", [{"set_flag": "met_mina"}], hidden_after="mina_rescued",
               result_text="「た、助けて……！封印を抜けたら戻れなくなっちゃって。奥の大きな水晶の木が怖くて動けないの」", portrait_image="/static/images/npc_mina.png"),
        action("escort_mina", "ミーナを連れて行く", [{"set_companion": "mina"}, {"set_flag": "mina_rescued"}],
               visible_after="met_mina", once="mina_rescued", requirements={"any": [{"not_flag": "mina_waiting"}, {"flag": "cleared_cave_prism_tree"}]}),
        action("leave_mina_wait", "ここで待つよう伝える", [{"set_flag": "mina_waiting"}], visible_after="met_mina", hidden_after="mina_rescued")]
    forge = next(a for a in loc["magic_shop"]["actions"] if a["id"] == "forge_prism_weapon")
    forge["result_variants"] = [dict(requirements={"flag": "mina_quest_done"}, text=MINA_FORGE)]
    for branch in forge["effects"][1:]:
        effects = branch["branch"]["then"]
        item = effects[0]["add_item"]
        improved = deepcopy(item)
        improved["combat"]["accuracy"] += 3
        effects[0] = {"branch": {"requirements": {"flag": "mina_quest_done"}, "then": [{"add_item": improved}], "else": [{"add_item": item}]}}

    loc["item_shop"]["actions"] += [
        action("ask_sarah_request", "何か困っていることはある？", [{"set_flag": "sarah_moss_request"}], once="asked_sarah_request",
               result_text="「お母さんの薬を作りたいんだけど、光苔が足りないの。森の暗いところに生えてるんだって」"),
        action("give_moss_to_sarah", "光苔を渡す", [{"remove_item": {"name": "光苔", "quantity": 1}}, {"set_flag": "sarah_moss_done"}, {"add_item": {"name": "治療の巻物", "quantity": 1}}],
               requirements={"has_item": "光苔"}, once="sarah_moss_done",
               result_text="「わあ、ありがとう！これでお母さんの薬が作れる！お礼に、これからはずっと安くしてあげるね」")]
    for lid, oid, name in (("elf_spring", "glowing_moss_patch", "岩陰で光る苔"), ("cave_hot_spring", "moss_on_wall", "温泉の壁の苔")):
        loc[lid].setdefault("objects", []).append(observe(oid, name, MOSS_TEXT,
            [{"add_item": {"name": "光苔", "quantity": 1}}], once=f"gathered_{oid}"))
    shops["sarah_shop"]["discount"] = dict(flag="sarah_moss_done", multiplier=.8)

    loc["forest_wolves"]["actions"].append(action("abandon_gald", "見捨てて先を急ぐ", [
        {"set_flag": "abandoned_gald"}, {"set_flag": "passed_forest_wolves"}, {"current_location": "forest_exit"}],
        hidden_after="passed_forest_wolves", result_text="背後で荷車の倒れる音がした。振り返らずに森を抜けた。"))
    loc["village"]["actions"].append(action("open_gald_shop", "行商人ガルドの店に入る", open_shop="gald_shop", visible_after="saved_gald"))
    loc["village"]["npc_ids"].append("gald")
    loc["village"]["npc_requirements"] = {"gald": {"flag": "saved_gald"}}
    upsert(pack["shops"], dict(id="gald_shop", location_id="village", keeper_npc="gald", title="行商人ガルド", requirements={"flag": "saved_gald"},
        greeting="よう、命の恩人！安くしとくぜ", buy_line="毎度あり！", sell_line="いい品だな、引き取ろう", poor_line="おっと、それじゃ足りねえな", buys=True,
        on_purchase_flag="visited_gald_shop", items=[dict(item_id=i, price=p, stock=s) for i, p, s in
            (("herb", 8, None), ("holy_water", 12, None), ("ice_charm", 40, 1), ("smoke_bomb", 12, None))]))
    cart = observe("gald_cart", "行商人の荷車", "倒れた荷車が放置されている。散らばった荷物の中に、使えそうな薬草が残っていた。",
                   [{"add_item": {"name": "薬草", "quantity": 1}}], once="searched_gald_cart")
    cart["requirements"] = {"flag": "abandoned_gald"}
    loc["village"].setdefault("objects", []).append(cart)
    town = next(a for a in loc["castle"]["actions"] if a["id"] == "explore_castle_town")
    town["children"].append(action("ask_gald_rumor", "行商人ガルドに声をかける", [{"set_flag": "heard_gald_rumor"}], visible_after="saved_gald",
                                   result_text="「将軍様の屋敷に、夜な夜な白い霧が出るって噂だぜ」", portrait_image="/static/images/npc_gald.png"))

    loc["goblin_fort_fourth"]["combat"]["victory_effects"].setdefault("inventory_add", []).append({"id": "robert_hammer", "name": "刻印のハンマー", "quantity": 1})
    loc["forge"]["actions"] += [
        action("ask_robert_hammer", "浮かない顔をしているが？", [{"set_flag": "robert_hammer_heard"}], once="asked_robert_hammer",
               result_text="「……親父の形見のハンマーを、ゴブリンどもに盗まれた」"),
        action("return_robert_hammer", "刻印のハンマーを返す", [{"remove_item": {"name": "刻印のハンマー", "quantity": 1}}, {"set_flag": "robert_hammer_returned"},
            {"branch": {"requirements": {"any": [{"flag": "bought_adamantite_armor"}, {"has_item": "アダマンタイトの鎧"}]},
                        "then": [{"gold_change": 100}], "else": [{"add_item": {"name": "アダマンタイトの鎧", "quantity": 1}}, {"equip_item": "アダマンタイトの鎧"}]}}],
            requirements={"has_item": "刻印のハンマー"}, once="robert_hammer_returned",
            result_text="「……それは。どこでこれを」ローベルトは長い間ハンマーを握りしめていた。「礼だ。好きな防具を一つ、仕立て直してやる」")]
    next(i for i in shops["forge_shop"]["items"] if i["item_id"] == "adamantite_armor")["on_purchase_flag"] = "bought_adamantite_armor"
    rows = [
        ("side_mina", "見習い魔法使いミーナ", "魔法店の弟子ミーナが、封印の洞窟から戻らないらしい。", ["mina_missing_heard", "met_mina", "mina_tracks_found"], "mina_quest_done",
         [("封印の洞窟でミーナを探す", "met_mina"), ("ミーナを連れ帰る", "mina_rescued"), ("魔法店に報告する", "mina_quest_done")]),
        ("side_sarah", "サラの薬づくり", "サラは、母親の薬に使う光苔を探している。", "sarah_moss_request", "sarah_moss_done", [("光苔を渡す", "sarah_moss_done")]),
        ("side_gald", "行商人ガルド", "狼に追われていた行商人を助けた。", "saved_gald", "visited_gald_shop", [("村でガルドの店を訪ねる", "visited_gald_shop")]),
        ("side_robert", "鍛冶師の形見", "鍛冶師ローベルトは、ゴブリンに盗まれた父の形見のハンマーを探している。", "robert_hammer_heard", "robert_hammer_returned", [("刻印のハンマーを返す", "robert_hammer_returned")]),
    ]
    for qid, title, description, start, done, stages in rows:
        quest = dict(id=qid, title=title, description=description, kind="side", start_flag=start, complete_flags=[done], fail_flags=[],
                     stages=[dict(text=t, done_flag=f) for t, f in stages])
        if qid == "side_robert":
            quest["start_item"] = "robert_hammer"
        pack["quests"].insert(-1, quest)
    def add_clue(value: Any) -> None:
        if isinstance(value, dict):
            if "flags_count_gte" in value:
                flags = value["flags_count_gte"]["flags"]
                if "heard_treaty_lore" in flags and "heard_gald_rumor" not in flags:
                    flags.append("heard_gald_rumor")
            for v in value.values():
                add_clue(v)
        elif isinstance(value, list):
            for v in value:
                add_clue(v)
    add_clue(pack)
    pack["quests"][-1]["clue_flags"].append("heard_gald_rumor")


if __name__ == "__main__":
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
