"""Install 051 definitions and opt-in normal mechanics without changing baby."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host.difficulty import _selector, overlay_fingerprint, validate_difficulty

ROOT = Path(__file__).resolve().parents[2]
REVISION = "2026-10-20-mechanics-051"


def status_definitions() -> list[dict[str, Any]]:
    # TODO(design): Finalize descriptions, hazard placements and the shop item list.
    def status(identifier: str, name: str, kind: str, duration: Any, description: str,
               *, modifiers: Any = None, tick: Any = None, cleansable: bool = True,
               tags: Any = None, **extra: Any) -> dict[str, Any]:
        return {"id": identifier, "name": name, "icon": name[:1], "kind": kind,
                "stackable": False, "max_stacks": 1, "duration": duration,
                "tick": tick or {}, "modifiers": modifiers or {}, "cleansable": cleansable,
                "tags": tags or ["debuff"], "description": "【仮】" + description, **extra}

    return [
        status("burn", "火傷", "dot", 2, "火傷による持続ダメージを受ける。",
               tick={"damage": "2", "element": "fire", "ignore_defense": True}, tags=["fire", "debuff"]),
        status("poison", "毒", "dot", 3, "層ごとに持続ダメージ。重ねると残り時間を更新する。",
               tick={"damage": "1", "element": "physical", "ignore_defense": True}, stackable=True, max_stacks=3,
               by_source={"player": {"tick": {"damage": "2"}}, "enemy": {"tick": {"damage": "1"}}}),
        status("weaken", "弱体", "modifier", 2, "与えるダメージが0.75倍になる。",
               modifiers={"damage_dealt_multiplier": .75}),
        status("paralysis", "麻痺", "modifier", 2, "25%の確率で行動できない。リソースは消費しない。",
               modifiers={"skip_chance": .25}),
        status("stun", "気絶", "skip_turn", 1, "次の行動を失い、その後2ラウンドは気絶を防ぐ。",
               cleansable=False, immunity_after=2),
        status("holy_mark", "聖印", "dot", 3, "聖属性の持続ダメージと、攻撃命中時の聖属性追撃。",
               tick={"damage": "1d3+wis/8", "element": "holy", "ignore_defense": True},
               modifiers={"on_damage_followup": {"damage": "1d3", "element": "holy", "accuracy": 100}}),
        status("blind", "目潰し", "modifier", 2, "命中率が下がる。ボスと冒険者への効果は20%。",
               modifiers={"accuracy_penalty": 30}, boss_modifiers={"accuracy_penalty": 20},
               by_source={"enemy": {"modifiers": {"accuracy_penalty": 20}}}),
        status("haste", "神速", "modifier", 3, "毎ラウンドの行動回数が1増える。持続中は重ねられない。",
               modifiers={"extra_actions_per_round": 1}, cleansable=False, tags=["buff"], no_reapply=True),
        status("holy_afterglow", "聖なる余光", "modifier", 1, "次の敵フェーズ終了まで攻撃ダメージを吸収する。上限は最大HPの25%。",
               modifiers={"shield": {"amount": 0, "max_hp_ratio": .25}}, cleansable=False,
               tags=["buff"], expires="enemy_phase_end"),
        status("arcane_shield", "魔導の盾", "modifier", None, "一度だけ攻撃ダメージを防ぐ。",
               modifiers={"shield": {"block_one_attack": True}}, cleansable=False, tags=["buff"]),
        status("gospel", "福音", "modifier", 3, "最大HPが2倍になり、増加分を回復する。攻撃を受けると元の最大HPの8%を回復する。毎ラウンド2回まで。",
               modifiers={"max_hp_multiplier": 2, "heal_after_attack_ratio": .08, "heal_limit_per_round": 2},
               cleansable=False, tags=["buff"]),
        status("holy_blessing", "聖光の加護", "modifier", 1, "この敵フェーズの被ダメージが0.75倍になる。",
               modifiers={"received_damage_multiplier": .75}, cleansable=False, tags=["buff"], expires="enemy_phase_end"),
        status("magic_focus", "魔力集中", "modifier", None, "次の攻撃魔法のダメージが1.3倍になる。",
               modifiers={"next_spell_damage_multiplier": 1.3}, cleansable=False, tags=["buff"]),
        status("suffocation", "窒息", "dot", 2, "ラウンド終了時に1ダメージ。浄化で解除できる。",
               tick={"damage": "1", "element": "physical", "ignore_defense": True}),
    ]


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    if "difficulty_overlays" not in result:
        raise ValueError("051 requires the 047 difficulty migration")
    definitions = result.setdefault("status_defs", [])
    for definition in status_definitions():
        if not any(entry["id"] == definition["id"] for entry in definitions):
            definitions.append(definition)
    # TODO(design): Reconcile the shared-dex note with the brief's normal-only rules and baby freeze.
    entries = [
        {"entity": "combat_rules", "id": "$", "path": "evade_model", "set": "dex"},
        {"entity": "combat_rules", "id": "$", "path": "evade_formula", "set": {"base": 4, "per_dex": 1.5, "cap": 20}},
        {"entity": "combat_rules", "id": "$", "path": "enemy_accuracy_override", "set": 100},
        {"entity": "characters", "id": "hero", "path": "skills.@id=divine_guard.cooldown", "set": 1},
        {"entity": "items", "id": "ice_charm", "path": "combat.requires_target_weakness", "set": "ice"},
    ]
    companion = next(entry for entry in result["companions"] if entry["id"] == "fire_bat_dragon")
    for effect in companion["round_start_effects"]:
        if effect["kind"] == "heal_player":
            ratio = 1.5 if effect.get("requirements", {}).get("flag") == "fire_bat_empowered" else .75
            entries.append({"entity": "companions", "id": "fire_bat_dragon",
                            "path": f"round_start_effects.{_selector(effect)}.scale_from_damage",
                            "set": {"source": "previous_damage_enemy", "ratio": ratio}})
    overlays = result["difficulty_overlays"]["normal"]
    for entry in entries:
        address = (entry["entity"], entry["id"], entry["path"])
        if not any((old["entity"], old["id"], old["path"]) == address for old in overlays):
            overlays.append(entry)
    result["meta"]["content_revision"] = max(result["meta"]["content_revision"], REVISION)
    validate_difficulty(result)
    return result


def main() -> None:
    revisions = {}
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        original = json.loads(path.read_text(encoding="utf-8"))
        updated = migrate(original)
        if updated != original:
            path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        revisions[name] = {"content_revision": updated["meta"]["content_revision"], "overlay_sha256": overlay_fingerprint(updated)}
        print(f"{name}: {updated['meta']['content_revision']}")
    guard = ROOT / "host/prompt/processed/difficulty/overlay_revision.json"
    guard.write_text(json.dumps(revisions, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
