from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFEAT = "水晶の枝に打ち据えられ、気がつくと泉のほとりに倒れていた。"
GALD = "森狼の群れが、荷車を背にした行商人を追い詰めている。男はこちらに気づき、必死に手を振った。"


def action(identifier: str, text: str, effects: list[dict[str, Any]] | None = None, **extra: Any) -> dict[str, Any]:
    return dict(id=identifier, text=text, preview=text, risk="判定不要", intent_keywords=[text],
                effects=effects or [], **extra)


def move(identifier: str, text: str, destination: str, **extra: Any) -> dict[str, Any]:
    return action(identifier, text, [{"current_location": destination}], **extra)


def observe(identifier: str, name: str, text: str, effects: list[dict[str, Any]],
            roll: dict[str, Any] | None = None, failure: str = "", once: str = "") -> dict[str, Any]:
    return dict(id=identifier, name=name, description=name, traits=[], observe_reveals=dict(
        roll=roll or {"dice_type": "none", "dc": 0}, success_text=text, failure_text=failure,
        success_effects=effects, once=once))


def upsert(records: list[dict[str, Any]], record: dict[str, Any]) -> None:
    old = next((r for r in records if r["id"] == record["id"]), None)
    if old is not None:
        records[records.index(old)] = record
    else:
        records.append(record)


def map_data(pack: dict[str, Any]) -> list[dict[str, Any]]:
    locations = {l["id"]: l for l in pack["locations"]}

    def node(identifier: str, label: str, kind: str, x: int, y: int, ids: list[str], **extra: Any) -> dict[str, Any]:
        return dict(id=identifier, label=label, kind=kind, x=x, y=y, location_ids=ids,
                    description=locations[ids[0]]["description"], **extra)

    def edge(a: str, b: str, action_id: str = "") -> dict[str, Any]:
        return {"from": a, "to": b, **({"action_id": action_id} if action_id else {})}

    forest = dict(id="forest", title="闇の森", nodes=[
        node("F1", "森の入口", "start", 10, 65, ["dark_forest_loc"]),
        node("F2", "迷い子の十字路", "event", 30, 65, ["lost_goblin_crossroads"]),
        node("F3", "精霊の泉", "rest", 50, 65, ["elf_spring", "slime_ambush_one", "slime_ambush_two", "slime_king_battle"]),
        node("F4", "狼の縄張り", "battle", 70, 65, ["forest_wolves"]),
        node("F5", "森の出口", "exit", 90, 65, ["forest_exit"]),
        node("fort", "ゴブリン砦", "branch", 30, 25, [l for l in locations if l.startswith("goblin_fort")], submap="goblin_fort"),
        node("cave", "封印の洞窟", "locked", 60, 25, [l for l in locations if l.startswith("cave_")],
             submap="sealed_cave", locked_until="cave_seal_broken", recommended="推奨 Lv2"),
    ], edges=[edge("F1", "F2", "pass_cleared_forest"), edge("F2", "F3", "crossroads_forward"),
              edge("F3", "F4", "continue_from_elf_spring"), edge("F4", "F5", "pass_cleared_wolves"),
              edge("F2", "fort", "enter_goblin_fort"), edge("F3", "cave", "inspect_spring_wall"),
              edge("fort", "F2"), edge("F2", "F5", "fort_shortcut"),
              edge("F3", "F2", "spring_back"), edge("F2", "F1", "crossroads_back"),
              edge("F4", "F3", "wolves_back"), edge("F5", "F4", "exit_back")])
    fort_rows = [
        ("G1", "ゴブリン砦", "battle", 12, 75, ["goblin_fort"]),
        ("G2", "二階", "battle", 30, 75, ["goblin_fort_first_second", "goblin_fort_second_choice"]),
        ("G3r", "右の通路", "battle", 48, 35, ["goblin_fort_second_right"]),
        ("G3l", "回復法陣", "rest", 48, 75, ["goblin_fort_second_left", "goblin_fort_healing_circle"]),
        ("G4", "三階", "battle", 68, 55, ["goblin_fort_third_gate", "goblin_fort_third_guards"]),
        ("G5", "財宝庫", "treasure", 87, 55, ["goblin_fort_fourth", "goblin_fort_chest_choice", "goblin_fort_chest_fight"]),
    ]
    fort = dict(id="goblin_fort", title="ゴブリン砦", parent="forest", nodes=[node(*r) for r in fort_rows],
                edges=[edge("G1", "G2", "fort_first_bypass"), edge("G2", "G3r", "explore_fort_right"),
                       edge("G2", "G3l", "explore_fort_left"), edge("G3r", "G4", "bypass_hobgoblin"),
                       edge("G3l", "G4", "use_fort_healing_circle"), edge("G4", "G5", "give_correct_password")])
    cave_rows = [("C0", "封印の岩壁", "locked", 10, 65, ["cave_seal"]),
                 ("C1", "熱気の回廊", "battle", 25, 65, ["cave_heat_corridor"]),
                 ("C2", "分かれ道", "branch", 40, 65, ["cave_fork"]),
                 ("C3a", "溶岩の小部屋", "treasure", 56, 25, ["cave_lava_room"]),
                 ("C3b", "地底の温泉", "rest", 56, 75, ["cave_hot_spring"]),
                 ("C4", "水晶の回廊", "battle", 74, 50, ["cave_crystal_corridor"]),
                 ("C5", "虹晶樹の間", "boss", 90, 50, ["cave_prism_tree"])]
    cave = dict(id="sealed_cave", title="封印の洞窟", parent="forest", nodes=[node(*r, recommended="推奨 Lv2") for r in cave_rows],
                edges=[edge("C0", "C1", "enter_open_cave"), edge("C1", "C2", "pass_heat_corridor"),
                       edge("C2", "C3a", "cave_left"), edge("C2", "C3b", "cave_right"),
                       edge("C3a", "C2", "lava_back"), edge("C3b", "C2", "hot_spring_back"),
                       edge("C3a", "C4", "lava_forward"), edge("C3b", "C4", "hot_spring_forward"),
                       edge("C4", "C5", "pass_crystal_corridor"), edge("C5", "C4", "prism_back"),
                       edge("C4", "C2", "crystal_back"), edge("C2", "C1", "fork_back"), edge("C1", "C0", "heat_back")])
    cave["nodes"][0]["locked_until"] = "cave_seal_broken"
    next(e for e in forest["edges"] if e.get("action_id") == "fort_shortcut")["visible_after"] = "resolved_lost_goblin_box"
    return [fort, cave, forest]  # Most specific location ownership first.


def upgrade(pack: dict[str, Any]) -> None:
    if pack["meta"].get("forest_v3"):
        return
    pack["meta"].update(forest_v3=True, content_revision="2026-10-12-v015-forest")
    loc = {l["id"]: l for l in pack["locations"]}
    cross = loc["lost_goblin_crossroads"]
    cross["title"] = "迷い子の十字路"
    accept = cross["actions"][0]
    accept["effects"] = [e for e in accept["effects"] if "current_location" not in e]
    accept["preview"] = "箱を取り戻す手伝いを引き受ける"
    cross["combat"]["victory_effects"] = {}
    # A failed theft encounter also remains at the crossroads.
    cross["actions"][1]["failure_effects"][-1]["branch"]["else"] = []
    cross["actions"] += [move("crossroads_forward", "先へ進む", "elf_spring"),
                         move("enter_goblin_fort", "ゴブリン砦へ向かう", "goblin_fort", visible_after="lost_goblin_quest"),
                         move("crossroads_back", "森の入口へ戻る", "dark_forest_loc"),
                         move("fort_shortcut", "砦の裏口から森の出口へ抜ける", "forest_exit",
                              requirements={"all": [{"flag": "resolved_lost_goblin_box"}, {"flag": "passed_forest_wolves"}]})]
    spring = loc["elf_spring"]
    spring["actions"][1].update(effects=[{"current_location": "forest_wolves"}], risk="判定不要", preview=GALD, result_text=GALD)
    spring["actions"][0]["effects"][-2:] = [{"branch": {"requirements": {"flag": "defeated_slime_king"},
        "then": [], "else": [{"current_location": "slime_ambush_one"}, {"start_combat": True}]}}]
    spring["actions"] += [move("inspect_spring_wall", "泉の奥の岩壁を調べる", "cave_seal"),
                          move("spring_back", "十字路へ戻る", "lost_goblin_crossroads")]
    loc["slime_king_battle"]["combat"]["victory_effects"]["current_location"] = "elf_spring"
    loc["goblin_fort_chest_choice"]["actions"][0]["effects"][-1]["current_location"] = "lost_goblin_crossroads"
    loc["goblin_fort_chest_fight"]["combat"]["victory_effects"]["current_location"] = "lost_goblin_crossroads"
    wolves = loc["forest_wolves"]
    wolves.update(description=GALD, npc_ids=["gald"])
    wolves["combat"]["auto_start"] = False
    wolves["combat"]["victory_effects"].update(flags_set=["passed_forest_wolves", "saved_gald"])
    wolves["combat"]["result_texts"]["victory"] = "「助かった！命の恩人だ。俺はガルド、村でも商売してる。見かけたら寄ってくれ」"
    obstacle = deepcopy(loc["dark_forest_loc"]["obstacles"][0])
    obstacle.update(id="forest_wolves", name="森狼", enemy_id="forest_wolf", description=GALD,
                    destination="forest_exit", resolved_flag="passed_forest_wolves", arrival_text=wolves["combat"]["result_texts"]["victory"],
                    pass_effects=[{"set_flag": "saved_gald"}])
    wolves["obstacles"] = [obstacle]
    wolves["actions"] = [action("fight_forest_wolves", "森狼と戦う", [{"start_combat": True}], hidden_after="passed_forest_wolves"),
                          action("distract_forest_wolves", "携帯食で森狼を誘導する", free_action={"operation": "distract", "target_id": "forest_wolves", "item_id": "trail_ration", "advance": True}, hidden_after="passed_forest_wolves"),
                          action("sneak_forest_wolves", "森狼の脇を潜行して通る", free_action={"operation": "sneak", "target_id": "forest_wolves", "item_id": "", "advance": True}, hidden_after="passed_forest_wolves"),
                          move("pass_cleared_wolves", "先へ進む", "forest_exit", visible_after="passed_forest_wolves"),
                          move("wolves_back", "泉へ戻る", "elf_spring")]
    loc["forest_exit"]["actions"].append(move("exit_back", "狼の縄張りへ戻る", "forest_wolves"))
    pack["milestones"][0].update(trigger_flag="passed_forest_wolves", alternative_flags=[])
    for location in (cross, spring, wolves):
        location["hybrid"]["prepared_turns"] = [t for t in location["hybrid"]["prepared_turns"] if t.get("action_id") not in {"continue_from_elf_spring", "help_lost_goblin"}]
        location["hybrid"]["summary"] = location["description"]

    items = [
        dict(id="prism_shard", name="虹晶の欠片", description="色が絶えず移ろう水晶の欠片。強い魔力を秘めている。", effect="魔法店で武器に加工できる", category="key", key_item=True),
        dict(id="ruby_charm", name="紅玉の護符", description="熱を帯びた赤い宝石の護符。", category="equipment",
             combat={"kind": "equipment", "requires_equipped": True, "damage_taken_multipliers": {"fire": .7}}),
        dict(id="glowing_moss", name="光苔", description="暗い場所で淡く光る苔。薬の材料になる。", category="material"),
        dict(id="robert_hammer", name="刻印のハンマー", description="柄に「ローベルト」の名が刻まれた古い鍛冶ハンマー。", category="key", key_item=True),
    ]
    weapons = [("hero", "剣", "刃の色が敵に応じて移ろう剣。相手の弱点を自ら探り当てる。", "str"),
               ("cleric", "杖", "祈りの光を七色に分ける杖。癒やしの力も高める。", "wis"),
               ("mage", "オーブ", "魔力を敵の弱点の属性へ変える宝珠。", "int"),
               ("thief", "短剣", "刺すたびに色を変える短剣。急所を逃さない。", "dex")]
    forge_effects = [{"remove_item": {"name": "虹晶の欠片", "quantity": 1}}]
    for char, title, description, attr in weapons:
        item = dict(id=f"prism_weapon_{char}", name=f"虹晶の{title}", description=description, category="equipment",
                    combat=dict(kind="weapon", name=f"虹晶の{title}", damage=f"1d10+{attr}/3", accuracy=92, element="weakness"))
        if char == "cleric":
            item["combat"]["skill_healing_bonus"] = 2
        items.append(item)
        forge_effects.append({"branch": {"requirements": {"character_id": char}, "then": [{"add_item": {**item, "quantity": 1}}, {"equip_item": item["name"]}]}})
    for item in items:
        upsert(pack["items"], item)
    loc["magic_shop"]["actions"] += [
        action("ask_seal_lore", "泉の封印について尋ねる", [{"set_flag": "heard_seal_lore"}], result_text="「精霊の泉の裏に古い封印がある。泉と同じ律動を読めば、解くのは難しくない」"),
        action("forge_prism_weapon", "虹晶の欠片を武器に仕立ててもらう", forge_effects,
               requirements={"has_item": "虹晶の欠片"}, result_text="「……面白い欠片だ。少し待っていろ」")]
    rows = [
        ("cave_seal", "泉の奥・封印の岩壁", "泉の裏手の岩壁に、七色に揺らめく魔法陣が刻まれている。陣の奥から、かすかに熱い風が吹き出している。", "sealed_cave"),
        ("cave_heat_corridor", "熱気の回廊", "岩肌が赤く光り、足元から熱気が立ち上る。岩陰で、溶岩をまとったトカゲが舌を鳴らしている。", "lava_cave"),
        ("cave_fork", "分かれ道", "通路が二つに分かれている。左からは溶岩の唸り、右からは水の滴る音と、かすかな人の声が聞こえる。", "lava_cave"),
        ("cave_lava_room", "溶岩の小部屋", "溶岩溜まりの縁に、古い宝箱が置かれている。宝箱の前で、小さな炎の精がいくつも踊っている。", "lava_cave"),
        ("cave_hot_spring", "地底の温泉", "湯気の立ち込める小さな温泉がある。岩の隙間に、ローブ姿の少女が膝を抱えて座り込んでいる。", "lava_cave"),
        ("cave_crystal_corridor", "水晶の回廊", "壁一面に、赤・青・緑の水晶が生えている。足音が響くたび、水晶が震え、形を変えて動き出した。", "crystal_cave"),
        ("cave_prism_tree", "虹晶樹の間", "洞窟の最奥に、七色の水晶でできた大樹がそびえている。枝の一本一本が脈打ち、根元には砕けた魔物たちの水晶が積み重なっている。", "crystal_cave"),
    ]
    for lid, title, description, bg in rows:
        record = dict(id=lid, scene_id="dark_forest", title=title, description=description, actions=[], objects=[],
                      background_image=f"/static/images/bg_{bg}.png", npc_ids=[], enemy_ids=[])
        upsert(pack["locations"], record)
        loc[lid] = record
    seal = loc["cave_seal"]
    seal["objects"] = [observe("seal_glyphs", "魔法陣の文様", "文様の一部が、精霊の泉の水面と同じ律動で明滅している。泉の力で解ける封印らしい。",
                               [{"set_flag": "seal_pattern_known"}], {"dice_type": "1d20+int", "dc": 12}, "複雑な文様の意味は読み取れなかった。")]
    for aid, text, attr, dc, success, failure, cost in [
        ("decode_seal", "魔法陣を解読する", "int", 15, "魔法陣の線を一本ずつなぞると、七色の光がほどけるように消えた。", "光が弾け、指先に痺れが走った。もう一度試すこともできる。", {"sp_change": -2}),
        ("pray_at_seal", "泉の精霊に祈る", "wis", 14, "泉の水面が光り、その輝きが岩壁の魔法陣を静かに溶かしていった。", "泉は静まり返ったままだ。", {"sp_change": -2}),
        ("force_seal", "力ずくで岩壁を砕く", "str", 17, "渾身の一撃で魔法陣ごと岩壁がひび割れ、通路が口を開けた。", "魔法陣に弾き返され、体が岩に叩きつけられた。", {"hp_change": -4})]:
        roll = {"dice_type": f"1d20+{attr}", "dc": dc}
        if aid == "decode_seal":
            roll["dc_overrides"] = [{"requirements": {"any": [{"flag": "seal_pattern_known"}, {"flag": "heard_seal_lore"}]}, "dc": 8}]
        seal["actions"].append(action(aid, text, roll=roll, critical_enabled=False, hidden_after="cave_seal_broken",
            success_effects=[{"set_flag": "cave_seal_broken"}, {"current_location": "cave_heat_corridor"}], failure_effects=[cost], result_texts={"success": success, "failure": failure}))
    seal["actions"] += [action("pour_holy_water_on_seal", "聖水を魔法陣に注ぐ", [{"remove_item": {"name": "聖水", "quantity": 1}}, {"set_flag": "cave_seal_broken"}, {"current_location": "cave_heat_corridor"}],
                               requirements={"has_item": "聖水"}, hidden_after="cave_seal_broken", result_text="聖水が触れた瞬間、魔法陣は白い煙を上げて砕け散った。"),
                        move("enter_open_cave", "洞窟へ進む", "cave_heat_corridor", visible_after="cave_seal_broken"),
                        move("leave_seal", "泉へ戻る", "elf_spring")]
    encounters = [("cave_heat_corridor", ["heat_lizard"] * 2, "cave_fork", "elite"),
                  ("cave_lava_room", ["fire_wisp"] * 3, "", "elite"),
                  ("cave_crystal_corridor", ["ruby_golem", "sapphire_moth", "sapphire_moth", "emerald_spider"], "cave_prism_tree", "elite"),
                  ("cave_prism_tree", ["prism_tree"], "", "boss")]
    for lid, enemies, destination, kind in encounters:
        flag = f"cleared_{lid}"
        victory = {"flags_set": [flag], **({"current_location": destination} if destination else {})}
        if lid == "cave_heat_corridor":
            victory["inventory_add"] = [{"id": "glowing_moss", "name": "光苔", "quantity": 1}]
        if lid == "cave_prism_tree":
            victory["inventory_add"] = [{"id": "prism_shard", "name": "虹晶の欠片", "quantity": 1}]
        loc[lid]["enemy_ids"] = enemies
        loc[lid]["combat"] = dict(enemy_ids=enemies, auto_start=lid in {"cave_lava_room", "cave_prism_tree"},
            encounter_class=kind, boss=kind == "boss", flee_allowed=False, victory_effects=victory,
            defeat_effects={"hp": 1, "current_location": "elf_spring"},
            result_texts={"defeat": DEFEAT if lid == "cave_prism_tree" else "気がつくと泉のほとりに倒れていた。"})
        if destination:
            aid = "heat" if lid == "cave_heat_corridor" else "crystal"
            text, attr, dc = ("岩陰を伝って抜ける", "dex", 13) if aid == "heat" else ("水晶の共鳴が収まるまで息を潜める", "wis", 15)
            loc[lid]["actions"] += [action(f"fight_{aid}", "戦う", [{"start_combat": True}], hidden_after=flag),
                action(f"sneak_{aid}", text, roll={"dice_type": f"1d20+{attr}", "dc": dc}, critical_enabled=False, hidden_after=flag,
                       success_effects=[{"current_location": destination}, {"set_flag": flag}],
                       failure_effects=[{"start_combat": True}, *([{"enemy_first": True}] if aid == "crystal" else [])]),
                move(f"pass_{aid}_corridor", "奥へ進む", destination, visible_after=flag)]
    loc["cave_heat_corridor"]["actions"].append(move("heat_back", "封印の岩壁へ戻る", "cave_seal"))
    loc["cave_fork"]["actions"] = [move("cave_left", "左の通路へ進む", "cave_lava_room"), move("cave_right", "右の通路へ進む", "cave_hot_spring"), move("fork_back", "熱気の回廊へ戻る", "cave_heat_corridor")]
    for lid, prefix in (("cave_lava_room", "lava"), ("cave_hot_spring", "hot_spring")):
        loc[lid]["actions"] += [move(prefix + "_back", "分かれ道へ戻る", "cave_fork"), move(prefix + "_forward", "奥へ進む", "cave_crystal_corridor")]
    loc["cave_lava_room"]["actions"].insert(0, action("open_lava_chest", "宝箱を開ける", [
        {"add_item": {"name": "火球術の巻物", "quantity": 2}}, {"add_item": {"name": "紅玉の護符", "quantity": 1}}, {"equip_item": "紅玉の護符"}],
        visible_after="cleared_cave_lava_room", once="opened_lava_chest", result_text="箱の中には、熱を帯びた巻物と赤い宝石の護符が収められていた。"))
    loc["cave_hot_spring"]["actions"].insert(0, action("rest_hot_spring", "温泉で休む", [{"restore_ratio": .5}], once="rested_hot_spring", result_text="熱い湯に浸かると、疲れがじんわりと溶けていく。"))
    loc["cave_crystal_corridor"]["actions"].append(move("crystal_back", "分かれ道へ戻る", "cave_fork"))
    loc["cave_prism_tree"]["combat"]["result_texts"]["victory"] = "大樹が砕け散ると、その芯から掌ほどの欠片が転がり出た。光にかざすと、色が絶えず移ろっている。"
    loc["cave_prism_tree"]["actions"] = [move("leave_prism_tree", "泉へ戻る", "elf_spring", visible_after="cleared_cave_prism_tree"), move("prism_back", "水晶の回廊へ戻る", "cave_crystal_corridor", visible_after="cleared_cave_prism_tree")]
    scene = next(s for s in pack["scenes"] if s["id"] == "dark_forest")
    scene["location_ids"] += [r[0] for r in rows]
    add_enemies(pack)
    pack["maps"] = map_data(pack)


def add_enemies(pack: dict[str, Any]) -> None:
    rows = [
        ("heat_lizard", "熱岩トカゲ", "溶岩を背負った大トカゲ。噛みつかれると火傷を負う。", "fire", 22, 1, 5, "灼熱の噛みつき", "1d4+1", {"ice": 1.5}),
        ("fire_wisp", "炎のウィスプ", "洞窟の熱から生まれた小さな炎の精。群れて漂う。", "fire", 12, 0, 20, "火の粉", "1d3", {"ice": 1.5, "water": 1.5}),
        ("ruby_golem", "紅晶ゴーレム", "赤い水晶が寄り集まってできた巨人。動きは鈍いが一撃が重い。", "fire", 26, 2, 0, "紅晶の拳", "1d6+1", {"physical": .6, "water": 1.5, "ice": 1.5}),
        ("sapphire_moth", "蒼晶の蝶", "青い水晶の翅を持つ蝶。鱗粉が冷気を帯びている。", "ice", 9, 0, 30, "凍える鱗粉", "1d3", {"fire": 1.5}),
        ("emerald_spider", "翠晶の蜘蛛", "緑の水晶の脚を持つ蜘蛛。毒を含んだ糸を吐く。", "earth", 12, 0, 10, "毒糸", "1d3", {"fire": 1.5}),
        ("prism_tree", "虹晶樹", "七色の水晶でできた大樹。洞窟の魔力を吸い上げ、魔物を生み出してきた。", "fire", 85, 2, 0, "虹の枝打ち", "1d8+2", {"fire": .25, "ice": 1.5, "water": 1.5}),
    ]
    for eid, name, description, element, hp, defense, evade, attack, damage, resistances in rows:
        basic = dict(name=attack, damage=damage, accuracy=85, element="physical" if eid in {"ruby_golem", "prism_tree"} else element)
        status = {"heat_lizard": dict(id="burn", name="火傷", damage="1", duration=2),
                  "sapphire_moth": dict(id="chill", name="凍え", accuracy_penalty=15, duration=2),
                  "emerald_spider": dict(id="poison", name="毒", damage="1", duration=2)}.get(eid)
        if status:
            status["remaining_rounds"] = status.pop("duration")
            basic["on_hit_status"] = status
        enemy = dict(id=eid, name=name, description=description, element=element, hp=hp, max_hp=hp,
                     image=f"/static/images/enemy_{eid}.png", attributes={"str": 8, "int": 8, "dex": 6, "end": 8},
                     combat=dict(basic_attack=basic, defense=defense, evade=evade), resistances=resistances,
                     rewards=dict(gold=0, items=[], flags=[]), skills=[])
        if eid == "ruby_golem":
            enemy["skills"] = [dict(id="ruby_fist", kind="damage", **basic), dict(id="ruby_ray", name="熱線", kind="damage", damage="1d4", accuracy=90, element="fire")]
        if eid == "prism_tree":
            enemy["resistance_cycle"] = dict(every=2, log="虹晶樹の輝きが<色>に変わった。", phases=[
                dict(name="紅", element="fire", resistances={"fire": .25, "water": 1.5, "ice": 1.5}),
                dict(name="蒼", element="ice", resistances={"ice": .25, "fire": 1.5}),
                dict(name="翠", element="earth", resistances={"earth": .25, "fire": 1.5, "wind": 1.5})])
            enemy["skills"] = [dict(id="root_absorb", name="根の吸収", kind="heal", healing="1d6", every_n_rounds=3),
                               dict(id="prism_branch", kind="damage", **basic),
                               dict(id="crystal_rain", name="結晶の雨", kind="damage", damage="1d6+2", accuracy=95, element="current", target="all")]
        upsert(pack["enemies"], enemy)


if __name__ == "__main__":
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
