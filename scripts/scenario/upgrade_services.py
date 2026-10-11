from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host.shops import item_category


ROOT = Path(__file__).resolve().parents[2]
REST_TEXT = "温かいスープと清潔な寝台で、一晩ぐっすりと眠った。体の疲れがすっかり抜けている。"
CLUES = ["frost_trace_seen", "heard_human_caused_dragon_return", "heard_ignis_last_words",
         "noticed_general_frost", "heard_treaty_lore"]


def quests() -> list[dict[str, Any]]:
    rows = [
        ("main_ignis", "main", "紅き邪竜の討伐", "国王エドワードから、王国を脅かす邪竜イグニスの討伐を依頼された。", "",
         [("闇の森を抜け、麓の村へ向かう", "reached_village"), ("竜の谷へ向かう", "entered_dragon_valley"),
          ("邪竜イグニスを倒す", "defeated_ignis"), ("王城へ戻り、国王に報告する", "reported_to_king")], "reported_to_king"),
        ("side_lost_goblin", "side", "迷子のゴブリンの箱", "別の一族に盗まれた箱を取り戻してほしいと、迷子のゴブリンに頼まれた。", "lost_goblin_quest",
         [("ゴブリン砦の最上階へたどり着く", "cleared_goblin_fort"), ("箱を持ち主に返す", "returned_lost_goblin_box")], "returned_lost_goblin_box"),
        ("side_robin", "side", "義賊ロビンの依頼", "ロビンと共に、ゴブリン砦の財宝を取り戻す。", "accepted_robin_goblin_quest",
         [("ゴブリン砦を攻略する", "cleared_goblin_fort")], "cleared_goblin_fort"),
        ("side_ian", "side", "砕けた氷の太刀", "イアンから、氷の太刀を砕いた元凶を追ってほしいと頼まれた。", "accepted_ian_request",
         [("元凶の手がかりを探す", "draco_revealed")], "draco_revealed"),
        ("mystery_frost", "mystery", "凍てつく謎", "炎に包まれた村に、不自然な氷が残されていた。誰の仕業だろうか。",
         ["frost_trace_seen", "heard_ignis_last_words", "noticed_general_frost"],
         [("白い氷の手がかりを集める", "draco_revealed")], "draco_revealed"),
    ]
    result = [dict(id=i, kind=k, title=t, description=d, start_flag=s,
                   stages=[dict(text=text, done_flag=flag) for text, flag in stages],
                   complete_flags=[end], fail_flags=["betrayed_lost_goblin"] if i == "side_lost_goblin" else [])
              for i, k, t, d, s, stages, end in rows]
    result[-1].update(clue_flags=CLUES, clue_item="white_dragon_scale")
    return result


def upgrade(pack: dict[str, Any]) -> None:
    if pack.get("shops"):
        return
    pack["meta"]["content_revision"] = "2026-10-12-services-v012"
    pack["quests"] = quests()
    locations = {loc["id"]: loc for loc in pack["locations"]}
    catalog = {item["name"]: item for item in pack["items"]}
    for item in pack["items"]:
        if item["id"] in {"white_dragon_scale", "red_dragon_core", "fire_seed"}:
            item.update(category="key", key_item=True)
        elif item["id"] == "ice_crystal":
            item["category"] = "material"
        else:
            category = item_category(item)
            if category:
                item["category"] = category

    rows = [
        ("sarah_shop", "item_shop", "sarah", "サラの道具屋", "いらっしゃいませ！今日は何をお探しですか？", "ありがとう！大事に使ってね。", "わあ、いいの？ちゃんと買い取るね。", "うーん、お金が足りないみたい……。", "sarah_shop"),
        ("magic_shop", "magic_shop", "blue_robed_mage", "青のローブ魔法店", "……魔道具なら一通り揃っている。", "扱いには気をつけてくれ。", "悪くない品だ。引き取ろう。", "代金が足りないようだ。", "blue_mage_shop"),
        ("forge_shop", "forge", "blacksmith", "ローベルト鍛冶店", "……用件は。", "手入れは怠るな。", "……預かろう。", "金が足りん。", "buy_equipment"),
        ("village_shop", "village", "shopkeeper", "麓の村の道具屋", "こんな時でも店は開けてるよ。気をつけてな。", "無事を祈ってるよ。", "助かるよ、引き取ろう。", "すまんが、それじゃ足りないな。", "buy_ice_amulet"),
    ]
    pack["shops"] = []
    removed_ids: set[str] = set()
    replacements: dict[str, dict[str, Any]] = {}
    for sid, lid, keeper, title, greeting, buy, sell, poor, old_id in rows:
        loc = locations[lid]
        old = next(a for a in loc["actions"] if a["id"] == old_id)
        actions = old.get("children", [old])
        offers: dict[str, dict[str, Any]] = {}
        keywords = list(old.get("intent_keywords", []))
        for action in actions:
            removed_ids.add(action["id"])
            keywords.extend(action.get("intent_keywords", []))
            effects = action["effects"]
            item = catalog[next(effect["add_item"]["name"] for effect in effects if "add_item" in effect)]
            price = -sum(effect.get("gold_change", 0) for effect in effects)
            limited = bool(action.get("once") or action.get("disabled_after"))
            if item["id"] in offers:
                offers[item["id"]]["stock"] += 1
                continue
            offer = dict(item_id=item["id"], price=price, stock=1 if limited else None)
            requirements = action.get("requirements", {})
            attrs = [req for req in requirements.get("all", []) if "attribute" in req]
            if attrs:
                offer["requirements"] = {"all": attrs}
            if any("equip_item" in effect for effect in effects):
                offer["equip_on_buy"] = True
            offers[item["id"]] = offer
            keywords.append(item["name"])
        removed_ids.add(old_id)
        entry = dict(id=f"open_{sid}", text="店に入る", preview=title, risk="判定不要",
                     open_shop=sid, intent_keywords=list(dict.fromkeys(["店に入る", "買う", "購入", "売却", *keywords])))
        for action in [old, *actions]:
            replacements[action["text"]] = entry
        loc["actions"][loc["actions"].index(old)] = entry
        pack["shops"].append(dict(id=sid, location_id=lid, keeper_npc=keeper, title=title,
                                  greeting=greeting, buy_line=buy, sell_line=sell, poor_line=poor,
                                  items=list(offers.values()), buys=True))

    inn = locations["inn"]
    parent = next(a for a in inn["actions"] if a["id"] == "ask_ian")
    rest = next(a for a in parent["children"] if a["id"] == "rest_at_inn")
    parent["children"].remove(rest)
    old_rest_text = rest["text"]
    rest.update(text="宿で休む（10G）", preview="温かい食事と寝台で疲れを癒す",
                requirements={"gold_gte": 10}, effects=[{"gold_change": -10}, {"restore_full": True}],
                result_text=REST_TEXT)
    rest["intent_keywords"].append("宿で休む")
    inn["actions"].insert(0, rest)

    def clean(node: Any) -> None:
        if isinstance(node, list):
            for value in node:
                clean(value)
        elif isinstance(node, dict):
            if node.get("id") in {"report_normally", "report_with_evidence"} and "effects" in node:
                node["effects"].append({"set_flag": "reported_to_king"})
            for key, value in list(node.items()):
                if key == "prepared_turns":
                    node[key] = [turn for turn in value if turn.get("action_id") not in removed_ids
                                 and turn.get("source_choice") not in replacements
                                 and turn.get("action_id") != "rest_at_inn" and turn.get("source_choice") != old_rest_text]
                elif key in {"choices", "fallback_choices", "choice_seeds"} and isinstance(value, list):
                    new = []
                    seen = set()
                    for choice in value:
                        if not isinstance(choice, dict):
                            new.append(choice)
                            continue
                        if choice.get("text") == old_rest_text:
                            choice = deepcopy(rest)
                        if choice.get("text") in replacements:
                            choice = deepcopy(replacements[choice["text"]])
                            if choice["id"] in seen:
                                continue
                            seen.add(choice["id"])
                        new.append(choice)
                    node[key] = new
                clean(node[key])
    clean(pack)


def main() -> None:
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
