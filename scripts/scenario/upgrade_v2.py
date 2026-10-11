from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / "host/prompt/processed"
CLUES = ["frost_trace_seen", "heard_human_caused_dragon_return", "heard_ignis_last_words",
         "noticed_general_frost", "heard_treaty_lore"]


def actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [a for row in rows for a in [row, *actions(row.get("children", []))]]


def upgrade(pack: dict[str, Any]) -> None:
    locations = {l["id"]: l for l in pack["locations"]}
    items = {i["id"]: i for i in pack["items"]}
    for identifier, name, description, effect in [
        ("white_dragon_scale", "白い竜鱗", "雪のように白い竜の鱗。触れると指先が凍える。", "証拠品（戦闘では使えない）"),
        ("ice_crystal", "氷の結晶", "溶けることのない氷のかけら。", "鍛冶屋で氷の護符に加工できる"),
        ("red_dragon_core", "紅竜の炎核", "イグニスの命の炎が宿った結晶。", "火属性の大ダメージ（消耗品）。"),
    ]:
        if identifier not in items:
            item = dict(id=identifier, name=name, description=description, effect=effect)
            pack["items"].append(item)
            items[identifier] = item
    items["red_dragon_core"]["combat"] = dict(kind="damage", damage="1d100+100", accuracy=100, element="fire", consumable=True)
    items["red_dragon_core"]["rare"] = True

    def item(identifier: str, quantity: int = 1) -> dict[str, Any]:
        return dict(id=identifier, name=items[identifier]["name"], quantity=quantity)

    def find(lid: str, aid: str) -> dict[str, Any]:
        return next(a for a in actions(locations[lid]["actions"]) if a["id"] == aid)

    def turn(lid: str, aid: str, text: str, outcome: str = "neutral") -> None:
        turns = locations[lid].setdefault("hybrid", {"mode": "prepared_gm_turns"}).setdefault("prepared_turns", [])
        turns[:] = [t for t in turns if not (t.get("action_id") == aid and t.get("outcome") == outcome)]
        turns.append(dict(id=f"{aid}_{outcome}", purpose="choice_response", action_id=aid, outcome=outcome,
                          draft=dict(gm_text=text, system_log="", state_delta={}, choices=[])))

    def add(lid: str, aid: str, text: str, effects: list[dict[str, Any]], *, preview: str = "",
            result: str = "", parent: str = "", **kwargs: Any) -> dict[str, Any]:
        container = find(lid, parent).setdefault("children", []) if parent else locations[lid]["actions"]
        container[:] = [a for a in container if a["id"] != aid]
        action = dict(id=aid, text=text, preview=preview or text, risk="判定不要", intent_keywords=[text], effects=effects, **kwargs)
        if action.get("roll"):
            action["risk"] = f"{action['roll']['dice_type']}判定（DC{action['roll']['dc']}）"
        container.append(action)
        if result:
            turn(lid, aid, result)
        return action

    def location(identifier: str, scene: str, title: str, description: str, background: str) -> None:
        if identifier in locations:
            return
        row = dict(id=identifier, scene_id=scene, title=title, description=description, actions=[],
                   npc_ids=[], enemy_ids=[], connected_location_ids=[], background_image=background)
        pack["locations"].append(row)
        locations[identifier] = row

    location("ignis_last_breath", "dragon_valley", "竜の谷・紅竜の最期",
             "倒れたイグニスの胸がかすかに上下している。焼け焦げた鱗の隙間、古い傷口だけが、炎の竜には似つかわしくない白い霜に覆われている。",
             "/static/images/bg_dragon_valley.png")
    location("castle_report", "castle_return", "王城・凱旋の間",
             "凱旋を祝う鐘が鳴り、王の間には人々が集まっている。国王エドワードが立ち上がって迎え、その傍らで将軍ドラコが静かに拍手を送っている。",
             "/static/images/bg_dragon_rpg.png")
    location("draco_battle", "castle_return", "王の間・剣聖ドラコ",
             "将軍ドラコが剣を抜く。その刃は氷のように青白く、王の間に霜が広がっていく。", "/static/images/bg_dragon_rpg.png")
    locations["castle_report"]["npc_ids"] = ["king", "general"]
    if not any(s["id"] == "castle_return" for s in pack["scenes"]):
        pack["scenes"].append(dict(id="castle_return", title="王城への帰還", location_ids=["castle_report", "draco_battle"]))
    for scene in pack["scenes"]:
        if scene["id"] == "dragon_valley":
            scene["location_ids"] = ["dragon_valley_loc", "ignis_last_breath"]
            scene["next_scene_ids"] = ["castle_return"]
    supplies = find("castle", "check_supplies")
    supplies["effects"] = [{"branch": {"requirements": {"not_flag": "checked_supplies"},
                                        "then": [{"gold_change": 50}, {"add_item": item("holy_water", 2)}]}}]
    victory = locations["dragon_valley_loc"]["combat"]["victory_effects"]
    victory.pop("game_over", None)
    victory.update(current_location="ignis_last_breath", flags_set=["defeated_ignis"], inventory_add=[item("red_dragon_core")])
    locations["dragon_valley_loc"]["combat"].setdefault("result_texts", {})["victory"] = locations["ignis_last_breath"]["description"]
    find("dragon_valley_loc", "attack_ignis_with_ice_amulet")["success_effects"] = [victory]
    add("ignis_last_breath", "examine_ignis_wound", "イグニスの傷を調べる",
        [{"add_item": item("white_dragon_scale")}, {"set_flag": "examined_ignis_wound"}],
        preview="霜に覆われた古傷を確かめる", once="examined_ignis_wound",
        result="傷口の奥で、雪のように白い鱗が一枚、肉に食い込んだまま凍りついていた。紅竜のものではない。")
    add("ignis_last_breath", "hear_ignis_last_words", "イグニスの最期の言葉を聞く", [{"set_flag": "heard_ignis_last_words"}],
        preview="消えゆく竜の声に耳を傾ける", once="heard_ignis_last_words",
        result="「……白き者に、気をつけよ。盟約を……破ったのは、我ではない……」紅竜の瞳から光が消えた。")
    add("ignis_last_breath", "return_to_castle_report", "王城へ戻り、国王に報告する", [{"current_location": "castle_report"}], preview="凱旋し、討伐を報告する")
    add("castle_report", "report_with_evidence", "将軍ドラコの正体を問いただす",
        [{"set_flag": "draco_revealed"}, {"current_location": "draco_battle"}, {"start_combat": True}],
        requirements={"any": [{"has_item": "白い竜鱗"}, {"flags_count_gte": {"flags": CLUES, "count": 2}}]},
        preview="集めた証拠を国王の前に示す",
        result="あなたが証拠を示すと、王の間が凍りついたように静まり返った。ドラコは小さく笑い、その吐息が白く凍る。「……人の子にしては、よく嗅ぎつけたものだ」")
    normal = "邪竜イグニスは討たれ、王国に平和が戻った。祝宴の夜、杯を掲げる将軍ドラコの瞳が、一瞬だけ雪のように白く光ったことに、気づいた者はいなかった。"
    add("castle_report", "report_normally", "討伐を報告する", [{"game_over": dict(title="冒険完了", ending="ignis_defeated", reason=normal)}],
        preview="イグニス討伐の報告を終える", result=normal)
    add("village_frozen_clue", "inspect_frost_core", "結氷の中心を調べる", [], once="inspected_frost_core",
        roll=dict(dice_type="1d20+wis", dc=12),
        success_effects=[{"add_item": item("white_dragon_scale")}, {"set_flag": "frost_trace_seen"}],
        failure_effects=[{"set_flag": "frost_trace_seen"}])
    turn("village_frozen_clue", "inspect_frost_core", "凍った炎の中心に、白い鱗が一枚埋まっていた。冷気はそこから広がっている。", "success")
    turn("village_frozen_clue", "inspect_frost_core", "冷気の源は分からない。ただ、この氷は自然のものではないと確信した。", "failure")
    add("village", "ask_elder_treaty", "古い盟約について聞く", [{"set_flag": "heard_treaty_lore"}],
        parent="ask_elder_weakness", result="「昔、元素と人と竜は互いを害さぬと誓い合った。北の雪嶺には、盟約を見張る白き竜がいると聞く」")
    # The parent's one-shot weakness answer must not disable the new conversation.
    find("village", "ask_elder_weakness").pop("once", None)
    add("inn", "ask_ian_dragon_tale", "竜と人の昔話を聞く", [{"set_flag": "heard_treaty_lore"}], parent="ask_ian",
        result="「村の鍛冶屋だった頃、祖父がよく言っていた。赤き竜は火を、白き竜は氷を守る。どちらも本来は人の敵じゃない、とな」")
    add("inn", "ask_robin_stolen_scale", "将軍の部屋から盗んだ物を見せてもらう", [{"add_item": item("white_dragon_scale")}],
        parent="ask_robin", once="received_robin_scale", requirements={"all": [{"flag": "recruited_robin"}, {"flag": "cleared_goblin_fort"}]},
        result="「将軍様の部屋で見つけたんだけどさ、売ろうとしたら手が凍りそうになって。あんたが持ってなよ」")
    add("alley_night", "buy_white_scale", "白い鱗を買う", [{"gold_change": -60}, {"add_item": item("white_dragon_scale")}],
        requirements={"all": [{"gold_gte": 60}, {"lacks_item": "白い竜鱗"}]},
        result="「ヒヒ……それは北の雪嶺から落ちてきたものさ。持ち主は案外、近くにいるかもしれないねえ」")
    wolf = locations["frost_wolf_battle"]["combat"]
    wolf["victory_effects"]["inventory_add"] = [item("white_dragon_scale")]
    sentence = "巨狼の核が砕け、中から白い鱗が一枚転がり出た。"
    if sentence not in wolf["result_texts"]["victory"]:
        wolf["result_texts"]["victory"] += sentence
    general = find("castle", "ask_general_advice")
    general["success_effects"] = [{"set_flag": "got_general_advice"}, {"add_item": item("holy_water")}]
    general["roll_bonuses"] = [dict(total_gte=18, effects=[{"set_flag": "noticed_general_frost"}], text="話し終えた将軍の吐息が、なぜか白く凍っていた。")]
    for t in locations["castle"]["hybrid"]["prepared_turns"]:
        if t.get("action_id") == "ask_general_advice" and t.get("outcome") == "success" and "不死の者には聖水が効く" not in t["draft"]["gm_text"]:
            t["draft"]["gm_text"] += "「不死の者には聖水が効く」"
    for lid, oid, name, dc, effects, success in [
        ("castle", "general_breath", "将軍ドラコ", 16, [{"set_flag": "noticed_general_frost"}], "将軍の足元だけ、絨毯にうっすらと霜が降りている。"),
        ("ice_elemental_encounter", "frost_crystal", "路地に散らばる氷の結晶", 12, [{"add_item": item("ice_crystal")}], "氷の結晶を手に入れた。"),
        ("goblin_fort_third_gate", "iron_gate_window", "鉄門の小窓", 13, [{"set_flag": "knows_fort_password"}], "入手した暗号で鉄門を開ける。"),
    ]:
        objects = locations[lid].setdefault("objects", [])
        objects[:] = [o for o in objects if o["id"] != oid]
        objects.append(dict(id=oid, name=name, description=name, observe_reveals=dict(
            roll=dict(dice_type="1d20+wis", dc=dc), once=f"observed_{oid}", success_effects=effects,
            failure_effects=[], success_text=success, failure_text="手がかりは見つからなかった。")))
    locations["ice_elemental_encounter"]["combat"]["victory_effects"]["inventory_add"] = [item("ice_crystal")]
    password = find("goblin_fort_third_gate", "give_correct_password")
    password.pop("visible_after", None)
    password["requirements"] = {"flag": "knows_fort_password"}
    for lid, aid, field in [("goblin_fort_second_right", "bypass_hobgoblin", "success_effects"),
                            ("lost_goblin_crossroads", "help_lost_goblin", "effects")]:
        effect = {"set_flag": "knows_fort_password"}
        target = find(lid, aid).setdefault(field, [])
        if effect not in target:
            target.append(effect)
    locations["goblin_fort_third_gate"]["entry_effects"] = [{"branch": {"requirements": {"all": [{"companion_id": "robin"}, {"not_flag": "knows_fort_password"}]}, "then": [{"set_flag": "knows_fort_password"}]}}]
    locations["goblin_fort_third_gate"]["entry_text"] = "ロビンが暗号を教えてくれた。"
    for identifier, price in [("holy_water", 15), ("ice_charm", 80), ("fireball_scroll", 40)]:
        name = items[identifier]["name"]
        add("item_shop", f"buy_sarah_{identifier}", f"{name}を買う（{price}G）", [{"gold_change": -price}, {"add_item": item(identifier)}],
            parent="sarah_shop", requirements={"gold_gte": price})
    for index in range(1, 4):
        herb = find("item_shop", f"buy_sarah_herb_{index}")
        herb["text"] = herb["text"].replace("5G", "10G")
        herb["intent_keywords"] = [herb["text"]]
        herb["requirements"] = {"gold_gte": 10}
        herb["effects"] = [{"gold_change": -10}, {"add_item": item("herb")}]
        for prepared in locations["item_shop"].get("hybrid", {}).get("prepared_turns", []):
            if prepared.get("action_id") == herb["id"]:
                prepared["draft"]["gm_text"] = prepared["draft"]["gm_text"].replace("5G", "10G")
    add("forge", "forge_ice_charm", "氷の結晶を護符に加工する", [{"gold_change": -20}, {"remove_item": item("ice_crystal")}, {"add_item": item("ice_charm")}],
        requirements={"all": [{"has_item": "氷の結晶"}, {"gold_gte": 20}]})
    # Minimal return paths required by the specified inn and crafting sources.
    add("forest_exit", "return_inn_after_forest", "宿屋へ向かう",
        [{"set_flag": "returned_from_forest"}, {"current_location": "inn"}])
    add("inn", "return_forest_exit", "森を出て麓の村へ向かう", [{"current_location": "forest_exit"}],
        visible_after="returned_from_forest")
    for lid in ("village_frozen_clue", "ian_ice_katana_aftermath"):
        add(lid, "visit_village", "長老に邪竜の弱点を聞く", [{"current_location": "village", "flags_set": ["reached_village"]}])
    add("village", "return_castle_from_village", "城に戻る",
        [{"set_flag": "returned_from_village"}, {"current_location": "castle"}])
    add("castle", "return_village", "麓の村へ向かう", [{"current_location": "village", "flags_set": ["reached_village"]}], visible_after="returned_from_village")
    add("village", "return_frozen_clue", "結氷した場所を探索する", [{"current_location": "village_frozen_clue"}])
    for scene in pack["scenes"]:
        if scene["id"] == "dark_forest" and scene.get("next_scene_ids"):
            scene["next_scene_ids"] = list(dict.fromkeys([*scene["next_scene_ids"], "throne_room"]))
        if scene["id"] == "village" and scene.get("next_scene_ids"):
            scene["next_scene_ids"] = list(dict.fromkeys([*scene["next_scene_ids"], "throne_room"]))
        if scene["id"] == "throne_room" and scene.get("next_scene_ids"):
            scene["next_scene_ids"] = list(dict.fromkeys([*scene["next_scene_ids"], "village"]))
    human = dict(id="draco_human", name="剣聖ドラコ", description="剣聖と称えられた将軍。人の姿のまま、凍てつく剣技を振るう。",
                 hp=25, max_hp=25, attributes=dict(str=16, dex=12, int=14, end=12), element="ice",
                 combat=dict(defense=2, basic_attack=dict(name="剣聖の一閃", damage="1d8+5", accuracy=90, element="physical")),
                 skills=[dict(id="sword_flash", name="剣聖の一閃", kind="attack", damage="1d8+5", accuracy=90, element="physical", ai_weight=3),
                         dict(id="ice_blade", name="氷刃", kind="attack", damage="1d8+4", accuracy=90, element="ice", ai_weight=2),
                         dict(id="guard_stance", name="護衛の構え", kind="defend", guard_multiplier=0.6, duration=2, ai_weight=1)],
                 next_phase="draco_dragon", image="/static/images/npc_general.png",
                 phase_transition_text="ドラコの体が裂け、白い光が王の間を満たす。天井を突き破って現れたのは、雪原のような翼を持つ巨竜だった。「我が名はヴァイス。盟約の番人にして、その終わりを告げる者」")
    dragon = dict(id="draco_dragon", name="白竜ヴァイス", description="将軍ドラコの真の姿。吐息は万物を凍らせる。",
                  hp=220, max_hp=220, attributes=dict(str=20, dex=10, int=20, end=16), element="ice", resistances=dict(fire=1.5, ice=0.25, physical=0.25, holy=0.25),
                  combat=dict(defense=2, basic_attack=dict(name="白翼の薙ぎ払い", damage="1d12+10", accuracy=90, element="physical")),
                  skills=[dict(id="frozen_breath", name="凍てつく吐息", kind="attack", damage="1d12+10", accuracy=90, element="ice", ai_weight=3),
                          dict(id="white_wings", name="白翼の薙ぎ払い", kind="attack", damage="1d12+10", accuracy=90, element="physical", ai_weight=2),
                          dict(id="snow_roar", name="雪嵐の咆哮", kind="status", status_effect="break_guard", ai_weight=1)],
                  image="/static/images/enemy_ignis.png")
    for enemy in (human, dragon):
        enemy["design_todo"] = "TODO(design): 専用のキャラクター画像を選定する。現在は既存画像を仮置き。"
        if not any(e["id"] == enemy["id"] for e in pack["enemies"]):
            pack["enemies"].append(enemy)
    win = "白竜ヴァイスは崩れ落ち、王の間に降り積もった霜が静かに溶けていった。国王エドワードは長い沈黙の後、竜の谷へ使者を送ると告げた。盟約を結び直すために。あなたの名は、竜と人をもう一度つないだ者として語り継がれる。"
    loss = "王の間は永遠の冬に閉ざされた。白竜ヴァイスは王冠を手に取り、新しい時代の始まりを告げた。"
    locations["draco_battle"]["enemy_ids"] = ["draco_human"]
    locations["draco_battle"]["combat"] = dict(auto_start=True, boss=True, encounter_class="boss", flee_allowed=False,
        enemy_ids=["draco_human"], victory_effects={"game_over": dict(title="冒険完了", ending="draco_defeated", reason=win)},
        defeat_effects={"game_over": dict(ending="draco_victory", reason=loss)}, result_texts=dict(victory=win, defeat=loss))
    pack["meta"]["content_revision"] = "2026-10-12-scenario-v2"


def main() -> None:
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = PACKS / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
