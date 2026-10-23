"""Install reviewed 054 status attacks, optional hazards and normal-only items."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host.difficulty import apply_difficulty, overlay_fingerprint, validate_difficulty

ROOT = Path(__file__).resolve().parents[2]
REVISION = "2026-10-24-status-content-054"
NORMAL = ["normal"]

ITEM_TEXTS = {'antidote_herb': ('毒消し草', '苦みの強い薬草を煎じた丸薬。体内の毒をすべて浄化する。'),
 'burn_salve': ('火傷薬', '冷たい薬草を練り上げた軟膏。火傷を浄化する。'),
 'smelling_salts': ('気付け薬', '鋭い香りで意識を研ぎ澄ます薬。麻痺・弱体・目潰しを浄化する。'),
 'panacea': ('万能薬', '希少な薬草を調合した霊薬。気絶以外の弱体状態をすべて浄化する。'),
 'blinding_powder': ('目くらまし粉', '灰と薬草を混ぜた細かい粉。敵単体に投げつけて目潰しを付与する。'),
 'oil_flask': ('油壺', '燃えやすい油を詰めた小壺。敵単体に火属性ダメージを与え、火傷を付与する。'),
 'haze_ball': ('霞玉', '白い霞を噴き出す小玉。足元を包み込み、自身の回避率を一時的に高める。'),
 'purifying_bell': ('清めの鈴', '澄んだ音色で穢れを払う鈴。装備中、弱体状態を浄化する「清めの祈り」を使える。'),
 'trap_probe': ('探り棒', '先端に金具のついた細長い棒。所持していると、探索中の罠や落石を見抜きやすくなる。'),
 'poison_dart': ('毒矢', '毒を塗った投げ矢。敵単体にわずかなダメージを与え、毒を付与する。')}
TRAP_TEXTS = {1: ('通路脇の木箱を開ける',
     '無造作に置かれた木箱だが、留め金のあたりに不自然な細工が見える。',
     '箱の裏に張られた細い針金を指先で外し、仕掛けられた毒針をやり過ごして蓋を開けた。中から薬草と灰の詰まった小袋を手に入れた。',
     '蓋を持ち上げた瞬間、箱の隙間からバネ仕掛けの毒針が飛び出した。とっさに手を引いたが、針先が皮膚を浅くかすめて毒が回る。'),
 2: ('噴気孔のそばの結晶を拾う',
     '岩の裂け目で結晶が光っているが、奥から不規則に熱気が噴き出している。',
     '地底の唸りがふっと途切れた一瞬を見極め、素早く手を伸ばして結晶の脇を探った。誰かが落とした軟膏の壺を無事に拾い上げた。',
     '手を伸ばした途端、岩の裂け目から灼熱の蒸気が激しく噴き上がった。熱風をまともに浴び、皮膚がひりつくような痛みに襲われる。'),
 3: ('天井の大結晶を叩き落とす',
     '天井から大結晶が危うく垂れ下がっている。衝撃を与えれば周囲ごと崩れそうだ。',
     '結晶の根元を狙って一気に打ち抜き、落ちてくる破片の軌道を読み切って後ろへ跳び退いた。砕けた塊の中から輝く欠片と薬瓶を拾う。',
     '結晶は砕け落ちたが、振動で天井の岩盤まで一緒に崩れ落ちてきた。逃げ遅れた肩口に重い岩片が直撃し、激しい衝撃に息が詰まる。'),
 4: ('焼け落ちかけた納屋を探る',
     '納屋の梁が赤く爆ぜて軋んでいる。中へ踏み込めば今にも崩れ落ちてきそうだ。',
     '火勢の弱い風上側から身を低くして滑り込み、梁が落ちる前に棚の荷物を掴んで外へ飛び出した。小銭の袋と軟膏が手元に残った。',
     '納屋に踏み込んだ瞬間、燃え尽きた梁が轟音とともに崩れ落ちた。飛び散る火の粉と落ちてきた木材に打たれ、煙にむせながら這い出る。'),
 5: ('呪符の墓標に供えられた品を取る',
     '朽ちた剣の墓標に古い呪符が巻きつき、周囲の霧だけが重く淀んでいる。',
     '戦場に眠る死者へ静かに祈りを捧げてから手を伸ばすと、墓標に絡みついていた黒い怨気が霧散した。供えられていた薬瓶を謹んで受け取る。',
     '無造作に供え物へ触れた瞬間、呪符が黒く焼け焦げて冷たい怨念が腕に絡みついた。骨の髄まで重く沈み込み、全身から力が抜けていく。'),
 6: ('沼に沈んだ箱を引き上げる',
     '濁った泥水の底に古い箱が沈んでいる。足場がぬかるみ、不用意に引けば危険そうだ。',
     '硬い木の根に足を掛けて踏ん張り、箱に絡む水草を切ってから一気に引き上げた。泥を拭うと、密閉された小箱の中に霊薬が残っていた。',
     '泥に足を取られて体勢を崩し、箱の縁に仕込まれていた錆びた痺れ針に指先を突かれた。冷たい泥水の中で、腕から先が急速に痺れていく。'),
 7: ('崩れかけた岩棚の袋を取る',
     '頭上の岩棚に旅人の袋が引っかかっているが、地鳴りのたびに小石が落ちてくる。',
     '地鳴りが収まった静寂の隙を突き、岩肌を蹴って一気に袋を掴み取った。岩棚が崩れる前に安全な道へ着地し、中の道具を回収した。',
     '手をかけた途端に地鳴りが響き、岩棚ごと大小の落石が雪崩れ落ちてきた。身をかわしきれずに岩角に打ち据えられ、砂煙の中でうずくまる。'),
 8: ('放置された木箱を開ける',
     '天幕の隅に鎖の巻かれた木箱が残されている。盗掘除けの仕掛けがあるかもしれない。',
     '鉱夫が仕掛けた掛け金の癖を見抜き、底板のバネを押さえながら慎重に蓋を開けた。仕掛けを動かさずに、中の小壺と金貨を手に入れた。',
     '掛け金を外した瞬間、箱の底から火油の飛沫と火花が弾け飛んだ。顔面をかすめた炎に焼かれ、焦げ臭い煙の中で思わず後ずさる。'),
 9: ('書斎の金庫をこじ開ける',
     '机の下に重厚な鉄の金庫が据えられている。鍵穴の奥に精巧な防犯の仕掛けがありそうだ。',
     '鍵穴の奥でかすかに光る放電針の継ぎ目を探り当て、金具で絶縁してから錠前を落とした。音も立てずに扉が開き、霊薬と金貨を手に入れた。',
     '錠前を回した瞬間、鍵穴の奥から紫色の電光が弾けて指先を走った。激しい雷撃に全身の筋肉が硬直し、金庫の前で膝から崩れ落ちる。')}

# Existing 052b moves are reused; legacy basic statuses are also converted.
STATUS_ATTACKS = (
    ("hobgoblin", "skills.@id=skull_crush", "stun", 50, 1, 1),
    ("heat_lizard", "combat.basic_attack", "burn", 50, 1, 2),
    ("heat_lizard", "skills.@id=fire_spit", "burn", 50, 1, 2),
    ("sapphire_moth", "combat.basic_attack", "blind", 40, 1, 2),
    ("emerald_spider", "combat.basic_attack", "poison", 75, 1, 3),
    ("fire_slime", "combat.basic_attack", "burn", 25, 1, 2),
    ("fire_elemental", "skills.@id=flame_torrent", "burn", 40, 1, 2),
    ("ice_elemental", "skills.@id=freezing_breath", "paralysis", 30, 1, 2),
    ("ghoul", "skills.@id=rotting_claw", "paralysis", 25, 1, 2),
    ("wraith", "combat.basic_attack", "weaken", 40, 1, 2),
    ("rock_giant", "skills.@id=rock_crusher", "stun", 50, 1, 1),
    ("ash_wraith", "skills.@id=resentment", "weaken", 50, 1, 2),
    ("ash_wraith", "skills.@id=ash_embrace", "suffocation", 100, 1, 2),
    ("lava_drake", "skills.@id=lava_breath", "burn", 80, 1, 2),
    ("xanxus_phantom", "skills.@id=inferno_focus", "burn", 100, 1, 2),
    ("ignis", "skills.@id=fire_breath", "burn", 100, 1, 2),
    ("ice_sentinel", "skills.@id=ice_hammer", "stun", 50, 1, 1),
    ("ice_assassin", "skills.@id=frozen_poison", "poison", 100, 2, 3),
)
PERIODIC_ATTACKS = (
    ("slime_king", "corrosive_slime", "腐食の粘液", "poison", 2, 3, .6,
     "{enemy}は酸の匂いが立ちこめる粘液を吐きかけた。"),
    ("war_hound", "intimidating_howl", "威嚇の遠吠え", "weaken", 1, 2, None,
     "{enemy}は低く唸り、威嚇の遠吠えを響かせた。"),
    ("grave_knight", "binding_sword", "呪縛の剣", "weaken", 1, 2, .8,
     "{enemy}は黒い靄を纏わせた呪縛の剣を振るった。"),
    ("earth_worm", "gravel_spray", "砂礫の噴射", "blind", 1, 2, .5,
     "{enemy}は大口を開き、目潰しの砂礫を噴き上げた。"),
)
UNDEAD = ("skeleton_soldier", "ghoul", "wraith", "grave_knight", "ash_wraith", "zebok")
SHOP_ITEMS = {
    "sarah_shop": (("antidote_herb", 10, 4), ("burn_salve", 10, 3), ("smelling_salts", 15, 3),
                   ("blinding_powder", 20, 3), ("haze_ball", 25, 2)),
    "village_shop": (("antidote_herb", 10, 4), ("burn_salve", 10, 4)),
    "oaksdawn_chapel_shop": (("antidote_herb", 10, 3), ("smelling_salts", 15, 3),
                            ("panacea", 40, 1), ("purifying_bell", 45, 1)),
    "gald_shop": (("burn_salve", 8, 3), ("blinding_powder", 15, 3), ("haze_ball", 20, 2)),
    "magic_shop": (("panacea", 40, 2), ("purifying_bell", 50, 1)),
    "gald_capital_shop": (("panacea", 35, 1), ("oil_flask", 12, 3)),
    "forge_shop": (("oil_flask", 15, 3), ("trap_probe", 20, 1)),
    "oaksdawn_workshop_shop": (("oil_flask", 15, 3), ("trap_probe", 20, 1)),
}
# Number, location, kind, check, DC, HP loss, status, rewards, clue requirements.
TRAPS = (
    (1, "goblin_fort_second_choice", "trap", "軽業", 10, .10, "poison",
     (("antidote_herb", 1), ("blinding_powder", 1)), {"flag": "fort_corridors_heard_054"}),
    (2, "cave_heat_corridor", "trap", "知覚", 10, .10, "burn",
     (("burn_salve", 2),), {"flag": "heat_rhythm_known"}),
    (3, "cave_crystal_corridor", "rockfall", "運動", 12, .15, None,
     (("smelling_salts", 1), ("crystal_fragment", 2)), {"flag": "calmed_crystals"}),
    (4, "burning_house", "rockfall", "知覚", 10, .15, "burn",
     (("burn_salve", 1),), {"flag": "fire_upwind_known"}),
    (5, "bone_field", "trap", "信仰", 10, .10, "weaken",
     (("smelling_salts", 2),), {"has_item": "錆びた兵士の徽章"}),
    (6, "ghoul_marsh", "trap", "運動", 12, .10, "paralysis",
     (("panacea", 1),), {"flag": "marsh_path_known"}),
    (7, "gorge_rockfall_path", "rockfall", "軽業", 10, .15, None,
     (("antidote_herb", 1),), {"flag": "gorge_tremor_rhythm"}),
    (8, "gorge_miner_camp", "trap", "知覚", 12, .15, "burn",
     (("oil_flask", 1),), {"flag": "read_miner_diary"}),
    (9, "mansion_study", "trap", "軽業", 14, .10, "paralysis",
     (("panacea", 1),), {"flag": "mansion_patrol_known"}),
)


def _upsert(records: list[dict[str, Any]], record: dict[str, Any], key: str = "id") -> None:
    old = next((entry for entry in records if entry.get(key) == record[key]), None)
    if old is None:
        records.append(deepcopy(record))
    else:
        records.remove(old)
        normalized = {field: old[field] for field in ("title", "keywords") if field in old}
        old.clear()
        old.update(normalized)
        old.update(deepcopy(record))
        records.append(old)


def _append_effect(records: list[dict[str, Any]], effect: dict[str, Any]) -> None:
    if effect not in records:
        records.append(deepcopy(effect))


def _status(identifier: str, chance: int = 100, stacks: int = 1, duration: int = 2) -> dict[str, Any]:
    return {"id": identifier, "chance": chance, "stacks": stacks, "duration": duration}


def _items() -> list[dict[str, Any]]:
    prayer = {"id": "purify_prayer", "name": "清めの祈り", "kind": "cleanse", "cost": 3,
              "cost_type": "mp", "cooldown": 1, "cleanse": {"count": 1, "tags": ["debuff"]},
              "description": "澄んだ鈴の音とともに祈りを捧げ、自身の弱体状態を1つ浄化する。"}
    specs = {
        "antidote_herb": {"kind": "cleanse", "cleanse": {"count": "all", "tags": ["poison"]}, "cooldown": 0},
        "burn_salve": {"kind": "cleanse", "cleanse": {"tags": ["fire"]}, "cooldown": 0},
        "smelling_salts": {"kind": "cleanse", "cleanse": {"tags": ["paralysis", "weaken", "blind"]}, "cooldown": 0},
        "panacea": {"kind": "cleanse", "cleanse": {"count": "all", "tags": ["debuff"]}, "cooldown": 0},
        "blinding_powder": {"kind": "damage", "status_on_hit": True, "accuracy": 95,
                            "on_hit_status": {"id": "blind"}},
        "oil_flask": {"kind": "damage", "damage": "1d4", "element": "fire", "accuracy": 90,
                      "on_hit_status": {"id": "burn"}},
        "haze_ball": {"kind": "status", "self_status": {"id": "haze"}},
        "purifying_bell": {"kind": "equipment", "requires_equipped": True, "grants_skills": [prayer]},
    }
    records = []
    for identifier, (name, description) in ITEM_TEXTS.items():
        if identifier == "poison_dart":
            continue
        record = {"id": identifier, "name": name, "description": description, "difficulty_only": NORMAL.copy()}
        if identifier == "trap_probe":
            record["category"] = "key"
        elif identifier == "purifying_bell":
            record.update(category="equipment", slot="accessory", combat=deepcopy(specs[identifier]))
        else:
            record.update(category="consumable", combat={**deepcopy(specs[identifier]), "consumable": True})
        records.append(record)
    return records


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    if not any(entry.get("damage_max_hp_ratio") for enemy in apply_difficulty(result, "normal")["enemies"]
               for entry in enemy.get("skills", [])):
        raise ValueError("054 requires the complete 052b migration")
    definitions = {entry["id"]: entry for entry in result["status_defs"]}
    for identifier in ("poison", "paralysis", "weaken", "blind"):
        definitions[identifier]["tags"] = [identifier, "debuff"]
    _upsert(result["status_defs"], {
        "id": "haze", "name": "霞", "icon": "霞", "kind": "modifier", "stackable": False,
        "max_stacks": 1, "duration": 2, "tick": {}, "modifiers": {"evade_bonus": 15},
        "tags": ["buff"], "cleansable": False, "description": "白い霞に身を隠し、回避率が高まっている。",
        "apply_text": "{target}は白い霞に身を隠した。",
    })
    overlays = result["difficulty_overlays"]["normal"]
    overlays[:] = [entry for entry in overlays if not (
        entry.get("entity") == "enemies" and entry.get("id") == "xanxus_phantom"
        and entry.get("path") == "combat.basic_attack.on_hit_status")]

    def setting(entity: str, identifier: str, path: str, value: Any) -> None:
        if path.endswith(".on_hit_status") and any(
                old["entity"] == entity and old["id"] == identifier and old["path"].startswith(path + ".")
                for old in overlays):
            raise ValueError(f"054 status conflicts with numeric overlay: {entity}/{identifier}/{path}")
        record = {"entity": entity, "id": identifier, "path": path, "set": deepcopy(value)}
        old = next((entry for entry in overlays if (entry["entity"], entry["id"], entry["path"])
                    == (entity, identifier, path)), None)
        if old is None:
            overlays.append(record)
        elif old != record:
            raise ValueError(f"054 refuses to replace another status overlay: {entity}/{identifier}/{path}")

    for enemy_id, path, identifier, chance, stacks, duration in STATUS_ATTACKS:
        setting("enemies", enemy_id, path + ".on_hit_status", _status(identifier, chance, stacks, duration))
    for identifier in UNDEAD:
        enemy = next(entry for entry in result["enemies"] if entry["id"] == identifier)
        setting("enemies", identifier, "status_immunity", list(dict.fromkeys([*enemy.get("status_immunity", []), "poison"])))
    setting("items", "poison_dart", "combat.on_hit_status", {"id": "poison", "stacks": 2})
    poison_dart = next(item for item in result["items"] if item["id"] == "poison_dart")
    poison_dart["description"] = ITEM_TEXTS["poison_dart"][1]
    effective_enemies = {entry["id"]: entry for entry in apply_difficulty(result, "normal")["enemies"]}
    for enemy_id, identifier, name, status_id, stacks, duration, multiplier, text in PERIODIC_ATTACKS:
        enemy = next(entry for entry in result["enemies"] if entry["id"] == enemy_id)
        basic = effective_enemies[enemy_id]["combat"]["basic_attack"]
        skill = {"id": identifier, "name": name, "kind": "attack", "difficulty_only": NORMAL.copy(),
                 "requires_combat_rule": "elite_percentage_round_cap",
                 "every_n_rounds": 3, "accuracy": basic["accuracy"], "element": basic["element"],
                 "damage": basic["damage"] if multiplier is not None else "0",
                 "on_hit_status": _status(status_id, 100, stacks, duration), "log_text": text}
        if multiplier is None:
            skill["status_on_hit"] = True
        else:
            skill["damage_multiplier"] = multiplier
        _upsert(enemy["skills"], skill)
    new_items = _items()
    existing_items = {item["id"]: item for item in result["items"]}
    new_items = [{**{field: value for field, value in existing_items.get(item["id"], {}).items()
                    if field in ("title", "keywords")}, **item} for item in new_items]
    new_ids = {record["id"] for record in new_items}
    result["items"] = [record for record in result["items"] if record["id"] not in new_ids] + new_items
    for shop in result["shops"]:
        new_ids = {row[0] for row in SHOP_ITEMS.get(shop["id"], ())}
        shop["items"] = [row for row in shop["items"] if row["item_id"] not in new_ids]
        for identifier, price, stock in SHOP_ITEMS.get(shop["id"], ()):
            _upsert(shop["items"], {"item_id": identifier, "price": price, "stock": stock,
                                     "difficulty_only": NORMAL.copy()}, "item_id")
    for enemy_id, item_id in (("slime", "antidote_herb"), ("emerald_spider", "antidote_herb"),
                              ("heat_lizard", "burn_salve"), ("war_hound", "smelling_salts")):
        enemy = next(entry for entry in result["enemies"] if entry["id"] == enemy_id)
        reward = _reward(result, item_id, 1)
        reward["difficulty_only"] = NORMAL.copy()
        _upsert(enemy["rewards"]["items"], reward)
    # The legacy tutorial migration clones slime; its spring-only reward must not spread to F1.
    tutorial = next(enemy for enemy in result["enemies"] if enemy["id"] == "tutorial_slime")
    tutorial["rewards"]["items"] = [reward for reward in tutorial["rewards"]["items"]
                                      if not (reward.get("id") == "antidote_herb"
                                              and reward.get("difficulty_only") == NORMAL)]
    locations = {entry["id"]: entry for entry in result["locations"]}
    actions = {entry["id"]: entry for location in result["locations"] for entry in location.get("actions", [])}
    _append_effect(actions["listen_fort_corridors"]["success_effects"],
                   {"set_flag": "fort_corridors_heard_054", "difficulty_only": NORMAL.copy()})
    _append_effect(actions["commune_spring"]["success_effects"], {
        "branch": {"requirements": {"character_id": "cleric"}, "then": [
            {"add_item": _reward(result, "purifying_bell", 1)}], "else": []},
        "difficulty_only": NORMAL.copy(),
    })
    _upsert(locations["elf_spring"]["actions"], {
        "id": "gather_antidote_herb_054", "text": "泉のほとりで薬草を摘む", "preview": "",
        "result_text": "泉のほとりで薬草を摘む。",
        "risk": "判定不要", "risk_source": "action", "intent_keywords": ["泉のほとりで薬草を摘む"],
        "once": "gathered_antidote_herb_054", "hidden_after": "gathered_antidote_herb_054",
        "difficulty_only": NORMAL.copy(), "effects": [{"add_item": _reward(result, "antidote_herb", 1)}],
    })
    for identifier in ("recruit_liese_letter", "recruit_liese_water", "recruit_liese_persuade"):
        action = actions[identifier]
        key = "success_effects" if "roll" in action else "effects"
        _append_effect(action[key], {"add_item": _reward(result, "smelling_salts", 1), "difficulty_only": NORMAL.copy()})
    for row in TRAPS:
        _upsert(locations[row[1]]["actions"], _trap(result, row))
    holy = deepcopy(next(action for action in locations["bone_field"]["actions"] if action["id"] == "hazard_054_05"))
    holy.update(id="hazard_054_05_holy_water", text="聖水を振りかけて呪いを解く",
                preview="聖水 ×1（判定なしで墓標の呪いを浄化し、供え物を回収する）",
                risk="判定不要", intent_keywords=["聖水を振りかけて呪いを解く"],
                requirements={"has_item": "聖水"},
                result_text="墓標に聖水を振りかけると、呪符に宿っていた黒い怨気が白い湯気を立てて消え去った。清められた墓標の前から、供えられていた薬瓶を回収した。")
    holy["effects"] = [{"remove_item": {"name": "聖水", "quantity": 1}}, *holy.pop("success_effects")]
    for key in ("roll", "failure_effects", "result_texts"):
        holy.pop(key)
    _upsert(locations["bone_field"]["actions"], holy)
    overlays.sort(key=lambda entry: (entry["entity"], entry["id"], entry["path"]))
    result["meta"]["content_revision"] = max(result["meta"]["content_revision"], REVISION)
    validate_difficulty(result)
    return result


def _reward(pack: dict[str, Any], identifier: str, quantity: int) -> dict[str, Any]:
    item = next(entry for entry in pack["items"] if entry["id"] == identifier)
    return {"id": identifier, "name": item["name"], "quantity": quantity}


def _trap(pack: dict[str, Any], row: tuple[Any, ...]) -> dict[str, Any]:
    number, location, kind, skill, dc, ratio, status_id, rewards, clue = row
    text, preview, success, failure = TRAP_TEXTS[number]
    effects = [{"add_item": _reward(pack, identifier, quantity)} for identifier, quantity in rewards]
    success_only_effects: list[dict[str, Any]] = []
    if number in (7, 8):
        success_only_effects = effects
        effects = []
    if number in (4, 9):
        effects.append({"gold_change": 15 if number == 4 else 30})
    if number == 8:
        success_only_effects.append({"gold_change": 15})
    if number == 7:
        effects.append({"set_flag": "passed_gorge_rockfall_path"})
    failure_effects = [{"damage_player": {"max_hp_ratio": ratio}}]
    if status_id:
        failure_effects.append({"apply_status": _status(status_id, 100, 1, 3 if status_id == "poison" else 2)})
    attribute = {"軽業": "dex", "知覚": "wis", "運動": "str", "信仰": "wis"}[skill]
    label = {"dex": "敏捷", "wis": "知恵", "str": "筋力"}[attribute]
    clue_reason = {
        1: "通路の奥に耳を澄ます", 2: "熱風の切れ目を知っている", 3: "水晶の共鳴を知っている",
        4: "風上を知っている", 5: "錆びた兵士の徽章", 6: "沈まない足場を知っている",
        7: "地鳴りの間隔を知っている", 8: "鉱夫の荷物を調べる", 9: "夜番の交代を知っている",
    }[number]
    action = {
        "id": f"hazard_054_{number:02d}", "text": text, "preview": preview,
        "risk": f"{skill}（{label}）判定・DC{dc}", "risk_source": "action", "intent_keywords": [text],
        "difficulty_only": NORMAL.copy(), "once": f"hazard_054_{number:02d}_done",
        "hidden_after": f"hazard_054_{number:02d}_done", "hazard": {"kind": kind, "warning": preview},
        "roll": {"dice_type": f"1d20+{attribute}", "skill": skill, "dc": dc, "advantage": [
            {"requirements": {"character_id": "thief"}, "reason": "盗賊の勘"},
            {"requirements": {"has_item": "探り棒"}, "reason": "探り棒で確かめた"},
            {"requirements": clue, "reason": clue_reason},
        ]},
        "critical_enabled": False, "effects": [], "success_effects": [*deepcopy(effects), *deepcopy(success_only_effects)],
        "failure_effects": [*failure_effects, *deepcopy(effects)],
        "result_texts": {"success": success, "failure": failure},
    }
    if number == 3:
        action["visible_after"] = "cleared_cave_crystal_corridor"
    if number == 7:
        action["visible_requirements"] = {"not_flag": "passed_gorge_rockfall_path"}
    return action


def main() -> None:
    manifest = {}
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        original = json.loads(path.read_text(encoding="utf-8"))
        updated = migrate(original)
        if updated != original:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
        manifest[name] = {"content_revision": updated["meta"]["content_revision"],
                          "overlay_sha256": overlay_fingerprint(updated)}
        print(f"{name}: {updated['meta']['content_revision']}")
    path = ROOT / "host/prompt/processed/difficulty/overlay_revision.json"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
