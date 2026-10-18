"""Apply the authored spec 038 loot, collection requests and preparation warnings."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .oaksdawn import action
from .risk_labels import PACKS, ROOT, annotate_risks, movement_destinations
from .upgrade_forest import upsert


LOOT = {
    "slime_core": ("スライムの核", 3, "ぷるぷると震える半透明の核。薬の材料になる。", ("slime", "tutorial_slime", "slime_king")),
    "goblin_trinket": ("ゴブリンの飾り物", 5, "ゴブリンが身につけていた、安物の金属の飾り。",
                       ("goblin", "goblin_archer", "hobgoblin", "goblin_king")),
    "wolf_pelt": ("獣の毛皮", 8, "厚く柔らかな獣の毛皮。", ("forest_wolf", "war_hound")),
    "ember_shard": ("残り火の欠片", 10, "いつまでも冷めない火を宿した、小さな欠片。",
                    ("fire_slime", "fire_elemental", "fire_wisp", "heat_lizard", "xanxus_phantom")),
    "frost_shard": ("霜の欠片", 10, "握ると指先がしびれる、溶けない霜の欠片。",
                    ("ice_elemental", "ice_sentinel", "ice_assassin", "frost_dire_wolf")),
    "crystal_fragment": ("色水晶の欠片", 12, "光にかざすと色を変える水晶の欠片。",
                         ("ruby_golem", "sapphire_moth", "emerald_spider", "prism_tree")),
    "rusted_badge": ("錆びた兵士の徽章", 6, "十年前の兵士がつけていた錆びた徽章。裏に名前が刻まれている。",
                     ("skeleton_soldier", "ghoul", "wraith", "grave_knight")),
    "ash_essence": ("煤の精", 10, "亡霊が崩れた後に残る、黒い煤の塊。", ("ash_wraith",)),
    "drake_scale": ("溶岩竜の鱗", 15, "熱を帯びた赤黒い鱗。鍛冶屋が高く買う。", ("lava_drake",)),
    "beetle_shell": ("甲虫の殻", 8, "砂利を固めたような硬い殻。", ("gravel_beetle", "stone_lizard")),
    "giant_mossstone": ("巨人の苔石", 12, "岩の巨人の体から剥がれた、苔むした石。", ("rock_giant", "earth_worm")),
}
# Design decision (2026-10-18): the three optional bosses drop the shard of their element, two each.
BOSSES = {"slime_king", "goblin_king", "grave_knight", "earth_worm", "frost_dire_wolf", "prism_tree", "xanxus_phantom"}
UNSPECIFIED: set[str] = set()
WARNING = "（強敵の気配がする。心もとないなら、一度王都か城塞へ戻って補給するのも手だ）"
FORT_PREVIEW = "砦の奥には強敵がいるらしい。薬草は足りているか？"
GATE_TEXT = "鉄門の奥から、地を揺らすような唸り声が響いてくる。"
LEAVE_TEXT = "見張りの目を盗んで来た道を引き返し、森の十字路まで戻った。"
SHORTCUT_TEXT = "一度通った道だ。片付けた見張りの跡を抜けて、まっすぐ三階の鉄門へ向かった。"
REQUESTS = (
    dict(id="sarah_scarf", location="item_shop", title="サラの襟巻き", item="wolf_pelt", quantity=2,
         accept="他に頼みごとはある？", deliver="獣の毛皮を渡す", gold=30, reward="healing_scroll",
         request="「冬の前に、母さんにあったかい襟巻きを作ってあげたいの。獣の毛皮が二枚あれば足りるかな」",
         thanks="サラは毛皮を抱きしめて、ぱっと笑った。「ありがとう！ 母さん、きっと喜ぶよ。これ、お礼！」",
         description="道具屋のサラは、母親に襟巻きを編むための獣の毛皮を探している。",
         stage="獣の毛皮を二枚、サラに渡す"),
    dict(id="nameless_soldiers", location="oaksdawn_chapel", title="名もなき兵士たち", item="rusted_badge", quantity=3,
         accept="司祭に話を聞く", deliver="徽章を司祭に渡す", gold=50, reward="holy_water",
         request="「古戦場で倒れた兵たちは、名前すら故郷に届いておりません。もし徽章を見つけたら、ここへ持ってきてはくださらんか」",
         thanks="司祭は徽章の錆を指でぬぐい、刻まれた名前を一つずつ読み上げた。「……これで、皆の家族に知らせを出せます。光のご加護を」",
         description="暁の礼拝堂の老司祭は、古戦場で倒れた兵士たちの徽章を集め、家族に名前を届けたいと願っている。",
         stage="錆びた兵士の徽章を三つ、司祭に渡す"),
    dict(id="refuge_hearth", location="village", title="炊き出しの火", item="ember_shard", quantity=2,
         accept="村人の様子を見る", deliver="残り火の欠片を竈にくべる", gold=40, reward="herb",
         request="村の女が、消えかけた竈の前でため息をついていた。「火の精霊のせいで、薪がすっかり燃え尽きちまってね。……皮肉なもんだけど、冷めない火でもあればねえ」",
         thanks="欠片を竈に落とすと、赤い火がふわりと立ち上がった。避難所に、粥の匂いが広がっていく。「助かったよ。少ないけど、持っていっておくれ」",
         description="麓の村の避難所では、炊き出しの竈の火が消えかけている。",
         stage="残り火の欠片を二つ、竈にくべる"),
)


def apply(pack: dict[str, Any]) -> None:
    locations = {loc["id"]: loc for loc in pack["locations"]}
    enemies = {enemy["id"]: enemy for enemy in pack["enemies"]}
    for identifier, (name, price, description, sources) in LOOT.items():
        upsert(pack["items"], dict(id=identifier, name=name, sell_price=price, description=description,
                                  category="loot", icon=f"/static/images/icon_{identifier}.png"))
        for enemy_id in sources:
            enemies[enemy_id]["loot"] = dict(id=identifier, name=name, quantity=2 if enemy_id in BOSSES else 1)
    items = {item["id"]: item for item in pack["items"]}
    added_actions: dict[str, list[str]] = {}
    workshop = next(shop for shop in pack["shops"] if shop["id"] == "oaksdawn_workshop_shop")
    workshop.update(buys=True, buy_categories=["loot", "equipment"])
    workshop["sell_line"] = "いい素材だね。工房で使わせてもらうよ"
    # Herbs were scarce from chapter 3 on (サラ stocks three); the village shop and the chapel now sell them too.
    for shop_id in ("village_shop", "oaksdawn_chapel_shop"):
        shop = next(entry for entry in pack["shops"] if entry["id"] == shop_id)
        if not any(offer["item_id"] == "herb" for offer in shop["items"]):
            shop["items"].append(dict(item_id="herb", price=10, stock=None))

    for request in REQUESTS:
        identifier = request["id"]
        accepted, completed = f"accepted_{identifier}", f"completed_{identifier}"
        accept = action(f"accept_{identifier}", request["accept"], once=accepted, hidden_after=accepted,
                        result_text=request["request"])
        if identifier == "sarah_scarf":
            accept["visible_requirements"] = {"any": [{"flag": "asked_sarah_request"}, {"flag": "sarah_moss_done"}]}
            accept["requirements"] = deepcopy(accept["visible_requirements"])
        item = items[request["item"]]
        reward = items[request["reward"]]
        requirement = {"has_item": item["name"], "item_quantity_gte": request["quantity"]}
        deliver = action(f"deliver_{identifier}", request["deliver"], [
            {"remove_item": dict(name=item["name"], quantity=request["quantity"])},
            {"add_item": dict(id=reward["id"], name=reward["name"], quantity=2)}, {"gold_change": request["gold"]}],
            once=completed, hidden_after=completed, visible_after=accepted,
            visible_requirements=requirement, requirements={"all": [{"flag": accepted}, requirement]},
            result_text=request["thanks"])
        for entry in (accept, deliver):
            if identifier == "sarah_scarf":
                entry["portrait_image"] = "/static/images/npc_sarah.png"
            upsert(locations[request["location"]]["actions"], entry)
            added_actions.setdefault(request["location"], []).append(entry["id"])
        upsert(pack["quests"], dict(id=f"side_{identifier}", title=request["title"], description=request["description"],
            kind="side", start_flag=accepted, complete_flags=[completed], fail_flags=[],
            stages=[dict(text=request["stage"], done_flag=completed)]))

    gate = locations["goblin_fort_third_gate"]
    if GATE_TEXT not in gate["description"]:
        gate["description"] += GATE_TEXT
    if "summary" in gate.get("hybrid", {}):
        gate["hybrid"]["summary"] = gate["description"]
    upsert(gate["actions"], action("regroup_from_fort_third_gate", "態勢を立て直すため砦を出る",
        [{"current_location": "lost_goblin_crossroads"}, {"set_flag": "fort_third_gate_reached"}], result_text=LEAVE_TEXT))
    added_actions[gate["id"]] = ["regroup_from_fort_third_gate"]
    previews = [("lost_goblin_crossroads", "enter_goblin_fort", FORT_PREVIEW),
                ("inn", "accept_robin_goblin_quest", FORT_PREVIEW),
                ("village", "go_dragon_valley", "この先は邪竜の巣。薬草と回復薬を確かめておけ。"),
                ("festival_town", "go_report_hall", "決着の時が近い。準備は整っているか？")]
    for location, identifier, preview in previews:
        actions = locations[location]["actions"]
        entry = next(a for a in actions if a["id"] == identifier)
        entry.update(preview=preview, preparation_warning=WARNING)
        for choice in locations[location].get("choices", []):
            if choice["text"] == entry["text"]:
                choice["preview"] = preview
        if location in {"lost_goblin_crossroads", "inn"}:
            shortcut = action(f"rush_fort_third_gate_{location}", "砦の三階へ急ぐ",
                [{"current_location": "goblin_fort_third_gate"}], visible_after="fort_third_gate_reached",
                hidden_after="defeated_goblin_king", requirements={"all": [
                    {"flag": "fort_third_gate_reached"}, {"not_flag": "defeated_goblin_king"},
                    {"not_flag": "cleared_goblin_fort"}]},
                result_text=SHORTCUT_TEXT, preparation_warning=WARNING)
            actions[:] = [a for a in actions if a["id"] != shortcut["id"]]
            actions.insert(actions.index(entry) + 1, shortcut)
            added_actions.setdefault(location, []).append(shortcut["id"])
    annotate_risks(pack)
    for identifier, action_ids in added_actions.items():
        location = locations[identifier]
        for index, entry in enumerate(location["actions"]):
            if entry["id"] not in action_ids:
                continue
            choice = {key: deepcopy(value) for key, value in entry.items() if key in {
                "text", "preview", "risk", "requirements", "visible_requirements", "visible_after", "hidden_after", "once"}}
            choices = location.setdefault("choices", [])
            choices[:] = [old for old in choices if old["text"] != entry["text"]]
            preceding = location["actions"][index - 1]["text"] if index else ""
            position = next((i + 1 for i, old in enumerate(choices) if old["text"] == preceding), len(choices))
            choices.insert(position, choice)
            for destination in movement_destinations(entry):
                if destination not in location.setdefault("connected_location_ids", []):
                    location["connected_location_ids"].append(destination)
    pack["meta"]["loot_economy_v038"] = True
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), "2026-10-18-v038")
    if pack["meta"].get("npc_combat_v041"):
        from .npc_combat import apply as apply_npc_combat

        apply_npc_combat(pack)


def main() -> None:
    for filename in PACKS:
        path = ROOT / "host/prompt/processed" / filename
        original = path.read_text(encoding="utf-8")
        pack = json.loads(original)
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2 if '\n  "' in original[:200] else None)
                        + ("\n" if original.endswith("\n") else ""), encoding="utf-8")


if __name__ == "__main__":
    main()
