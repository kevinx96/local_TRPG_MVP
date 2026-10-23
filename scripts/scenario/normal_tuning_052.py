"""052 normal numeric tuning; base baby data remains untouched."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import quote

from host.difficulty import overlay_fingerprint, validate_difficulty

ROOT = Path(__file__).resolve().parents[2]
REVISION = "2026-10-23-tuning-052b"

# L1: bounded EXP search and approved integer / per-level growth.
PROGRESSION: dict[str, Any] = {'level_gains': {'hero': {'max_hp': 3,
                          'max_mp': 1,
                          'max_sp': 1,
                          'attributes': {'str': 2, 'end': 1},
                          'by_level': {'2': {'max_sp': 2},
                                       '4': {'max_sp': 2,
                                             'attributes': {'dex': 1}},
                                       '6': {'max_sp': 2,
                                             'attributes': {'dex': 1}},
                                       '8': {'attributes': {'dex': 1}}}},
                 'cleric': {'max_hp': 3,
                            'max_mp': 2,
                            'max_sp': 1,
                            'attributes': {'wis': 2, 'int': 1}},
                 'mage': {'max_hp': 2,
                          'max_mp': 3,
                          'max_sp': 1,
                          'attributes': {'int': 2, 'wis': 1},
                          'by_level': {'2': {'max_hp': 3},
                                       '4': {'max_hp': 3,
                                             'attributes': {'dex': 1}},
                                       '8': {'attributes': {'dex': 1}}}},
                 'thief': {'max_hp': 2,
                           'max_mp': 1,
                           'max_sp': 2,
                           'attributes': {'dex': 2, 'str': 1}}},
 'exp_table': {'2': 20,
               '3': 50,
               '4': 54,
               '5': 99,
               '6': 171,
               '7': 319,
               '8': 679},
 'exp_rewards': {'trash': 4,
                 'elite': 12,
                 'boss': 25,
                 'quest': 30,
                 'unclassified': 4,
                 'scripted_loss': 0,
                 'guest': 0}}


# L2: numeric-only candidate; unresolved gates are recorded in the 052 report.
ENEMIES: dict[str, dict[str, Any]] = {'ash_wraith': {'skills.@id=ash_embrace.damage': '1',
                'skills.@id=resentment.damage': '1d2+9'},
 'draco_human': {'skills.@id=ice_blade.damage': '1d2+24',
                 'skills.@id=sword_flash.damage': '1d2+8',
                 'hp': 15,
                 'max_hp': 15},
 'emerald_spider': {'combat.basic_attack.damage': '1'},
 'fire_elemental': {'combat.basic_attack.damage': '1d2+12'},
 'fire_slime': {'combat.basic_attack.damage': '1d2+2'},
 'forest_wolf': {'combat.basic_attack.damage': '2d4+2'},
 'frost_dire_wolf': {'combat.basic_attack.damage': '2d4+8',
                     'hp': 56,
                     'max_hp': 56},
 'goblin': {'combat.basic_attack.damage': '1d2+2'},
 'goblin_archer': {'combat.basic_attack.damage': '1'},
 'goblin_king': {'combat.basic_attack.damage': '1d2+4', 'hp': 51, 'max_hp': 51},
 'heat_lizard': {'combat.basic_attack.damage': '1d2+2'},
 'hobgoblin': {'combat.basic_attack.damage': '1d2+3'},
 'ice_elemental': {'combat.basic_attack.damage': '1d2+8'},
 'ignis': {'skills.@id=fire_breath.damage': '2d4+17', 'hp': 149, 'max_hp': 149},
 'prism_tree': {'skills.@id=crystal_rain.damage': '2d4+6',
                'hp': 78,
                'max_hp': 78,
                'combat.defense': 0},
 'ruby_golem': {'skills.@id=ruby_fist.damage': '1d2+5'},
 'sapphire_moth': {'combat.basic_attack.damage': '1'},
 'slime': {'combat.basic_attack.damage': '4'},
 'slime_king': {'combat.basic_attack.damage': '2d4+5', 'hp': 93, 'max_hp': 93},
 'draco_dragon': {'hp': 132, 'max_hp': 132}}



# L3: reviewed content; skull_crush / rock_crusher / ice_hammer status hooks belong to 054.
MOVES_052B = [{'enemy': 'forest_wolf',
  'id': 'throat_bite',
  'reuse': False,
  'name': '喉笛喰らい',
  'ratio': 0.20,
  'release_text': '【仮】{enemy}は低く身を沈め、鋭い牙で急所へ飛びかかった！',
  'basic_weight': 2},
 {'enemy': 'hobgoblin',
  'id': 'skull_crush',
  'reuse': False,
  'name': '脳天砕き',
  'ratio': 0.2,
  'release_text': '【仮】{enemy}は大棍棒を大きく振りかぶり、渾身の力で叩きつけた。',
  'basic_weight': 2},
 {'enemy': 'war_hound',
  'id': 'raging_bite',
  'reuse': False,
  'name': '猛り噛み砕き',
  'ratio': 0.18,
  'release_text': '【仮】{enemy}は荒々しく唸り、顎を大きく開いて飛びかかった！',
  'basic_weight': 2},
 {'enemy': 'fire_elemental',
  'id': 'flame_torrent',
  'reuse': False,
  'name': '爆炎の奔流',
  'ratio': 0.2,
  'release_text': '【仮】{enemy}の核が激しく脈打ち、灼熱の炎が渦を巻いて噴き出した！',
  'basic_weight': 2},
 {'enemy': 'ice_elemental',
  'id': 'freezing_breath',
  'reuse': False,
  'name': '凍てつく息',
  'ratio': 0.2,
  'release_text': '【仮】{enemy}が冷たい息を吐き出し、周囲の空気を凍らせた。',
  'basic_weight': 2},
 {'enemy': 'heat_lizard',
  'id': 'fire_spit',
  'reuse': False,
  'name': '火炎吐き',
  'ratio': 0.18,
  'release_text': '【仮】{enemy}が喉を膨らませ、火の玉を吐き出した。',
  'basic_weight': 2},
 {'enemy': 'ruby_golem',
  'id': 'ruby_fist',
  'reuse': True,
  'name': '紅晶砕き',
  'ratio': 0.22,
  'release_text': '【仮】{enemy}が結晶の拳を振り上げ、床ごと叩き潰した。',
  'basic_weight': 1},
 {'enemy': 'ash_wraith',
  'id': 'soot_wave',
  'reuse': False,
  'name': '黒煤の窒息波',
  'ratio': 0.15,
  'ai_weight': 3,
  'skill_weights': {'ash_embrace': 4, 'resentment': 2},
  'release_text': '【仮】{enemy}が煤の腕を広げ、視界ごと包み込むように迫った。',
  'basic_weight': 0},
 {'enemy': 'lava_drake',
  'id': 'lava_breath',
  'reuse': True,
  'name': '溶岩の牙',
  'ratio': 0.2,
  'release_text': '【仮】{enemy}の牙から赤黒い溶岩が滴り、噛み砕くように迫った。',
  'basic_weight': 1},
 {'enemy': 'ice_sentinel',
  'id': 'ice_hammer',
  'reuse': True,
  'name': '凍てつく大槌',
  'ratio': 0.2,
  'release_text': '【仮】{enemy}は凍りついた大槌を高く掲げ、床ごと叩き潰した！',
  'basic_weight': 1},
 {'enemy': 'ice_assassin',
  'id': 'ice_blade_combo',
  'reuse': True,
  'name': '氷刃の連撃',
  'ratio': 0.2,
  'release_text': '【仮】{enemy}は白い息とともに踏み込み、凍る刃を続けざまに振るった！',
  'basic_weight': 1},
 {'enemy': 'ghoul',
  'id': 'rotting_claw',
  'reuse': False,
  'name': '腐肉の爪',
  'ratio': 0.2,
  'release_text': '【仮】{enemy}が黒ずんだ爪を振り回し、腐臭とともに飛びかかった。',
  'basic_weight': 2},
 {'enemy': 'rock_giant',
  'id': 'rock_crusher',
  'reuse': False,
  'name': '岩砕きの剛腕',
  'ratio': 0.25,
  'release_text': '【仮】{enemy}は岩の剛腕を振り上げ、大地ごと叩き潰した。',
  'basic_weight': 2},
 {'enemy': 'zebok',
  'id': 'nether_curse',
  'reuse': False,
  'name': '冥府の呪言',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}が呪言を放ち、凝縮された死の奔流が襲いかかった！',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}が骨の杖を高く掲げると、黒い瘴気が渦を巻いて収束していく……！'},
 {'enemy': 'slime_king',
  'id': 'royal_crush',
  'reuse': False,
  'name': '大王の巨体潰し',
  'ratio': 0.3,
  'release_text': '【仮】{enemy}が全体重を乗せて落下し、地面ごと押し潰した！',
  'every_n_rounds': 0,
  'warning': '【仮】{enemy}の巨体が大きく膨れ上がり、天井すれすれまで跳び上がった……！'},
 {'enemy': 'goblin_king',
  'id': 'royal_cleave',
  'reuse': False,
  'name': '王の大断ち',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}が大剣を両手で振りかぶり、床ごと叩き割った。',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}が錆びた大剣を両手で高く振りかぶり、全身に力を込めた……！'},
 {'enemy': 'grave_knight',
  'id': 'grave_cleave',
  'reuse': False,
  'name': '墓守の大断ち',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}が両手で大剣を振り上げ、石床ごと断ち割った。',
  'every_n_rounds': 0,
  'warning': '【仮】{enemy}の兜に蒼い冥火が灯り、大剣を上段に大きく構え直した……！'},
 {'enemy': 'earth_worm',
  'id': 'earth_collapse',
  'reuse': False,
  'name': '地砕きの崩落',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}が巨体をくねらせ、峡谷の底ごと叩き潰した。',
  'every_n_rounds': 0,
  'warning': '【仮】{enemy}が巨体を大きく反らし、峡谷の岩盤が激しく軋み始めた……！'},
 {'enemy': 'prism_tree',
  'id': 'aurora_torrent',
  'reuse': False,
  'name': '極光の奔流',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}の枝先から、七色の極光が奔流となって放たれた！',
  'every_n_rounds': 4,
  'warning': '【仮】{enemy}の幹の結晶が一斉に脈打ち、まばゆい七色の光が集まっていく……！'},
 {'enemy': 'frost_dire_wolf',
  'id': 'blizzard_howl',
  'reuse': False,
  'name': '吹雪の遠吠え',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}が天を仰いで吠えると、凍てつく吹雪が吹き荒れた。',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}が深く息を吸い込むと、周囲の空気が白く凍りつき始めた……！'},
 {'enemy': 'xanxus_phantom',
  'id': 'inferno_focus',
  'reuse': False,
  'name': '劫火の収束',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}が凝縮した劫火の球を解き放ち、爆炎が襲いかかった！',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}の炎の輪郭が激しく燃え上がり、掌に巨大な火球が渦巻く……！'},
 {'enemy': 'ignis',
  'id': 'fire_breath',
  'reuse': True,
  'name': '炎の息',
  'ratio': 0.4,
  'release_text': '【仮】{enemy}は深く息を吸い込み、灼熱の炎を吐き出した！',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}が大きく顎を開き、喉の奥に灼熱の炎が渦巻いている……！'},
 {'enemy': 'dragon_knight_mounted',
  'id': 'dive',
  'reuse': True,
  'name': '急降下突撃',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}は空高く舞い上がり、槍先を揃えて急降下した！',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}は翼を大きく広げて空高く舞い上がり、槍先をこちらへ向けた……！'},
 {'enemy': 'dragon_knight_human',
  'id': 'guardian_sentence',
  'reuse': False,
  'name': '守護者の処断',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}が大地を蹴って踏み込み、渾身の力で槍を突き出した！',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}は槍を深く引き絞り、鋭い眼差しでただ一点を見据えた……！'},
 {'enemy': 'draco_human',
  'id': 'silver_secret_blade',
  'reuse': False,
  'name': '白銀の秘太刀',
  'ratio': 0.35,
  'release_text': '【仮】{enemy}の剣が白く閃き、凍てつく斬撃が走った！',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}が白銀の剣を鞘に納め、足元から凍てつく冷気が立ちのぼる……！'},
 {'enemy': 'draco_dragon',
  'id': 'frozen_breath',
  'reuse': True,
  'name': '凍てつく吐息',
  'ratio': 0.45,
  'release_text': '【仮】{enemy}は白い冷気を吸い込み、すべてを凍らせる吐息を放った！',
  'every_n_rounds': 3,
  'warning': '【仮】{enemy}が深く息を吸い込み、喉の奥で白銀の冷気が渦巻いている……！'}]

BOSSES_052B: dict[str, dict[str, Any]] = {
    "ignis": {"hp": 140, "max_hp": 140, "resistances.physical": .25,
              "combat.basic_attack.damage": "2d4+8", "skills.@id=tail_sweep.damage": "2d4+8"},
    "prism_tree": {"hp": 90, "max_hp": 90, "combat.basic_attack.damage": "2d4+7",
                   "skills.@id=prism_branch.damage": "2d4+7", "skills.@id=crystal_rain.damage": "2d4+7"},
    "draco_human": {"combat.basic_attack.damage": "2d4+10", "skills.@id=sword_flash.damage": "2d4+10",
                    "skills.@id=ice_blade.damage": "2d4+10"},
    "draco_dragon": {"hp": 140, "max_hp": 140, "combat.basic_attack.damage": "2d4+10",
                     "skills.@id=white_wings.damage": "2d4+10"},
}


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    entries = [{"entity": "progression", "id": "$", "path": key, "set": deepcopy(value)}
               for key, value in PROGRESSION.items()]
    entries.extend({"entity": "enemies", "id": identifier, "path": path, "set": value}
                   for identifier, paths in ENEMIES.items() for path, value in paths.items())
    entries.extend(_moves_052b(result))
    entries.extend(_prism_resistances(result))
    for identifier, fields in BOSSES_052B.items():
        for key, value in fields.items():
            entry = next((e for e in entries if e["entity"] == "enemies" and e["id"] == identifier and e["path"] == key), None)
            if entry is None:
                entries.append({"entity": "enemies", "id": identifier, "path": key, "set": value})
            else:
                entry["set"] = value
    _ignis_second_phase(result)
    entries.append({"entity": "items", "id": "hero_holy_sword", "path": "combat.damage", "set": "1d8+34"})
    destinations = {(e["entity"], e["id"], e["path"]): e for e in entries}
    updated = []
    for entry in result["difficulty_overlays"]["normal"]:
        key = entry["entity"], entry["id"], entry["path"]
        updated.append(destinations.pop(key, entry))
    result["difficulty_overlays"]["normal"] = updated + list(destinations.values())
    result["difficulty_overlays"]["normal"].sort(key=lambda e: (e["entity"], e["id"], e["path"]))
    result["meta"]["content_revision"] = max(result["meta"]["content_revision"], REVISION)
    validate_difficulty(result)
    return result


def _prism_resistances(pack: dict[str, Any]) -> list[dict[str, Any]]:
    tree = next(e for e in pack["enemies"] if e["id"] == "prism_tree")
    phases = tree["resistance_cycle"]["phases"]
    elements = {element for enemy in pack["enemies"] for element in enemy.get("resistances", {})}
    entries = []
    for prefix, resistances in [("resistances", phases[0]["resistances"]),
                                *[(f"resistance_cycle.phases.@name={quote(p['name'], safe='')}.resistances", p["resistances"]) for p in phases]]:
        for element in sorted(elements):
            ratio = resistances.get(element, 1)
            entries.append({"entity": "enemies", "id": "prism_tree", "path": prefix+"."+element,
                            "set": ratio if ratio > 1 else 0})
    return entries


def _ignis_second_phase(pack: dict[str, Any]) -> None:
    skills = next(e for e in pack["enemies"] if e["id"] == "ignis")["skills"]
    skill = {"id": "raging_inferno", "name": "狂乱の劫火", "kind": "attack", "difficulty_only": ["normal"],
             "requires_combat_rule": "elite_percentage_round_cap",
             "damage": "2d4+10", "accuracy": 100, "element": "fire", "ai_weight": 1,
             "use_below_hp_ratio": .4,
             "release_text": "【仮】{enemy}は凍てつく古傷の痛みに狂乱し、周囲一帯を紅蓮の炎で薙ぎ払った！"}
    old = next((s for s in skills if s["id"] == skill["id"]), None)
    if old is None:
        skills.append(skill)
    else:
        old.clear()
        old.update(skill)


def _moves_052b(pack: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [{"entity": "combat_rules", "id": "$", "path": "elite_percentage_round_cap", "set": .30}]
    catalog = {e["id"]: e for e in pack["enemies"]}
    for move in MOVES_052B:
        enemy = catalog[move["enemy"]]
        skills = enemy.setdefault("skills", [])
        skill = next((s for s in skills if s["id"] == move["id"]), None)
        fields = {"damage_max_hp_ratio": move["ratio"], "release_text": move["release_text"]}
        if "warning" in move:
            fields["telegraph"] = {"charge_rounds": 1, "warning": move["warning"]}
            fields["every_n_rounds"] = move["every_n_rounds"]
            if not move["every_n_rounds"]:
                fields["use_below_hp_ratio"] = .99
        else:
            fields["ai_weight"] = move.get("ai_weight", 1)
            if skill and skill.get("hits", 1) > 1:
                fields["hits"] = 1
        if move["reuse"]:
            if skill is None:
                raise ValueError(f"Missing reviewed skill: {move['enemy']}/{move['id']}")
            entries.extend({"entity": "enemies", "id": enemy["id"],
                            "path": f"skills.@id={move['id']}.{key}", "set": value}
                           for key, value in fields.items())
        else:
            record = {"id": move["id"], "name": move["name"], "kind": "attack",
                      "requires_combat_rule": "elite_percentage_round_cap",
                      "difficulty_only": ["normal"], "accuracy": 100,
                      "element": enemy.get("combat", {}).get("basic_attack", {}).get("element", "physical"),
                      "ai_weight": 1, **fields}
            if move["enemy"] == "prism_tree":
                record["element"] = "current"
            if skill is None:
                skills.append(record)
            else:
                skill.clear()
                skill.update(record)
        weight = move.get("basic_weight", 2 if move.get("every_n_rounds") == 0 else 0)
        if "warning" not in move and move["reuse"]:
            weight = 0
            entries.append({"entity": "enemies", "id": enemy["id"], "path": "combat.basic_attack_weight", "set": 0})
            for other in skills:
                if other["id"] != move["id"]:
                    entries.append({"entity": "enemies", "id": enemy["id"],
                                    "path": f"skills.@id={other['id']}.ai_weight", "set": 2})
        if weight:
            entries.append({"entity": "enemies", "id": enemy["id"], "path": "combat.basic_attack_weight", "set": weight})
        for identifier, skill_weight in move.get("skill_weights", {}).items():
            entries.append({"entity": "enemies", "id": enemy["id"], "path": f"skills.@id={identifier}.ai_weight", "set": skill_weight})
    entries.extend([
        {"entity": "locations", "id": "goblin_fort_first_second", "path": "combat.encounter_class", "set": "trash"},
        {"entity": "locations", "id": "goblin_fort_first_second", "path": "combat.encounter_modifiers",
         "set": [{"id": "trash_guards_052b", "enemy_damage_multiplier": .7}]},
    ])
    return entries


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
    path = ROOT / "host/prompt/processed/difficulty/overlay_revision.json"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
