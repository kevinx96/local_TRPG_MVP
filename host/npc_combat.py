"""Engine-owned NPC hostility, confirmation and persistent consequences."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .world_state import current_location_id


def gone(session: dict[str, Any], npc_id: str) -> bool:
    flags = session.get("flags", {})
    return bool(flags.get(f"npc_gone_{npc_id}") or
                (npc_id == "dragon_knight" and flags.get("dragon_knight_defeated")))


def present(session: dict[str, Any], npc_id: str) -> bool:
    from . import state

    location = state._current_location_record(session) or {}
    return (npc_id in location.get("npc_ids", []) and not gone(session, npc_id)
            and state._session_requirement_passes(location.get("npc_requirements", {}).get(npc_id), session))


def related_available(session: dict[str, Any], record: dict[str, Any]) -> bool:
    identifiers = record.get("npc_ids_required", [])
    if record.get("npc_id"):
        identifiers = [*identifiers, record["npc_id"]]
    return all(not gone(session, identifier) for identifier in identifiers)


def portrait_available(session: dict[str, Any], image: str) -> bool:
    if not image:
        return False
    pack = session.get("scenario_pack", {})
    if any(npc.get("image") == image and gone(session, npc["id"]) for npc in pack.get("npcs", [])):
        return False
    return not any(portrait == image and gone(session, identifier)
                   for location in pack.get("locations", [])
                   for identifier, portrait in location.get("npc_portrait_overrides", {}).items())


def filter_actions(session: dict[str, Any], actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not any(value for key, value in session.get("flags", {}).items()
               if key.startswith("npc_gone_") or key == "dragon_knight_defeated"):
        return actions
    result = []
    for source in actions:
        if not related_available(session, source):
            continue
        action = deepcopy(source)
        if "children" in action:
            action["children"] = filter_actions(session, action["children"])
            if not action["children"]:
                continue
        result.append(action)
    return result


def absence_text(session: dict[str, Any], text: str) -> str:
    """Only replace authored passages explicitly inventoried by the migration."""
    if not text or not any(value for key, value in session.get("flags", {}).items() if key.startswith("npc_gone_")):
        return text
    for entry in session.get("scenario_pack", {}).get("npc_absence_texts", []):
        if entry["text"] and entry["text"] in text and any(gone(session, identifier) for identifier in entry["npc_ids"]):
            replacements = entry.get("replacements", {})
            replacement = " ".join(replacements[identifier] for identifier in entry["npc_ids"]
                                   if identifier in replacements and gone(session, identifier))
            text = text.replace(entry["text"], replacement or entry["replacement"])
    return text


def absence_context(session: dict[str, Any], value: Any) -> Any:
    if not any(value for key, value in session.get("flags", {}).items() if key.startswith("npc_gone_")):
        return value
    if isinstance(value, dict):
        return {key: absence_context(session, child) for key, child in value.items()}
    if isinstance(value, list):
        return [absence_context(session, child) for child in value]
    return absence_text(session, value) if isinstance(value, str) else value


def _npc(session: dict[str, Any], npc_id: str) -> dict[str, Any]:
    return next((npc for npc in session["scenario_pack"].get("npcs", []) if npc["id"] == npc_id), {})


def _profile(session: dict[str, Any], npc_id: str) -> dict[str, Any]:
    profile = deepcopy(_npc(session, npc_id).get("npc_combat", {}))
    profile.update(profile.get("locations", {}).get(current_location_id(session), {}))
    return profile


def request_attack(session: dict[str, Any], npc_id: str) -> dict[str, Any]:
    if session.get("pending_npc_attack") or session.get("combat") or not present(session, npc_id):
        return {"text": "その相手はここにはいません。", "outcome": "rejected"}
    profile = _profile(session, npc_id)
    if profile.get("category") == "protected":
        return {"text": profile["blocked_text"], "outcome": "blocked"}
    if profile.get("category") not in {"killable", "child", "treason", "special"}:
        return {"text": "今は、その相手に刃を向けるべき時ではない。", "outcome": "blocked"}
    session["pending_npc_attack"] = {"npc_id": npc_id, "location_id": current_location_id(session)}
    return {"text": f"{_npc(session, npc_id)['name']}に武器を向けようとしている。本当に攻撃するか？",
            "outcome": "confirmation"}


def confirmation_actions(session: dict[str, Any]) -> list[dict[str, Any]]:
    pending = session.get("pending_npc_attack")
    if not pending:
        return []
    return [dict(id="npc_attack_confirm", text=f"{_npc(session, pending['npc_id'])['name']}を攻撃する",
                 risk="危険（戦闘）", npc_confirmation=True),
            dict(id="npc_attack_cancel", text="やめておく", risk="判定不要", npc_confirmation=True)]


def resolve_confirmation(session: dict[str, Any], action_id: str) -> str:
    from . import state

    pending = session.pop("pending_npc_attack")
    if action_id == "npc_attack_cancel":
        return "あなたは武器を下ろした。"
    npc_id = pending["npc_id"]
    if pending["location_id"] != current_location_id(session) or not present(session, npc_id):
        return "その相手はここにはいません。"
    profile = _profile(session, npc_id)
    if profile["category"] == "treason":
        state.apply_state_delta(session, {"game_over": {"ending": "treason", "title": "反逆者",
                                                        "reason": profile["ending_text"]}})
        return profile["ending_text"]
    return start_battle(session, npc_id)


def start_battle(session: dict[str, Any], npc_id: str, *, interception: bool = False) -> str:
    from . import combat, state

    profile = _profile(session, npc_id)
    if npc_id == "dragon_knight":
        encounter = deepcopy(session["scenario_pack"]["npc_combat"]["dragon_encounter"])
        intro = session["scenario_pack"]["npc_combat"]["interception_text" if interception else "challenge_text"]
        if interception:
            encounter["victory_effects"]["current_location"] = "royal_gate"
    else:
        participants = [] if profile["category"] == "child" else [npc_id]
        for guardian in profile.get("guardians", []):
            identifier = guardian["npc_id"]
            if gone(session, identifier) or not state._session_requirement_passes(guardian.get("requirements"), session):
                continue
            participants.extend([identifier] * guardian.get("count", 1))
        enemies = [_profile(session, identifier)["enemy_id"] for identifier in participants]
        encounter = dict(enemy_ids=enemies, auto_start=True, flee_allowed=True, encounter_class="elite",
                         npc_participants=list(dict.fromkeys(participants)), npc_target=npc_id,
                         npc_town=bool((state._current_location_record(session) or {}).get("town_npc_combat")))
        intro = "戦闘開始: " + "、".join(_npc(session, identifier)["name"] for identifier in participants)
        companion = session.get("companion") or {}
        if any(_profile(session, identifier).get("companion_id") == companion.get("id")
               for identifier in participants if _profile(session, identifier).get("companion_id")):
            state._set_companion(session, None)
    session["npc_encounter_override"] = encounter
    session["combat_start_requested"] = True
    try:
        if not combat.ensure_combat_started(session, intro_text=intro):
            raise combat.CombatError("この行動は現在選択できません。")
    finally:
        session.pop("npc_encounter_override", None)
    return intro


def dragon_action(session: dict[str, Any], *, interception: bool = False) -> str:
    settings = session["scenario_pack"]["npc_combat"]
    if interception or session.get("flags", {}).get("town_blood"):
        return start_battle(session, "dragon_knight", interception=interception)
    count = int(session.get("dragon_knight_talk_count", 0))
    session["dragon_knight_talk_count"] = count + 1
    return settings["dialogue"][count % len(settings["dialogue"])]


def aftermath(session: dict[str, Any], battle: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Commit casualties even if the player subsequently flees or loses."""
    from . import combat

    encounter = battle.get("encounter", {})
    casualties = [identifier for identifier in encounter.get("npc_participants", [])
                  if identifier != "guardian_guard" and any(
                      (enemy.get("npc_id") or encounter.get("npc_enemy_map", {}).get(enemy.get("template_id"))) == identifier
                      and combat._enemy_is_defeated(enemy) for enemy in battle["enemies"])
                  and not gone(session, identifier)]
    for identifier in list(casualties):
        casualties.extend(child for child in _profile(session, identifier).get("flee_dependents", [])
                          if not gone(session, child) and child not in casualties)
    guard_fallen = any(enemy.get("npc_id") == "guardian_guard" and combat._enemy_is_defeated(enemy)
                       for enemy in battle["enemies"])
    if not casualties and not guard_fallen:
        return {}, []
    flags = [f"npc_gone_{identifier}" for identifier in casualties]
    if encounter.get("npc_town"):
        flags.append("town_blood")
    texts = [_profile(session, identifier).get("fallen_text", "") for identifier in casualties]
    delta: dict[str, Any] = {"flags_set": flags, "inventory_add": [], "gold_change": 0}
    items = {item["id"]: item for item in session["scenario_pack"]["items"]}
    shops = session["scenario_pack"].get("shops", [])
    counters = []
    for identifier in casualties:
        owned = [shop for shop in shops if shop["keeper_npc"] == identifier]
        if owned:
            counters.append(next((shop for shop in owned if shop["location_id"] == battle["location_id"]), owned[0]))
    for shop in counters:
        stock = session.get("shop_stock", {}).get(shop["id"], {})
        for offer in shop["items"]:
            remaining = stock.get(offer["item_id"], offer.get("stock"))
            quantity = remaining if remaining is not None else int(offer["price"] >= 40)
            if quantity > 0:
                delta["inventory_add"].append({"id": offer["item_id"], "name": items[offer["item_id"]]["name"],
                                                "quantity": quantity})
        delta["gold_change"] += int(shop.get("counter_gold", 0))
        texts.append(f"{shop['title']}の品を手に入れた。")
    return delta, [text for text in texts if text]
