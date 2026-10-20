"""Idempotent specs 041/045 migration, shared by both scenario packs."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .risk_labels import PACKS, ROOT, annotate_risks
from .ruby_names import apply as ruby_names
from .upgrade_forest import upsert


BLOCKED = {
    "old_soldier_ghost": "刃は半透明の体をすり抜け、冷たい風だけが残った。亡霊の兵士は悲しげにあなたを見つめている。",
    "generic": "今は、その相手に刃を向けるべき時ではない。",
}
TREASON = {
    "king": "剣を抜いた瞬間、将軍ドラコの刃が先にあなたの喉元へ届いていた。「陛下に刃を向けるとは。……愚かな」 視界が白く凍りつき、あなたの名は反逆者として記録された。",
    "general": "踏み込んだはずの一歩より早く、白い刃があなたの胸を貫いていた。「剣聖に挑むには、早すぎたな」 王城の床に霜が広がり、あなたの名は反逆者として記録された。",
}
FALLEN = {
    "ian": "イアンは古い金槌を握ったまま、カウンターの陰に崩れ落ちた。",
    "robin": "ロビンの弓が床に落ちた。「……あんたを、信じてたのに」",
    "sarah": "火コウモリ竜が床に落ちると、サラは悲鳴を上げて店の奥から逃げ出していった。道具屋には、もう誰もいない。",
    "fire_bat_dragon": "小さな炎が消え、火コウモリ竜は動かなくなった。",
    "blacksmith": "ローベルトは金槌を取り落とし、炉の前に崩れ落ちた。炉の火だけが、変わらず燃えている。",
    "suspicious_merchant": "黒いローブがしぼむように崩れ、中身は煙のように消えた。後には、毛の束と小さな袋だけが残っている。",
    "gald": "陽気な行商人は、荷車にもたれるようにして動かなくなった。",
    "elder": "長老は杖を取り落とし、静かに目を閉じた。",
    "riku": "リクは泣きながら避難所の外へ駆けていった。",
    "shopkeeper": "店主は帳簿を抱えたまま、棚の前に倒れ込んだ。",
    "lost_goblin": "ゴブリンは小さく鳴いて、動かなくなった。",
    "walter": "老騎士は剣を支えに膝をつき、そのまま倒れた。「守護団に……栄光を」",
    "liese": "リーゼの盾が石床に転がった。「光よ……この人を、お赦しください」",
    "oaksdawn_priest": "老司祭は祈りの言葉を最後まで言えずに、祭壇の前に倒れた。",
    "brigitte": "ブリギッテは前掛けを血に染めて、金床の横に崩れ落ちた。",
    "elio": "エリオの周りの水が、ただの水たまりになって床に広がった。",
    "mina": "ミーナは杖を握ったまま、湯けむりの中に倒れた。",
    "warlock": "青いローブが床に広がり、杖の先の光がふっと消えた。棚の小瓶が、一斉に色を失っていく。",
    "xanxus": "炎が掻き消え、骸骨は乾いた音を立てて崩れ落ちた。赤い法衣だけが、灰の上に残っている。法衣の中から、王家の紋が入った封書がこぼれ落ちた。",
}
# TODO(design): 045b draft, awaiting design lead approval.
MINA_SHOP_FALLEN = "ミーナは杖を握ったまま、魔法店の床に倒れた。棚の小瓶だけが、窓からの光を受けて淡く瞬いている。"
DIALOGUE = [
    "「ノクスは南風が好きでな。霧の古戦場から風が吹く日は、機嫌が悪い」",
    "「竜が人に懐くのは珍しいと言われる。だが、こいつは卵の時から俺の外套の中で育った」",
    "「見張りは退屈なくらいがちょうどいい。何も起きないのが一番だ」",
    "「人に飼われた竜がいるなら、人を憎む竜がいても不思議はない。……谷の紅竜も、何かあったのかもしれんな」",
]
CHALLENGE = "ガレスは槍を手に取ると、あなたの前に静かに立ちはだかった。背後で、灰色の飛竜が低く喉を鳴らす。「……血の匂いがする。町の者を手にかけたのは、お前だな」「守護団は民を守るためにある。ここで終わらせる」"
INTERCEPTION = "谷を抜けようとしたとき、頭上を大きな影が横切った。灰色の飛竜が岩棚に降り立ち、その背から竜騎士が槍を構える。「竜を討った英雄、か。だが町の者の血は、竜の血では洗い流せない」「ここで裁く。ノクス、行くぞ」"
TRANSITION = "飛竜ノクスが翼を裂かれ、地に落ちた。ガレスは竜の背から飛び降り、その首を一度だけ撫でる。「……下がっていろ、ノクス」 その瞳が、竜と同じ金色に染まっていく。"
VICTORY = "ガレスは槍を杖にして膝をついた。「民の血を……忘れるな」 飛竜が主をくわえ、灰色の空へ飛び去っていった。"
DEFEAT = "竜騎士の槍があなたを貫いた。「守護団の名において」"
EPILOGUE = "町の人々は、あの日の惨劇を忘れていない。英雄の名が語られるとき、そこには必ず血の影がつきまとった。"
XANXUS_EPILOGUE = "燃える街道に、赤い法衣の灰だけが残された。白竜の企みを知る者が、一人この世から消えた。"
# Template choices within the authored ranges; exact choices are listed in the engineering report.
TEMPLATES = {
    "ian": (14, "1d6+2", 65, "physical"), "robin": (28, "1d8+3", 85, "physical"),
    "blacksmith": (14, "1d6+2", 65, "physical"), "brigitte": (14, "1d6+2", 65, "physical"),
    "elder": (8, "1d4", 60, "physical"), "oaksdawn_priest": (8, "1d4", 60, "physical"),
    "shopkeeper": (8, "1d4", 60, "physical"), "gald": (10, "1d4+1", 60, "physical"),
    "suspicious_merchant": (24, "1d8+2", 75, "physical"), "lost_goblin": (6, "1d4", 60, "physical"),
    "guardian_guard": (18, "1d8+1", 75, "physical"), "fire_bat_dragon": (22, "1d6+3", 85, "fire"),
    "liese": (36, "1d8+3", 90, "holy"), "elio": (26, "1d8+3", 85, "water"),
    "walter": (40, "1d8+3", 90, "physical"), "mina": (16, "1d8+3", 85, "ice"),
}
GUARDIANS = {"ian": [{"npc_id": "robin"}], "robin": [{"npc_id": "ian"}],
    "sarah": [{"npc_id": "fire_bat_dragon"}], "riku": [{"npc_id": "elder"}],
    "walter": [{"npc_id": "guardian_guard", "count": 2}],
    "brigitte": [{"npc_id": "guardian_guard"}],
    "oaksdawn_priest": [{"npc_id": "liese", "requirements": {"not_flag": "recruited_liese"}}]}
COMPANIONS = {"robin": "robin", "fire_bat_dragon": "fire_bat_dragon", "liese": "paladin_liese", "elio": "hydromancer_elio", "mina": "mina", "warlock": "blue_robed_mage"}
TOWNS = {"castle_town", "forge", "inn", "magic_shop", "item_shop", "alley", "alley_night", "village", "festival_town", "ian_ice_katana_aftermath"}
ACTION_NPCS = {
    "rest_at_inn": "ian", "ask_ian": "ian", "ask_robin": "robin", "accept_robin_goblin_quest": "robin",
    "ask_robin_rumor": "robin", "ask_robin_merchant": "robin", "ask_robin_join": "robin",
    "borrow_fire_bat_dragon": "sarah", "ask_sarah_request": "sarah", "give_moss_to_sarah": "sarah",
    "accept_sarah_scarf": "sarah", "deliver_sarah_scarf": "sarah", "ask_gald_rumor": "gald",
    "talk_elder": "elder", "rest_at_refuge": "elder", "return_riku": "riku",
    "ask_mina_missing": "mina", "report_mina_safe": "mina", "talk_mina": "mina", "escort_mina": "mina", "leave_mina_wait": "mina",
    "help_lost_goblin": "lost_goblin", "ignore_lost_goblin": "lost_goblin", "return_lost_goblin_box": "lost_goblin",
    "steal_lost_goblin_box": "lost_goblin", "abandon_gald": "gald",
    "accept_ian_request": "ian", "refuse_ian_after_xanxus": "ian", "refuse_ian_before_xanxus": "ian",
    "greet_walter": "walter", "ask_guardian_refusal": "walter", "request_guardian_letter": "walter",
    "report_battlefield_bell_hq": "walter", "open_gorge_path": "walter",
    "pray_oaksdawn": "oaksdawn_priest", "accept_nameless_soldiers": "oaksdawn_priest", "deliver_nameless_soldiers": "oaksdawn_priest",
    "talk_liese": "liese", "recruit_liese_letter": "liese", "recruit_liese_water": "liese", "recruit_liese_persuade": "liese",
    "ask_battlefield_bell": "liese", "report_battlefield_bell_chapel": "liese",
    "talk_brigitte": "brigitte", "forge_dawn_weapon": "brigitte", "ask_workshop_hearth": "brigitte", "deliver_baked_lava_stone": "brigitte",
    "talk_elio": "elio", "recruit_elio_gold": "elio", "recruit_elio_water": "elio", "recruit_elio_persuade": "elio",
    "elio_flood_worm": "elio", "visit_village": "elder",
    "break_burning_beam": "riku", "climb_to_window": "riku", "douse_with_ice": "riku",
    "ask_blue_mage_rumor": "warlock", "invite_blue_mage": "warlock", "ask_seal_lore": "warlock",
    "refuse_xanxus_with_rescue": "warlock", "call_warlock": "warlock",
}


def both(*requirements: dict[str, Any]) -> dict[str, Any]:
    return {"all": [value for value in requirements if value]}


def action(identifier: str, text: str, **extra: Any) -> dict[str, Any]:
    return dict(id=identifier, text=text, preview="", risk="判定不要", effects=[], **extra)


def attack(identifier: str, name: str, damage: str, accuracy: int, element: str = "physical", **extra: Any) -> dict[str, Any]:
    return dict(id=identifier, name=name, kind="attack", damage=damage, accuracy=accuracy, element=element, **extra)


def apply(pack: dict[str, Any]) -> None:
    locations = {record["id"]: record for record in pack["locations"]}
    upsert(pack["npcs"], dict(id="dragon_knight", name="竜騎士ガレス", description="暁の守護団の竜騎士。飛竜ノクスと城壁の見張り台を巡る。",
                            image="/static/images/npc_dragon_knight.png"))
    upsert(pack["npcs"], dict(id="guardian_guard", name="守護団の衛兵", description="守護団の衛兵", image="/static/images/npc_walter.png"))
    npcs = {record["id"]: record for record in pack["npcs"]}
    for identifier, npc in npcs.items():
        profile: dict[str, Any] = dict(category="protected", blocked_text=BLOCKED["generic"], town=False, guardians=[], aftermath="none")
        if identifier in TREASON:
            profile.update(category="treason", ending_text=TREASON[identifier])
        elif identifier == "old_soldier_ghost":
            profile["blocked_text"] = BLOCKED[identifier]
        elif identifier in TEMPLATES or identifier in {"sarah", "riku"}:
            profile.update(category="child" if identifier in {"sarah", "riku"} else "killable",
                           town=identifier not in {"lost_goblin", "mina"}, guardians=deepcopy(GUARDIANS.get(identifier, [])),
                           fallen_text=FALLEN.get(identifier, ""), aftermath="fled" if identifier in {"sarah", "riku"} else "dead")
            if identifier in TEMPLATES:
                hp, damage, accuracy, element = TEMPLATES[identifier]
                profile["enemy_id"] = f"npc_{identifier}"
                enemy = dict(id=f"npc_{identifier}", npc_id=identifier, name=npc["name"], hp=hp, max_hp=hp,
                             image=npc.get("image", ""), attributes={}, skills=[],
                             combat={"basic_attack": attack("attack", "攻撃", damage, accuracy, element)})
                if identifier == "suspicious_merchant":
                    enemy["combat"]["evade"] = 15
                if identifier == "liese":
                    enemy["skills"] = [enemy["combat"]["basic_attack"],
                        dict(id="healing_prayer", name="癒しの祈り", kind="heal", healing="7", use_below_hp_ratio=.5)]
                upsert(pack["enemies"], enemy)
            if identifier in COMPANIONS:
                profile["companion_id"] = COMPANIONS[identifier]
            if identifier in {"fire_bat_dragon", "elder"}:
                profile["flee_dependents"] = ["sarah" if identifier == "fire_bat_dragon" else "riku"]
            if identifier == "mina":
                profile["locations"] = {"magic_shop": dict(town=True, guardians=[{"npc_id": "warlock"}], fallen_text=MINA_SHOP_FALLEN)}
        elif identifier == "dragon_knight":
            profile.update(category="special", aftermath="withdrawn")
        npc["npc_combat"] = profile
    for location in pack["locations"]:
        location["town_npc_combat"] = location["id"] in TOWNS or location["id"].startswith("oaksdawn_")
    for location_id, npc_id in (("village", "shopkeeper"), ("oaksdawn_chapel", "oaksdawn_priest"), ("oaksdawn_wall", "dragon_knight")):
        locations[location_id]["npc_ids"] = list(dict.fromkeys([*locations[location_id].get("npc_ids", []), npc_id]))
    # Guard-only records must not create a new conversation surface.
    for identifier, companion_id in COMPANIONS.items():
        for companion in pack.get("companions", []):
            if companion["id"] == companion_id:
                companion["npc_id"] = identifier
    for shop in pack.get("shops", []):
        shop["counter_gold"] = {"sarah_shop": 30, "forge_shop": 40, "village_shop": 20,
                                "gald_shop": 50, "gald_capital_shop": 50, "oaksdawn_workshop_shop": 60,
                                "magic_shop": 50}.get(shop["id"], 0)

    def annotate(actions: list[dict[str, Any]], location_id: str, inherited: str = "") -> None:
        for entry in actions:
            identifier = entry["id"]
            owner = ACTION_NPCS.get(identifier) or inherited
            if entry.get("open_shop"):
                owner = next(shop["keeper_npc"] for shop in pack["shops"] if shop["id"] == entry["open_shop"])
            if location_id == "forge" and identifier != "return_castle_from_forge":
                owner = "blacksmith"
            if location_id == "alley_night" and identifier != "leave_night_alley":
                owner = "suspicious_merchant"
            if owner:
                entry["npc_id"] = owner
            if identifier == "return_riku":
                entry["npc_ids_required"] = ["elder"]
            if identifier == "borrow_fire_bat_dragon":
                entry["npc_ids_required"] = ["fire_bat_dragon"]
            annotate(entry.get("children", []), location_id, owner or "")
    for location in pack["locations"]:
        annotate(location.get("actions", []), location["id"])
    for quest in pack.get("quests", []):
        owner = {"side_lost_goblin": "lost_goblin", "side_robin": "robin", "side_ian": "ian", "side_mina": "mina",
                 "side_sarah": "sarah", "side_sarah_scarf": "sarah", "side_gald": "gald", "side_robert": "blacksmith",
                 "side_riku": "riku", "side_battlefield_bell": "liese", "side_workshop_hearth": "brigitte",
                 "side_nameless_soldiers": "oaksdawn_priest"}.get(quest["id"])
        if owner:
            quest["npc_id"] = owner
    # Keep movement routes after removing the actor-dependent choices.
    upsert(locations["ian_ice_katana_aftermath"]["actions"], dict(id="leave_without_ian", text="先へ進む", preview="", risk="危険（戦闘）",
            visible_after="npc_gone_ian", result_text="イアンはもうここにはいない。", effects=[{"current_location": "valley_entrance"}]))
    upsert(locations["goblin_fort_chest_choice"]["actions"], dict(id="leave_without_goblin", text="森の出口へ向かう", preview="", risk="判定不要",
        visible_after="npc_gone_lost_goblin", result_text="迷子のゴブリンはもうここにはいない。", effects=[{"current_location": "forest_exit"}]))
    # Existing scripted fights with these people share the same casualty handling.
    for identifier, npc_id in (("lost_goblin_crossroads", "lost_goblin"), ("goblin_fort_chest_fight", "lost_goblin"),
                               ("merchant_battle", "suspicious_merchant")):
        encounter = locations[identifier]["combat"]
        enemy_ids = encounter.get("enemy_ids") or locations[identifier].get("enemy_ids", [])
        encounter.update(npc_participants=[npc_id], npc_enemy_map={eid: npc_id for eid in enemy_ids},
                         npc_town=npc_id == "suspicious_merchant")

    mounted = attack("dragon_charge", "竜槍の突撃", "1d8+4", 85)
    human = attack("dragon_blood_spear", "竜血の槍", "1d10+5", 90)
    upsert(pack["enemies"], dict(id="dragon_knight_mounted", name="竜騎士ガレスと飛竜ノクス", hp=90, max_hp=90,
        attributes={}, image="/static/images/enemy_dragon_knight_mounted.png", combat={"defense": 2, "evade": 6, "basic_attack": mounted},
        skills=[mounted, attack("grey_wind", "灰風の息吹", "1d8+4", 90, "wind"), attack("dive", "急降下", "1d8+4", 70)],
        resistances={"physical": .75, "wind": 0, "ice": 1.5, "lightning": 1.5}, next_phase="dragon_knight_human", phase_transition_text=TRANSITION))
    upsert(pack["enemies"], dict(id="dragon_knight_human", name="竜騎士ガレス", hp=65, max_hp=65, attributes={},
        image="/static/images/enemy_dragon_knight.png", combat={"defense": 3, "evade": 10, "basic_attack": human},
        skills=[human, attack("piercing_spear", "穿竜突き", "1d10+5", 100, ignores_defense=True),
                dict(id="dragon_stance", name="竜騎士の構え", kind="defend")], resistances={"physical": .85, "wind": .5}))
    upsert(pack["items"], dict(id="grey_dragon_scale", name="灰竜の鱗", category="loot", sell_price=30,
                             description="灰竜の鱗", icon="/static/images/icon_grey_dragon_scale.png"))
    encounter = dict(enemy_ids=["dragon_knight_mounted"], boss=True, encounter_class="boss", auto_start=True, flee_allowed=False,
        victory_effects={"gold_change": 30, "inventory_add": [{"id": "grey_dragon_scale", "name": "灰竜の鱗", "quantity": 1}],
                         "flags_set": ["dragon_knight_defeated"]},
        result_texts={"victory": VICTORY, "defeat": DEFEAT},
        defeat_effects={"hp": 0, "game_over": {"ending": "combat_defeat", "reason": DEFEAT}})
    pack["npc_combat"] = dict(dialogue=DIALOGUE, challenge_text=CHALLENGE, interception_text=INTERCEPTION, dragon_encounter=encounter)
    wall = locations["oaksdawn_wall"]
    upsert(wall["actions"], action("talk_dragon_knight", "竜騎士と話す", npc_id="dragon_knight", dragon_knight=True,
                                  result_text=DIALOGUE[0], hidden_after="town_blood"))
    upsert(wall["actions"], dict(id="challenge_dragon_knight", text="竜騎士に話しかける", preview="", risk="危険（戦闘）",
                               npc_id="dragon_knight", dragon_knight=True, visible_after="town_blood", result_text=CHALLENGE, effects=[]))
    interception_encounter = deepcopy(encounter)
    interception_encounter["victory_effects"]["current_location"] = "royal_gate"
    interception_encounter["intro_text"] = INTERCEPTION
    upsert(pack["locations"], dict(id="dragon_valley_return", scene_id="dragon_valley", title="竜の谷・帰路", description=INTERCEPTION,
        background_image="/static/images/bg_dragon_valley.png", npc_ids=[], enemy_ids=["dragon_knight_mounted"], actions=[], choices=[],
        connected_location_ids=["royal_gate"], combat=interception_encounter))
    scene = next(scene for scene in pack["scenes"] if scene["id"] == "dragon_valley")
    scene["location_ids"] = list(dict.fromkeys([*scene["location_ids"], "dragon_valley_return"]))
    for area in pack.get("maps", []):
        if area["id"] == "dragon_valley":
            node = next(node for node in area["nodes"] if "ignis_last_breath" in node["location_ids"])
            node["location_ids"] = list(dict.fromkeys([*node["location_ids"], "dragon_valley_return"]))
    for identifier in ("ignis_last_breath", "ignis_purified"):
        entry = next(a for a in locations[identifier]["actions"] if a["id"] == "return_to_castle_report")
        entry["effects"] = [{"branch": {"requirements": both({"flag": "town_blood"}, {"not_flag": "dragon_knight_defeated"}),
            "then": [{"current_location": "dragon_valley_return"}], "else": [{"current_location": "royal_gate"}]}}]
        entry["result_variants"] = [{"requirements": both({"flag": "town_blood"}, {"not_flag": "dragon_knight_defeated"}), "text": INTERCEPTION}]
        locations[identifier]["connected_location_ids"] = ["royal_gate", "dragon_valley_return"]
    upsert(pack["epilogues"], dict(id="town_blood", endings=["ignis_defeated", "ignis_purified", "draco_defeated", "draco_defeated_with_ignis"],
                                 requirements={"flag": "town_blood"}, text=EPILOGUE))
    _attackable_mages(pack, locations, npcs)
    _absence_inventory(pack)
    # Earlier migrations append their own records; keep their established order stable.
    for section, identifier in (("enemies", "tutorial_slime"), ("items", "travel_potion")):
        pack[section] = [entry for entry in pack[section] if entry["id"] != identifier] + [entry for entry in pack[section] if entry["id"] == identifier]
    from .checks_e import CHECKS, CHOICE_KEYS

    check_ids = {entry[0] for entry in CHECKS}
    for location in pack["locations"]:
        actions = location.get("actions", [])
        location["actions"] = [entry for entry in actions if entry["id"] not in check_ids] + [entry for entry in actions if entry["id"] in check_ids]
    wall["choices"] = [{key: deepcopy(value) for key, value in entry.items() if key in (
        CHOICE_KEYS if entry["id"] in check_ids else {
            "text", "preview", "risk", "requirements", "visible_after", "hidden_after", "enabled", "disabled_reason"})}
        for entry in wall["actions"]]
    annotate_risks(pack)
    ruby_names(pack)
    pack["meta"]["npc_combat_v041"] = True
    pack["meta"]["npc_combat_v045"] = True
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), "2026-10-19-ruby-045-npc-combat")


def _attackable_mages(pack: dict[str, Any], locations: dict[str, Any], npcs: dict[str, Any]) -> None:
    character = next(record for record in pack["characters"] if record["id"] == "warlock")
    enemy = {key: deepcopy(character[key]) for key in (
        "name", "description", "hp", "max_hp", "mp", "max_mp", "sp", "max_sp",
        "attributes", "resistances", "combat", "skills", "image")}
    enemy.update(id="npc_warlock", npc_id="warlock")
    upsert(pack["enemies"], enemy)
    for identifier in ("warlock", "blue_robed_mage"):
        npcs[identifier]["npc_combat"] = dict(category="killable", town=True, guardians=[], aftermath="dead",
            shared_npc_ids=["warlock", "blue_robed_mage"], enemy_id="npc_warlock", companion_id="blue_robed_mage",
            fallen_text=FALLEN["warlock"], fallen_effects=[{"unset_flag": "warlock_rescue_available"}],
            encounter={"npc_town": True})
    npcs["xanxus"]["npc_combat"] = dict(category="killable", town=False, guardians=[], aftermath="dead",
        enemy_id="xanxus", gone_flag="defeated_xanxus", fallen_text=FALLEN["xanxus"],
        fallen_effects=[{"set_flag": flag} for flag in ("defeated_xanxus", "heard_xanxus_betrayal", "xanxus_encountered")] + [
            {"branch": {"requirements": {"has_item": "火種"}, "then": [
                {"remove_item": {"name": "火種", "quantity": 1, "force": True}}, {"set_flag": "fire_seed_removed"}]}}],
        encounter={"npc_town": False}, locations={
            location: {"encounter": {"npc_town": False, "victory_effects": [
                {"current_location": "valley_nest_gate" if location == "xanxus_at_nest" else "village_frozen_clue"}
            ] + ([{"set_flag": "nest_event_seen"}] if location == "xanxus_at_nest" else [])}}
            for location in ("xanxus_confrontation", "xanxus_ultimatum", "xanxus_at_nest")})
    # The original scripted loss still continues; a genuine victory shares the death consequences.
    locations["xanxus_battle"]["combat"].update(
        npc_participants=["xanxus"], npc_enemy_map={"xanxus": "xanxus"}, npc_town=False)

    alive = both({"not_flag": "npc_gone_warlock"}, {"not_flag": "npc_gone_blue_robed_mage"})
    for entry in locations["magic_shop"]["actions"]:
        if entry["id"] in {"ask_mina_missing", "report_mina_safe"}:
            entry["npc_ids_required"] = ["warlock"]
        if entry["id"] == "forge_prism_weapon":
            # The existing rescued-Mina variant explicitly lets her craft in her master's place.
            entry["visible_requirements"] = {"any": [alive, both({"flag": "mina_quest_done"}, {"not_flag": "npc_gone_mina"})]}
    refusal = next(a for a in locations["xanxus_ultimatum"]["actions"] if a["id"] == "refuse_xanxus_without_rescue")
    refusal.pop("hidden_after", None)
    refusal["visible_requirements"] = {"any": [{"not_flag": "warlock_rescue_available"},
        {"flag": "npc_gone_warlock"}, {"flag": "npc_gone_blue_robed_mage"}]}
    for location_id, before_id, after_id in (
            ("village_frozen_clue", "skip_frozen_clue_before_xanxus", "skip_frozen_clue_after_xanxus"),
            ("ian_ice_katana_aftermath", "refuse_ian_before_xanxus", "refuse_ian_after_xanxus")):
        for entry in locations[location_id]["actions"]:
            if entry["id"] == before_id:
                entry["visible_requirements"] = {"not_flag": "defeated_xanxus"}
            elif entry["id"] == after_id:
                entry.pop("visible_after", None)
                entry["visible_requirements"] = {"any": [{"flag": "xanxus_encountered"}, {"flag": "defeated_xanxus"}]}
    escape = next(a for a in locations["village_approach"]["actions"] if a["id"] == "escape_from_burning_village")
    escape["effects"] = [{"branch": {"requirements": {"flag": "defeated_xanxus"},
        "then": [{"current_location": "village_frozen_clue"}], "else": [{"current_location": "xanxus_confrontation"}]}}]
    nest = locations["valley_nest_gate"]["entry_effects"][0]["branch"]["then"][1]["branch"]
    nest["requirements"] = both({"flag": "accepted_fire_seed"}, {"not_flag": "fire_seed_removed"}, {"not_flag": "defeated_xanxus"})
    nest["else"][0]["branch"]["requirements"] = both({"flag": "warlock_rescue_available"}, alive)

    def guard_core_claim(value: Any) -> None:
        if isinstance(value, dict):
            requirement = value.get("requirements")
            if isinstance(requirement, dict):
                terms = requirement.get("all", [requirement])
                if any(term in terms for term in ({"flag": "promised_core_to_xanxus"}, {"flag": "xanxus_took_core"})):
                    if {"not_flag": "defeated_xanxus"} not in terms:
                        value["requirements"] = both(*terms, {"not_flag": "defeated_xanxus"})
            for child in value.values():
                guard_core_claim(child)
        elif isinstance(value, list):
            for child in value:
                guard_core_claim(child)
    for identifier in ("dragon_valley_loc", "ignis_last_breath", "ignis_purified"):
        guard_core_claim(locations[identifier])
    for entry in pack["epilogues"]:
        if entry["id"] in {"fire_seed_removed", "xanxus_core"}:
            entry["npc_ids_required"] = ["xanxus"]
        elif entry["id"] in {"warlock", "mina_done", "mina_alone"}:
            entry["npc_ids_required"] = ["warlock"] + (["mina"] if entry["id"].startswith("mina_") else [])
    endings = next(entry["endings"] for entry in pack["epilogues"] if entry["id"] == "xanxus_core")
    upsert(pack["epilogues"], dict(id="defeated_xanxus", endings=deepcopy(endings),
        requirements={"flag": "defeated_xanxus"}, text=XANXUS_EPILOGUE))


# Authored absence prose (design lead, 2026-10-19), plus marked 045b drafts.
# Key: the authored passage; value: (npc ids, replacement shown when any of them is gone).
FINAL_ABSENCE = {
    # TODO(design): these four Warlock passages are 045b drafts awaiting approval.
    "青いローブの銀髪の魔法使いが、杖を背に店番をしている。":
        (["warlock"], "薬草と古い紙の匂いが漂う魔法店。床には青いローブが広がり、光を失った杖が横たわっている。"),
    "薬草と古い紙の匂いが漂う店内で、青いローブの銀髪の魔法使いが顔を上げた。棚の小瓶が、窓からの光を受けて淡く瞬いている。「何かお探しかな」":
        (["warlock"], "薬草と古い紙の匂いが漂う店内。棚の小瓶は色を失い、床に広がった青いローブを窓からの光が照らしている。"),
    "青い光とともにワーロックが現れた。「先へ進む前に伝えておく。ザンザスは白竜と密約を交わしていた。紅竜の心臓と引き換えに、王国の半分をもらう約束だったそうだ。……気をつけろ」そう言い残し、彼は再び姿を消した。":
        (["warlock"], "竜の巣へ続く道に、冷たい風が吹き抜けている。岩の陰に積もった灰が、風に舞い上がった。"),
    "ワーロックがあなたを背後へ庇い、元素の水晶球を展開する。":
        (["warlock"], "燃える街道には、焼け焦げた地面と崩れた民家が続いている。灰を巻き上げる熱い風が、街道を吹き抜けていく。"),
    "村外れの石造りの集会所に、焼け出された村人たちが身を寄せ合っている。長老が人々を励まし、行商人の荷車の周りには小さな人だかりができている。":
        (["elder"], "村外れの石造りの集会所に、焼け出された村人たちが身を寄せ合っている。人々を励ます声は、もう聞こえない。"),
    "地図と剣が並ぶ質素な広間。白髪の老騎士――守護団長ヴァルターが、卓上の地図から顔を上げた。":
        (["walter"], "地図と剣が並ぶ質素な広間。団長の席は空いたままで、守護団員たちが黙って卓上の地図を見下ろしている。"),
    "崩れかけた民家の奥から、子どもの泣き声が聞こえる。入口は燃える梁で塞がれている。":
        (["riku"], "崩れかけた民家は静まり返っている。中に人の気配はない。"),
    "森狼の群れが、荷車を背にした行商人を追い詰めている。男はこちらに気づき、必死に手を振った。":
        (["gald"], "森狼の群れが、道端の壊れた荷車を漁っている。持ち主の姿はない。"),
    "「助かった！命の恩人だ。俺はガルド、村でも商売してる。見かけたら寄ってくれ」":
        (["gald"], "森狼の群れは散り散りに逃げていった。荷車の残骸だけが、道端に転がっている。"),
    "戦いが終わると迷子のゴブリンが現れ、自分の箱を見つけて抱き寄せようとする。":
        (["lost_goblin"], "戦いが終わった。主を失った箱が、金貨の山の陰に転がっている。"),
    "城下町の小さな鍛冶屋。鍛冶師ローベルトが武具の点検と修理をしてくれる。":
        (["blacksmith"], "城下町の小さな鍛冶屋。炉の火は消え、扉は閉ざされたままだ。"),
    "迷子のゴブリンが、別の一族に盗まれた箱を取り戻してほしいと頼んでいる。":
        (["lost_goblin"], "森の十字路。助けを求めていたゴブリンの姿は、もうない。"),
    "店主イアンが現れ、凍死するほどの力が残る破片に触れないよう制止した。":
        (["ian"], "凍死するほどの冷気を残す、砕けた氷の太刀の破片が散らばっている。"),
    "十歳ほどの金髪の少女サラと、小さな火コウモリ竜がいる。":
        (["sarah", "fire_bat_dragon"], "城下町の小さな道具屋。扉には鍵がかかり、店の中は暗い。"),
    "長老は焼け跡を見つめ、黙り込んでいる":
        (["elder"], "長老がいつも座っていた場所には、もう誰もいない。"),
    "ロビンが暗号を教えてくれた。":
        (["robin"], "鉄門の小窓の奥から、合言葉を求める声が響く。"),
    "湯気の立ち込める小さな温泉がある。岩の隙間に、ローブ姿の少女が膝を抱えて座り込んでいる。":
        (["mina"], "湯気の立ち込める小さな温泉がある。岩の隙間には、誰かが座り込んでいた跡だけが残っている。"),
    "炉の熱と槌の音が響く工房。分厚い前掛けの女鍛冶師が、白銀の剣に光の紋を刻んでいる。":
        (["brigitte"], "炉の火が落ちた工房。槌の音は止み、打ちかけの白銀の剣が金床の上で冷えている。"),
    "樫の梁がむき出しの酒場兼宿屋。非番の守護団員たちが峠の噂話をする隅で、青い外套の青年が水差しの水面をじっと見つめている。":
        (["elio"], "樫の梁がむき出しの酒場兼宿屋。非番の守護団員たちが、干し肉をかじりながら峠の噂話をしている。"),
    "高い窓から朝の光が差し込む礼拝堂。祭壇の前で、銀の鎧をまとった若い女騎士が祈りを捧げている。":
        (["liese"], "高い窓から朝の光が差し込む礼拝堂。祭壇の前には、死者を弔う白い花が供えられている。"),
    "街灯の届かない場所に、黒いローブの小柄で毛むくじゃらな商人が立っている。":
        (["suspicious_merchant"], "街灯の届かない路地裏。黒いローブの商人が立っていた場所には、誰もいない。"),
    "扉の鈴が鳴ると、棚の陰から金髪の少女サラが顔を出した。肩の上では小さな火コウモリ竜が、ぱちぱちと火の粉を散らしている。「いらっしゃいませ！今日は何をお探しですか？」":
        (["sarah", "fire_bat_dragon"], "扉の鈴が、誰もいない店の中に虚しく響いた。棚の品はそのまま、埃をかぶり始めている。"),
    "白髭を蓄えた長老は、あなたの決意を聞くと静かに頷いた。「イグニスは炎を操るが、その身は冷気に弱い。谷の冷気を宿した『氷の護符』があれば、奴の守りを崩せるはずじゃ。道具屋の店主が持っておるよ」":
        (["elder"], "避難所はひっそりとしていた。邪竜の弱点を語ってくれる者は、もういない。"),
}


# Passages that already read correctly after the person is gone.
KEEP_WHEN_ABSENT = {"怪しい商人の姿は消え、夜風だけが路地を抜けていく。", "箱を奪われまいと、迷子のゴブリンが短剣を抜く。"}


def _absence_inventory(pack: dict[str, Any]) -> None:
    """Inventory passages mentioning absent NPCs, using authored prose or marked drafts for visible ones."""
    names = {"ian": ["イアン"], "robin": ["ロビン"], "sarah": ["サラ"], "fire_bat_dragon": ["火コウモリ竜"],
             "blacksmith": ["ローベルト"], "suspicious_merchant": ["怪しい商人"], "gald": ["ガルド"],
             "elder": ["長老"], "riku": ["リク"], "shopkeeper": ["道具屋の店主"], "lost_goblin": ["迷子のゴブリン"],
             "walter": ["ヴァルター"], "liese": ["リーゼ"], "oaksdawn_priest": ["老司祭", "司祭"],
             "brigitte": ["ブリギッテ"], "elio": ["エリオ"], "mina": ["ミーナ"],
             "warlock": ["ワーロック", "青いローブの魔法使い", "青いローブの銀髪の魔法使い"]}
    entries: dict[str, dict[str, Any]] = {}

    def walk(value: Any, path: str, key: str = "") -> None:
        if isinstance(value, dict):
            for k, child in value.items():
                # Item lore, companion rules and chapter summaries stay true after someone is gone.
                if k not in {"npc_absence_texts", "npc_combat", "epilogues", "npcs", "enemies", "quests",
                             "items", "companions", "scenes"}:
                    walk(child, path + "/" + k, k)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                label = child.get("id", index) if isinstance(child, dict) else index
                walk(child, path + "/" + str(label), key)
        elif isinstance(value, str) and (key in {"description", "summary", "gm_text", "combat_text", "result_text", "entry_text", "success_text", "failure_text", "success", "failure", "victory"}
                                      or key == "text" and "/description_variants/" in path):
            identifiers = [identifier for identifier, aliases in names.items() if any(alias in value for alias in aliases)]
            parts = path.split("/")
            if len(parts) > 2 and parts[1:3] == ["locations", "burning_house"] and any(word in value for word in ("子ども", "男の子", "泣き声")):
                identifiers = list(dict.fromkeys([*identifiers, "riku"]))
            if value in KEEP_WHEN_ABSENT:
                return
            if value in FINAL_ABSENCE:
                ids, final = FINAL_ABSENCE[value]
                entries[value] = dict(text=value, npc_ids=ids, path=path, replacement=final,
                                      replacements={ids[0]: final}, status="draft" if ids == ["warlock"] else "final")
                return
            if value.strip() and identifiers and "もうここにはいない" not in value:
                entries[value] = dict(text=value, npc_ids=identifiers, path=path,
                    replacement=" ".join(f"{names[identifier][0]}はもうここにはいない。" for identifier in identifiers),
                    replacements={identifier: f"{names[identifier][0]}はもうここにはいない。" for identifier in identifiers}, status="TODO(design)")
    walk(pack, "")
    pack["npc_absence_texts"] = sorted(entries.values(), key=lambda entry: (-len(entry["text"]), entry["text"]))
    for entry in pack.get("epilogues", []):
        identifiers = [identifier for identifier, aliases in names.items() if any(alias in entry["text"] for alias in aliases)]
        if identifiers:
            entry["npc_ids_required"] = list(dict.fromkeys([*entry.get("npc_ids_required", []), *identifiers]))
    # Gald's rescue must never resurrect him or grant rescue rewards after his death.
    for location in pack["locations"]:
        if location["id"] != "forest_wolves":
            continue
        encounter = location.get("combat", {})
        if not encounter.get("npc_absence_effects"):
            original = encounter.get("victory_effects", {})
            if isinstance(original, dict) and "saved_gald" in original.get("flags_set", []):
                original["flags_set"].remove("saved_gald")
                encounter.setdefault("victory_bonus_effects", []).append({"branch": {"requirements": {"not_flag": "npc_gone_gald"}, "then": [{"set_flag": "saved_gald"}]}})
            encounter["npc_absence_effects"] = True
        for obstacle in location.get("obstacles", []):
            obstacle["pass_effects"] = [{"branch": {"requirements": {"not_flag": "npc_gone_gald"},
                "then": [{"set_flag": "saved_gald"}]}}]


def main() -> None:
    for name in PACKS:
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[npc_combat] updated {name}")


if __name__ == "__main__":
    main()
