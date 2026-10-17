"""Apply spec 031's authored content to both scenario packs, without changing old enemies."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .risk_labels import PACKS, ROOT, annotate_risks
from .upgrade_forest import action, move, upsert


BOOSTS = [
    ("elixir_str", "剛力の霊薬", "str", "飲めば腕に力がみなぎる、古い霊薬。"),
    ("elixir_dex", "迅速の霊薬", "dex", "身のこなしが風のように軽くなる。"),
    ("elixir_int", "叡智の霊薬", "int", "頭の芯まで澄みわたる、青い霊薬。"),
    ("elixir_wis", "祈りの霊薬", "wis", "心が静まり、見えないものの気配に敏くなる。"),
    ("elixir_end", "鉄壁の霊薬", "end", "体が岩のように頑丈になる。"),
    ("fruit_life", "生命の果実", "hp", "赤く熟した不思議な果実。"),
    ("fruit_mana", "魔力の果実", "mp", "青く光る不思議な果実。"),
]
DROPS = {
    "slime_king_battle": ("elixir_end", 1), "goblin_fort_fourth": ("elixir_str", 1),
    "frost_wolf_battle": ("elixir_dex", 1), "cave_prism_tree": ("elixir_int", 1),
    "merchant_battle": ("elixir_wis", 1), "xanxus_phantom_battle": ("fruit_mana", 2),
    "grave_chapel": ("fruit_life", 2),
    **{location: ("fruit_life", 1) for location in (
        "forest_wolves", "goblin_fort_first_second", "goblin_fort_second_right", "goblin_fort_second_left",
        "goblin_fort_third_guards", "cave_heat_corridor", "valley_ledge", "inn_night_ambush")},
    **{location: ("fruit_mana", 1) for location in (
        "village_fire_elemental", "ice_elemental_encounter", "cave_lava_room", "cave_crystal_corridor",
        "valley_entrance", "mansion_corridor", "ghoul_marsh")},
}
STEALS = {
    "goblin_fort_first_second": "fort_second_bypass", "goblin_fort_second_right": "bypass_hobgoblin",
    "ice_elemental_encounter": "bypass_ice_elemental", "cave_heat_corridor": "sneak_heat",
    "cave_crystal_corridor": "sneak_crystal", "valley_entrance": "sneak_through_ash",
    "mansion_corridor": "evade_ice_sentinels", "ghoul_marsh": "sneak_ghoul_marsh",
}
ELITE_REGIONS = {
    "forest": ("forest_wolves",),
    "goblin_fort": ("goblin_fort_first_second", "goblin_fort_second_right",
                    "goblin_fort_second_left", "goblin_fort_third_guards"),
    "sealed_cave": ("cave_heat_corridor", "cave_lava_room", "cave_crystal_corridor"),
    "burning_village": ("village_fire_elemental", "ice_elemental_encounter"),
    "old_battlefield": ("ghoul_marsh",),
    "dragon_valley": ("valley_entrance", "valley_ledge"),
    "general_mansion": ("mansion_corridor",),
    "inn_night_ambush": ("inn_night_ambush",),
}
FRUIT_AMOUNT = 3
CURSED_NAMES = ("呪われた聖剣", "呪われた聖杖", "呪われた水晶球", "呪われた短剣")
CURSED = {"any": [{"has_item": name} for name in CURSED_NAMES]}
UNCURSED = {"all": [{"not_item": name} for name in CURSED_NAMES]}
UNDEAD = ("skeleton_soldier", "ghoul", "wraith", "grave_knight")
BATTLEFIELD = ("old_battlefield", "bone_field", "ruined_watchtower", "ghoul_marsh", "grave_chapel")
TRAP = "「足元、気をつけな」ロビンが金貨の山の陰に仕掛けておいた投げ縄が跳ね上がり、ゴブリン王の足をすくった。王は金貨の山に頭から突っ込み、目を回している。"
EMPOWERED = "砕け散った虹晶の欠片を、火コウモリ竜が嬉しそうについばんだ。小さな炎が、虹色にきらめいている。"
GALD_HINT = "「古戦場の街道は村の裏手への近道だが、亡者が出る。教会の聖水を忘れるなよ」"
ZEBOK_TEXTS = [
    "祭壇の陰から、聞き覚えのある笑い声がした。黒いローブの小柄な商人――ゼボクが、毛むくじゃらの指で骸骨の騎士の兜を撫でている。「おや、我が品を大事にしているようだな。骨どもも、主の匂いには逆らえん。……代価のことは、忘れておらぬぞ」商人の姿は、霧に溶けるように消えた。",
    "「代価は確かに受け取った。客人には道を開けてやれ」ゼボクが手を振ると、骸骨の騎士は静かに頭を垂れた。商人の姿は、霧に溶けるように消えた。",
    "「懲りぬ奴よ。あの夜の借りは、この騎士に返してもらおう」ゼボクの指が鳴ると、骸骨の騎士の眼窩に赤い火が灯った。商人の姿は、霧に溶けるように消えた。",
    "祭壇の陰に、毛むくじゃらの小柄な影が見えた。「人の子か。ここは死者の道……生者が通る道ではないぞ」影は喉の奥で笑い、霧の中へ消えた。",
]


def upgrade_rewards(pack: dict[str, Any]) -> None:
    labels = {entry["id"]: entry["name"] for entry in pack["attribute_defs"]}
    for identifier, name, stat, description in BOOSTS:
        resource = stat in {"hp", "mp"}
        spec = {"kind": "permanent", "consumable": True, "amount": FRUIT_AMOUNT if resource else 2,
                "resource" if resource else "attribute": stat,
                "label": f"最大{stat.upper()}" if resource else labels[stat]}
        upsert(pack["items"], dict(id=identifier, name=name, description=description,
                                  category="consumable", combat=spec))
    locations = {loc["id"]: loc for loc in pack["locations"]}
    names = {item["id"]: item["name"] for item in pack["items"]}
    for identifier, (item, quantity) in DROPS.items():
        if identifier not in locations:
            continue
        loc = locations[identifier]
        loc["combat"]["one_time_reward"] = {
            "flag": f"reward_claimed:{identifier}",
            "items": [dict(id=item, name=names[item], quantity=quantity)],
            "steal_text": f"すれ違いざまに{names[item]}をくすねた。",
        }
        for region, encounters in ELITE_REGIONS.items():
            if identifier in encounters:
                shared = f"elite_fruit_claimed:{region}"
                loc["combat"]["one_time_reward"].update(
                    shared_flags=[shared], blocking_flags=[shared, *[
                        f"reward_claimed:{other}" for other in encounters]])
        if identifier in STEALS:
            entry = next(a for a in loc["actions"] if a["id"] == STEALS[identifier])
            entry["steal_encounter"] = identifier
    locations["forest_wolves"]["obstacles"][0]["steal_encounter"] = "forest_wolves"
    king = locations["goblin_fort_fourth"]["combat"]
    upsert(king.setdefault("encounter_modifiers", []), dict(
        id="robin_trap", requirements={"companion_id": "robin"}, enemy_ids=["goblin_king"],
        enemy_skip_rounds=2, text=TRAP, recovery_text="ゴブリン王が頭を振りながら起き上がった。"))
    bat = next(c for c in pack["companions"] if c["id"] == "fire_bat_dragon")
    bat["description"] = "毎ラウンド開始時に敵へ2d3の火属性ダメージを与え、プレイヤーのHPを3回復する（虹晶を食べた後は6回復）。"
    bat["round_start_effects"] = [e for e in bat["round_start_effects"] if e["kind"] != "heal_player"] + [
        dict(kind="heal_player", amount="3", requirements={"not_flag": "fire_bat_empowered"}),
        dict(kind="heal_player", amount="6", requirements={"flag": "fire_bat_empowered"}),
    ]
    prism = locations["cave_prism_tree"]["combat"]
    condition = {"all": [{"companion_id": "fire_bat_dragon"}, {"not_flag": "fire_bat_empowered"}]}
    prism["victory_bonus_effects"] = [{"branch": {"requirements": condition,
        "then": [{"set_flag": "fire_bat_empowered"}], "else": []}}]
    prism["victory_events"] = [dict(requirements=condition, text=EMPOWERED)]


def add_battlefield(pack: dict[str, Any]) -> None:
    if pack["meta"].get("rewards_battlefield_v031"):
        return
    pack["meta"].update(rewards_battlefield_v031=True, content_revision="2026-10-13-v031")
    locations = {loc["id"]: loc for loc in pack["locations"]}
    for identifier, name, description, hp, damage, accuracy in [
        ("skeleton_soldier", "骸骨兵", "錆びた鎧をまとった、十年前の兵士の骸。", 12, "1d6+2", 70),
        ("ghoul", "屍鬼", "沼の泥から這い出す、腐った死者。", 26, "1d10+3", 70),
        ("wraith", "怨霊", "霧の中に浮かぶ、青白い死者の怨念。", 12, "1d6+2", 70),
        ("grave_knight", "墓守の骸骨騎士", "礼拝堂を守り続ける、大剣の骸骨騎士。", 45, "2d6+3", 70),
    ]:
        upsert(pack["enemies"], dict(id=identifier, name=name, description=description, hp=hp, max_hp=hp,
            attributes={}, element="dark", resistances={"holy": 1.5, "physical": 1, "ice": 1}, skills=[],
            combat={"defense": 0, "evade": 0, "basic_attack": {
                "name": "攻撃", "damage": damage, "accuracy": accuracy, "element": "physical"}},
            rewards={"gold": 0, "items": [], "flags": []}, image=f"/static/images/enemy_{identifier}.png"))
    scene = dict(id="old_battlefield", title="霧の古戦場", location_ids=list(BATTLEFIELD), enemy_ids=list(UNDEAD),
                 description="霧の古戦場", npc_ids=["old_soldier_ghost", "suspicious_merchant"],
                 next_scene_ids=["dark_forest", "village"])
    upsert(pack["scenes"], scene)
    forest_scene = next(s for s in pack["scenes"] if s["id"] == "dark_forest")
    if forest_scene.get("next_scene_ids") and "old_battlefield" not in forest_scene["next_scene_ids"]:
        forest_scene["next_scene_ids"].append("old_battlefield")

    def location(identifier: str, title: str, description: str, background: str) -> dict[str, Any]:
        loc = dict(id=identifier, scene_id="old_battlefield", title=title, description=description,
                   background_image=f"/static/images/{background}.png", actions=[], npc_ids=[], enemy_ids=[],
                   connected_location_ids=[], choices=[])
        upsert(pack["locations"], loc)
        locations[identifier] = loc
        return loc

    start = location("old_battlefield", "霧の古戦場", "森を抜けた先で、街道は白い霧に沈んでいた。草むらには錆びた剣と兜が転がり、折れた軍旗が風に鳴っている。どこか遠くで、弔いの鐘が一度だけ鳴った。", "bg_old_battlefield")
    bone = location("bone_field", "骨の野", "霧の中から、錆びた鎧をまとった骸骨の兵士が二体、ぎこちなく立ち上がった。", "bg_old_battlefield")
    tower = location("ruined_watchtower", "崩れた見張り塔", "半ば崩れた石の塔。中では、半透明の兵士が一人、消えた焚き火の前にうずくまっている。", "bg_ruined_watchtower")
    marsh = location("ghoul_marsh", "屍鬼の沼", "黒い水が淀む沼地。泥の中から、腐った腕が何本も突き出している。", "bg_ghoul_marsh")
    chapel = location("grave_chapel", "墓守の礼拝堂", "古戦場の外れに、屋根の落ちた小さな礼拝堂がある。祭壇の前で、大剣を携えた骸骨の騎士が膝をついている。", "bg_grave_chapel")

    def travel(identifier: str, text: str, destination: str, **extra: Any) -> dict[str, Any]:
        return move(identifier, text, destination, result_text=locations[destination]["description"], **extra)

    entry = travel("enter_old_battlefield", "霧の古戦場を抜けて村の裏手へ向かう", "old_battlefield")
    entry["preview"] = "街道を外れ、古戦場を通る"
    locations["forest_exit"]["actions"].append(entry)
    start["entry_events"] = [
        dict(once="battlefield_warlock_warned", requirements={"companion_id": "blue_robed_mage"}, narrate=True,
             text="ワーロックが足を止めた。「瘴気が濃い……ここでは元素の流れが乱れる。癒やしの術は当てにしないでくれ」"),
        dict(once="battlefield_curse_noticed", requirements=deepcopy(CURSED), narrate=True,
             text="腰の呪いの品が、かすかに脈打った。霧の向こうで、何かがこちらを見ている。"),
    ]
    start["actions"] = [travel("battlefield_to_bones", "骨の野へ進む", "bone_field"),
                         travel("battlefield_to_forest", "森の出口へ戻る", "forest_exit")]
    bone["actions"] = [
        action("fight_skeleton_soldiers", "骸骨兵と戦う", [{"start_combat": True}], hidden_after="passed_bone_field"),
        action("sneak_bone_field", "霧に紛れて抜ける", roll=dict(dice_type="1d20+dex", dc=14),
               hidden_after="passed_bone_field", success_effects=[{"set_flag": "passed_bone_field"}],
               failure_effects=[{"start_combat": True}], result_texts={
                   "success": "骸骨兵が霧の向こうを見つめている隙に、野を抜けた。",
                   "failure": "足元の骨が乾いた音を立て、骸骨兵が一斉にこちらを向いた。"}),
        action("show_curse_to_skeletons", "呪いの品を掲げて通る", [{"set_flag": "passed_bone_field"}],
               requirements=deepcopy(CURSED), secret=True, hidden_after="passed_bone_field",
               result_text="骸骨兵は呪いの品の気配に気づくと、錆びた剣を下ろして道を開けた。"),
        travel("bones_to_tower", "崩れた見張り塔へ向かう", "ruined_watchtower", visible_after="passed_bone_field"),
        travel("bones_to_marsh", "屍鬼の沼へ進む", "ghoul_marsh", visible_after="passed_bone_field"),
        travel("bones_to_battlefield", "霧の古戦場へ戻る", "old_battlefield", visible_after="passed_bone_field"),
    ]
    cloak_text = "崩れた階段の上に、古い衛兵の外套が残っていた。裏地には、死者を鎮める祈りの文句が縫い込まれている。"
    upsert(pack["items"], dict(id="gravekeeper_cloak", name="墓守の外套", category="equipment",
        description=cloak_text, combat={"kind": "armor", "defense": 2, "conditional_defense": {
            "enemy_ids": list(UNDEAD), "location_ids": list(BATTLEFIELD), "amount": 1,
            "description": "霧の古戦場：被ダメージをさらに1軽減"}}))
    tower["npc_ids"] = ["old_soldier_ghost"]
    upsert(pack["npcs"], dict(id="old_soldier_ghost", name="亡霊の兵士", description="半透明の若い兵士",
                             image="/static/images/npc_old_soldier_ghost.png"))
    tower["actions"] = [
        action("talk_old_soldier", "亡霊の兵士に話しかける", [{"set_flag": "heard_old_soldier_ghost"}],
               portrait_image="/static/images/npc_old_soldier_ghost.png",
               result_text="亡霊は顔を上げた。「……十年前、将軍ドラコの進言で、我らは竜の谷へ送られた。谷に着いた夜、白い霜が陣を覆い、気づけば皆ここで骨になっていた。紅竜の炎ではない。あれは、ひどく冷たかった」"),
        action("search_watchtower", "塔の上を調べる", [{"add_item": {"id": "gravekeeper_cloak", "name": "墓守の外套", "quantity": 1}},
               {"equip_item": "墓守の外套"}], once="found_gravekeeper_cloak", result_text=cloak_text),
        action("rest_watchtower", "焚き火に火を入れて休む", [{"restore_full": True}], once="rested_watchtower",
               result_text="消えた焚き火に火を入れ、少しだけ休んだ。亡霊は黙って、その火を見つめていた。"),
        travel("tower_to_bones", "骨の野へ戻る", "bone_field"),
    ]
    marsh["actions"] = [
        action("fight_ghoul", "屍鬼と戦う", [{"start_combat": True}], hidden_after="passed_ghoul_marsh"),
        # TODO(design): spec 未提供沼地潜行的成功/失败正文，沿用引擎判定日志。
        action("sneak_ghoul_marsh", "沼の縁を伝って抜ける", roll=dict(dice_type="1d20+dex", dc=15),
               hidden_after="passed_ghoul_marsh", success_effects=[{"set_flag": "passed_ghoul_marsh"}],
               failure_effects=[{"start_combat": True}]),
        travel("marsh_to_bones", "骨の野へ戻る", "bone_field"),
        travel("marsh_to_chapel", "墓守の礼拝堂", "grave_chapel", visible_after="passed_ghoul_marsh",
               portrait_image="/static/images/npc_zebok_merchant.png"),
    ]
    chapel["entry_events"] = [
        dict(once="battlefield_zebok_seen", requirements={"all": [deepcopy(CURSED), {"flag": "curse_bargain_pending"}, {"not_flag": "curse_price_paid"}]}, narrate=True, text=ZEBOK_TEXTS[0]),
        dict(once="battlefield_zebok_seen", requirements={"all": [deepcopy(CURSED), {"flag": "curse_price_paid"}]}, narrate=True, text=ZEBOK_TEXTS[1]),
        dict(once="battlefield_zebok_seen", requirements={"any": [{"flag": "fought_cursed_merchant"}, {"flag": "zebok_escaped"}]},
             narrate=True, text=ZEBOK_TEXTS[2], effects=[{"set_flag": "battlefield_zebok_hostile"}]),
        dict(once="battlefield_zebok_seen", narrate=True, text=ZEBOK_TEXTS[3]),
    ]
    chapel["actions"] = [
        action("curse_pass_grave_knight", "騎士に道を譲ってもらう", [{"set_flag": "passed_grave_chapel"}],
               requirements=deepcopy(CURSED), secret=True, hidden_after="passed_grave_chapel",
               result_text="骸骨の騎士は大剣を床に突き立て、深く頭を垂れた。祭壇の脇の裏門が、軋みながら開く。"),
        action("challenge_grave_knight", "あえて騎士に挑む", [{"start_combat": True}],
               requirements=deepcopy(CURSED), secret=True, hidden_after="passed_grave_chapel"),
        action("fight_grave_knight", "骸骨の騎士と戦う", [{"start_combat": True}],
               requirements=deepcopy(UNCURSED), secret=True, hidden_after="passed_grave_chapel"),
        action("chapel_to_village", "礼拝堂の裏門から村へ抜ける", [{"set_flag": "reached_village"},
               {"current_location": "village_frozen_clue"}], visible_after="passed_grave_chapel",
               result_text="礼拝堂の裏門を抜けると、坂の下に炎上する麓の村が見えた。村の外れの一角だけが、なぜか白く凍りついている。"),
        travel("chapel_to_marsh", "屍鬼の沼へ進む", "ghoul_marsh"),
    ]
    for loc, ids, category, flag, victory in [
        (bone, ["skeleton_soldier", "skeleton_soldier"], "trash", "passed_bone_field", "骸骨兵は崩れ落ち、ただの骨の山に戻った。"),
        (marsh, ["ghoul", "wraith"], "elite", "passed_ghoul_marsh", "最後の屍鬼が泥の中へ沈んだ。黒い水面に、青く光る果実が一つ浮かんでいる。"),
        (chapel, ["grave_knight"], "boss", "passed_grave_chapel", "骸骨の騎士は、大剣を祭壇に立てかけるように崩れ落ちた。兜の奥から、赤い果実が二つ転がり出た。"),
    ]:
        loc["enemy_ids"] = ids
        loc["combat"] = dict(enemy_ids=deepcopy(ids), auto_start=False, encounter_class=category, boss=category == "boss",
            flee_allowed=False, disable_companion_healing=["blue_robed_mage"], victory_effects={"flags_set": [flag]},
            result_texts={"victory": victory})
    marsh["combat"].update(enemy_variants=[dict(requirements=deepcopy(CURSED), enemy_ids=["ghoul"])],
        encounter_modifiers=[dict(id="curse_slows_ghoul", requirements=deepcopy(CURSED), enemy_ids=["ghoul"],
            enemy_hp_multiplier=0.6, text="屍鬼は呪いの品の気配に怯え、動きが鈍っている。")],
        start_events=[dict(requirements=deepcopy(UNCURSED), text="沼の上に青白い怨霊が浮かび上がり、屍鬼に加勢した。")])
    chapel["combat"]["enemy_first_requirements"] = {"flag": "battlefield_zebok_hostile"}
    betray = next(a for a in locations["alley_night"]["actions"] if a["id"] == "betray_cursed_merchant")
    betray["effects"].append({"set_flag": "fought_cursed_merchant"})
    rumor = next(a for a in locations["castle_town"]["actions"] if a["id"] == "ask_gald_rumor")
    rumor["result_text"] += GALD_HINT
    evidence = next(a for a in locations["castle_report"]["actions"] if a["id"] == "report_with_evidence")
    next(r["flags_count_gte"] for r in evidence["requirements"]["any"] if "flags_count_gte" in r)["flags"].append("heard_old_soldier_ghost")
    for loc in (locations["alley_night"], locations["alley_after"]):
        for entry in loc.get("actions", []):
            if entry.get("portrait_image") == "/static/images/npc_suspicious_merchant.png":
                entry["portrait_image"] = "/static/images/npc_zebok_merchant.png"
    merchant = next(n for n in pack["npcs"] if n["id"] == "suspicious_merchant")
    merchant["image"] = merchant["portrait_image"] = "/static/images/npc_zebok_merchant.png"
    nodes = [dict(id=f"B{i}", label=label, kind=kind, x=x, y=y, location_ids=ids,
                  description=locations[ids[0]]["description"] if ids else label)
             for i, label, kind, x, y, ids in [
                 (1, "霧の古戦場", "start", 10, 50, ["old_battlefield"]),
                 (2, "骨の野", "battle", 30, 50, ["bone_field"]),
                 (3, "崩れた見張り塔", "rest", 45, 18, ["ruined_watchtower"]),
                 (4, "屍鬼の沼", "battle", 60, 72, ["ghoul_marsh"]),
                 (5, "墓守の礼拝堂", "boss", 78, 40, ["grave_chapel"]),
                 (6, "村の裏門", "exit", 92, 50, []),
             ]]
    edges = [dict(**{"from": a, "to": b}, action_id=identifier) for a, b, identifier in [
        ("B1", "B2", "battlefield_to_bones"), ("B2", "B1", "bones_to_battlefield"),
        ("B2", "B3", "bones_to_tower"), ("B3", "B2", "tower_to_bones"),
        ("B2", "B4", "bones_to_marsh"), ("B4", "B2", "marsh_to_bones"),
        ("B4", "B5", "marsh_to_chapel"), ("B5", "B4", "chapel_to_marsh"), ("B5", "B6", "chapel_to_village"),
    ]]
    upsert(pack["maps"], dict(id="old_battlefield", title="霧の古戦場", nodes=nodes, edges=edges))


def finish_battlefield(pack: dict[str, Any]) -> None:
    locations = {loc["id"]: loc for loc in pack["locations"]}
    next(scene for scene in pack["scenes"] if scene["id"] == "old_battlefield")["enemy_ids"] = []
    for identifier in ("old_battlefield", "ruined_watchtower"):
        locations[identifier]["combat"] = {"enemy_ids": [], "auto_start": False}
    for event in locations["grave_chapel"]["entry_events"]:
        if event.get("once") == "battlefield_zebok_seen":
            event["portrait_image"] = "/static/images/npc_zebok_merchant.png"
    knight = next(enemy for enemy in pack["enemies"] if enemy["id"] == "grave_knight")
    knight.update(hp=60, max_hp=60)
    knight["combat"]["basic_attack"]["damage"] = "2d8+5"
    for identifier in BATTLEFIELD:
        loc = locations[identifier]
        for entry in loc["actions"]:
            if entry.get("preview") == entry["text"]:
                entry["preview"] = ""
        if identifier in {"bone_field", "ghoul_marsh", "grave_chapel"}:
            defeat = f"{loc['title']}で力尽きた。冒険はここで終わりを迎える。"
            loc["combat"]["defeat_effects"] = {"game_over": {
                "ending": "combat_defeat", "reason": defeat}}
            loc["combat"]["result_texts"]["defeat"] = defeat
    # Fight openers, the marsh sneak and companion roles are the design lead's final texts.
    from scripts.scenario.design_031 import apply as apply_design
    apply_design(pack)


def upgrade(pack: dict[str, Any]) -> None:
    add_battlefield(pack)
    upgrade_rewards(pack)
    finish_battlefield(pack)
    economy_path = ROOT / "eval/balance/rewards_economy.json"
    if economy_path.exists():
        bonuses = json.loads(economy_path.read_text(encoding="utf-8"))["gold_bonus"]
        for loc in pack["locations"]:
            if loc["id"] in bonuses:
                loc["combat"]["victory_gold_bonus"] = bonuses[loc["id"]]
    annotate_risks(pack)
    from scripts.scenario.equipment_slots import apply as apply_slots
    apply_slots(pack)


def main() -> None:
    for name in PACKS:
        path = ROOT / "host/prompt/processed" / name
        original = path.read_text(encoding="utf-8")
        pack = json.loads(original)
        upgrade(pack)
        indent = 2 if '\n  "' in original[:200] else None
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=indent) + ("\n" if original.endswith("\n") else ""), encoding="utf-8")


if __name__ == "__main__":
    main()
