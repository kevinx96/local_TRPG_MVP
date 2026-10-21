"""Normal-only EXP, choices and spell learning. No I/O or model calls."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

EVENT_TEMPLATES = {
    "exp_gained": "経験値を{amount}獲得した。",
    "level_up": "レベルが{level}に上がった！",
    "skill_gained": "新たなスキル「{name}」を習得した！",
    "passive_choice_pending": "Lv{level}のパッシブスキルが選択可能になった。",
    "passive_chosen": "パッシブ「{name}」を習得した！",
    "spell_learned": "術式を解読し、「{name}」を習得した！",
}


def enabled(session: dict[str, Any]) -> bool:
    return (session.get("difficulty", "baby") == "normal"
            and session.get("scenario_pack", {}).get("progression", {}).get("level_model") == "exp")


def definition(session: dict[str, Any], character: dict[str, Any] | None = None) -> dict[str, Any]:
    actor = character or session["character"]
    return next((entry for entry in session.get("scenario_pack", {}).get("class_progression", [])
                 if entry["id"] == actor.get("character_id")), {})


def effects(session: dict[str, Any]) -> dict[str, Any]:
    if not enabled(session):
        return {}
    catalog = {entry["id"]: entry for entry in definition(session).get("passives", [])}
    result = {}
    for selected in session["character"].get("passives", []):
        tiers = catalog.get(selected["id"], {}).get("tiers", [])
        if 0 < selected["tier"] <= len(tiers):
            result.update(deepcopy(tiers[selected["tier"] - 1]["effects"]))
    return result


def _event(session: dict[str, Any], kind: str, data: dict[str, Any]) -> None:
    from .state import record_state_event
    record_state_event(session, kind, EVENT_TEMPLATES[kind].format(**data), data)


def _grant_actives(session: dict[str, Any], actor: dict[str, Any], *, announce: bool = False) -> list[str]:
    skills = actor.setdefault("skills", [])
    gained = []
    for entry in definition(session, actor).get("actives", []):
        if not int(actor.get("skills_cleared_through_level", 0)) < entry["level"] <= actor.get("level", 1):
            continue
        skill = entry["skill"]
        if any(old.get("id") == skill["id"] for old in skills):
            continue
        skills[:] = [old for old in skills if not skill.get("replaces") or old.get("name") != skill["replaces"]]
        skills.append(deepcopy(skill))
        gained.append(skill["id"])
        if announce:
            _event(session, "skill_gained", {"skill_id": skill["id"], "name": skill["name"]})
    return gained


def _initialize_actor(session: dict[str, Any], actor: dict[str, Any], *, migrate: bool) -> None:
    config = session["scenario_pack"]["progression"]
    level = actor.setdefault("level", 1)
    actor.setdefault("exp", int(config["exp_table"].get(str(level), 0)))
    actor.setdefault("passives", [])
    actor.setdefault("passive_history", {})
    actor.setdefault("exp_rewarded_quests", [])
    template = next((entry for entry in session["scenario_pack"].get("characters", [])
                     if entry["id"] == actor.get("character_id")), {})
    skills = actor.setdefault("skills", [])
    if migrate:
        if actor is session["character"] and not actor.get("skills_cleared_through_level"):
            event_level = 1
            for event in session.get("event_log", []):
                data = event.get("data", {})
                if event.get("kind") == "level_up":
                    event_level = int(data.get("level", event_level))
                if event.get("kind") in {"skills_cleared", "clear_skills"} or data.get("clear_skills"):
                    actor["skills_cleared_through_level"] = int(data.get("level", event_level))
        old_ids = {skill["id"] for skill in template.get("level_skills", [])}
        skills[:] = [skill for skill in skills if skill.get("id") not in old_ids]
        if not actor.get("skills_cleared_through_level"):
            for skill in template.get("skills", []):
                existing = next((old for old in skills if old.get("id") == skill["id"]), None)
                if existing is None:
                    skills.append(deepcopy(skill))
                else:
                    for key in ("conditional_bonus", "spell_tier"):
                        if key in skill:
                            existing[key] = deepcopy(skill[key])
    _grant_actives(session, actor)
    actor.setdefault("learned_spells", [skill["id"] for skill in skills if skill.get("spell_tier") == "basic"])


def initialize(session: dict[str, Any]) -> bool:
    """Defer old-save migration through settlement; repair absent fields safely."""
    if not enabled(session) or (session.get("combat") and session.get("progression_revision") != "050"):
        return False
    before = deepcopy((session["character"], session.get("pending_passive_choices"), session.get("progression_revision")))
    migrate = session.get("progression_revision") != "050"
    _initialize_actor(session, session["character"], migrate=migrate)
    actor = session["character"]
    session["pending_passive_choices"] = [
        group["level"] for group in definition(session).get("passive_groups", [])
        if group["level"] <= actor["level"] and str(group["level"]) not in actor["passive_history"]
    ]
    saved_characters = [(session.get("combat") or {}).get("original_character")]
    saved_characters += [snapshot.get("state", {}).get("character")
                         for snapshot in session.get("area_snapshots", {}).values()]
    for saved in saved_characters:
        if isinstance(saved, dict):
            _initialize_actor(session, saved, migrate=migrate)
    session["progression_revision"] = "050"
    return before != (actor, session["pending_passive_choices"], session["progression_revision"])


def reward(session: dict[str, Any], amount: int, source: str) -> None:
    if not enabled(session) or amount <= 0:
        return
    if session.get("progression_revision") != "050":
        # Settlement can still hold the finished battle for narration.
        battle = session.pop("combat", None)
        try:
            initialize(session)
        finally:
            session["combat"] = battle
    actor = session["character"]
    config = session["scenario_pack"]["progression"]
    actor["exp"] = actor.get("exp", 0) + amount
    next_exp = config["exp_table"].get(str(actor.get("level", 1) + 1))
    _event(session, "exp_gained", {"amount": amount, "source": source, "total": actor["exp"], "next": next_exp})
    while actor.get("level", 1) < config["max_level"]:
        level = actor.get("level", 1) + 1
        if actor["exp"] < config["exp_table"][str(level)]:
            break
        gains = config["level_gains"].get(actor.get("character_id"), {})
        for resource in ("hp", "mp", "sp"):
            key = "max_" + resource
            actor[key] += int(gains.get(key, 0))
            actor[resource] = actor[key]
        for key, value in gains.get("attributes", {}).items():
            actor.setdefault("attributes", {})[key] = actor.get("attributes", {}).get(key, 0) + value
        actor["level"] = level
        new_skills = _grant_actives(session, actor, announce=True)
        group = next((g for g in definition(session).get("passive_groups", []) if g["level"] == level), None)
        if group:
            session.setdefault("pending_passive_choices", []).append(level)
            names = {p["id"]: p["name"] for p in definition(session)["passives"]}
            _event(session, "passive_choice_pending", {"level": level, "options": [names[p] for p in group["options"]]})
        _event(session, "level_up", {"level": level, "levels_gained": 1, "gains_per_level": gains,
                                   "exp": actor["exp"], "new_skills": new_skills,
                                   "passive_choice_level": level if group else None})


def quest_rewards(session: dict[str, Any], before: list[dict[str, Any]]) -> None:
    if not enabled(session):
        return
    from .quests import public_quests
    previous = {q["id"]: q["status"] for q in before}
    paid = session["character"].setdefault("exp_rewarded_quests", [])
    for quest in public_quests(session):
        source = "quest:" + quest["id"]
        if (quest["id"] != "main_ignis" and quest["status"] == "completed"
                and previous.get(quest["id"]) != "completed" and quest["id"] not in paid):
            paid.append(quest["id"])
            reward(session, session["scenario_pack"]["progression"]["exp_rewards"]["quest"], source)


def _option(entry: dict[str, Any], tier: int) -> dict[str, Any]:
    name = entry["name"] + (f"+{tier - 1}" if tier > 1 else "")
    return {"id": entry["id"], "tier": tier, "name": name, "description": entry["tiers"][tier - 1]["description"]}


def public_progression(session: dict[str, Any]) -> dict[str, Any] | None:
    if not enabled(session):
        return None
    actor = session["character"]
    config = session["scenario_pack"]["progression"]
    catalog = {p["id"]: p for p in definition(session).get("passives", [])}
    selected = {p["id"]: p["tier"] for p in actor.get("passives", [])}
    pending = []
    for group in definition(session).get("passive_groups", []):
        if group["level"] not in session.get("pending_passive_choices", []):
            continue
        options = []
        for identifier in group["options"]:
            entry = catalog[identifier]
            tier = selected.get(identifier, 0)
            option = _option(entry, min(tier + 1, len(entry["tiers"])))
            option.update(name=entry["name"] + (f"+{tier - 1}" if tier > 1 else ""),
                          next_name=option["name"],
                          current_description=entry["tiers"][tier - 1]["description"] if tier else "",
                          next_description=option["description"])
            options.append(option)
        pending.append({"level": group["level"], "options": options})
    next_exp = config["exp_table"].get(str(actor.get("level", 1) + 1))
    return {"level": actor.get("level", 1), "exp": actor.get("exp", 0),
            "exp_to_next": max(0, next_exp - actor.get("exp", 0)) if next_exp is not None else None,
            "passives": [_option(catalog[k], v) for k, v in selected.items() if k in catalog],
            "pending": pending}


def choose_passive(session: dict[str, Any], level: int, passive_id: str) -> dict[str, Any]:
    """Return an updated deep copy; never mutate the input or persist a save."""
    result = deepcopy(session)
    pending = result.get("pending_passive_choices", [])
    if not enabled(result) or result.get("combat") or not pending or type(level) is not int or level != min(pending):
        raise ValueError("このレベルのパッシブは現在選択できません。")
    definitions = definition(result)
    group = next((g for g in definitions["passive_groups"] if g["level"] == level), {})
    if passive_id not in group.get("options", []):
        raise ValueError("そのパッシブは選択できません。")
    actor = result["character"]
    selected = next((p for p in actor.setdefault("passives", []) if p["id"] == passive_id), None)
    entry = next(p for p in definitions["passives"] if p["id"] == passive_id)
    tier = selected["tier"] + 1 if selected else 1
    if tier > len(entry["tiers"]):
        raise ValueError("そのパッシブは選択できません。")
    if selected:
        selected["tier"] = tier
    else:
        actor["passives"].append({"id": passive_id, "tier": tier})
    actor.setdefault("passive_history", {})[str(level)] = passive_id
    pending.remove(level)
    _event(result, "passive_chosen", {"level": level, "passive_id": passive_id, "name": _option(entry, tier)["name"]})
    return result


def learn_reason(session: dict[str, Any], item: dict[str, Any]) -> str:
    if not enabled(session) or item.get("category") != "spellbook" or not item.get("learn_skill"):
        return "この道具は解読できる術式巻物ではない。"
    if session.get("combat"):
        return "戦闘中は術式巻物を解読できない。"
    actor = session["character"]
    if actor.get("character_id") not in item.get("learnable_by", []):
        return "魔法使いにしか解読できない術式だ。"
    if any(s.get("id") == item["learn_skill"]["id"] for s in actor.get("skills", [])):
        return "この術式はすでに習得している。"
    return ""


def learn_spell(session: dict[str, Any], item_id: str) -> dict[str, Any]:
    result = deepcopy(session)
    actor = result["character"]
    item = next((i for i in actor.get("inventory", []) if i.get("id") == item_id and i.get("quantity", 1) > 0), None)
    if item is None:
        raise ValueError("対象の道具を所持していません。")
    reason = learn_reason(result, item)
    if reason:
        raise ValueError(reason)
    skill = deepcopy(item["learn_skill"])
    actor.setdefault("skills", []).append(skill)
    actor.setdefault("learned_spells", []).append(skill["id"])
    item["quantity"] = item.get("quantity", 1) - 1
    if item["quantity"] <= 0:
        actor["inventory"].remove(item)
    _event(result, "spell_learned", {"skill_id": skill["id"], "item_id": item_id, "name": skill["name"]})
    return result
