from __future__ import annotations

from typing import Any, Optional


WORLD_STATE_KEY = "world_state"


def ensure_world_state(session: dict[str, Any]) -> dict[str, str]:
    """Migrate legacy position fields and return the canonical world position."""
    pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else {}
    world = session.get(WORLD_STATE_KEY)
    if not isinstance(world, dict):
        world = {}

    scene_id = str(world.get("scene_id") or session.get("current_scene") or "").strip()
    location_id = str(world.get("location_id") or session.get("current_location") or "").strip()
    if not scene_id:
        scene_id = str(pack.get("meta", {}).get("initial_scene") or "start")
    if not location_id:
        location_id = _initial_location(pack, scene_id)

    location_scene = _scene_for_location(pack, location_id)
    if location_scene:
        scene_id = location_scene
    elif not _find_scene(pack, scene_id):
        scene_id = str(pack.get("meta", {}).get("initial_scene") or scene_id or "start")
        location_id = _initial_location(pack, scene_id)

    canonical = {"scene_id": scene_id, "location_id": location_id}
    session[WORLD_STATE_KEY] = canonical
    session.pop("current_scene", None)
    session.pop("current_location", None)
    return canonical


def current_scene_id(session: dict[str, Any]) -> str:
    return ensure_world_state(session)["scene_id"]


def current_location_id(session: dict[str, Any]) -> str:
    return ensure_world_state(session)["location_id"]


def current_location_title(session: dict[str, Any]) -> str:
    pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else {}
    location_id = current_location_id(session)
    location = _find_location(pack, location_id)
    if location:
        return str(location.get("title") or location.get("name") or location_id)
    return location_id


def commit_world_position(
    session: dict[str, Any],
    *,
    scene_id: Optional[str] = None,
    location_id: Optional[str] = None,
) -> tuple[bool, str]:
    """Atomically validate and commit an engine-authorized world transition."""
    pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else {}
    current = ensure_world_state(session)
    requested_scene = str(scene_id or "").strip()
    requested_location = str(location_id or "").strip()

    if requested_location:
        location = _find_location(pack, requested_location)
        if not location:
            return False, f"unknown location: {requested_location}"
        owner_scene = _scene_for_location(pack, requested_location)
        if not owner_scene:
            return False, f"location has no scene_id: {requested_location}"
        if requested_scene and requested_scene != owner_scene:
            return False, f"scene/location mismatch: {requested_scene}/{requested_location}"
        requested_scene = owner_scene
    elif requested_scene:
        if not _find_scene(pack, requested_scene):
            return False, f"unknown scene: {requested_scene}"
        requested_location = _initial_location(pack, requested_scene)
        if not requested_location:
            return False, f"scene has no initial location: {requested_scene}"
    else:
        return True, ""

    if requested_scene != current["scene_id"] and not _scene_transition_allowed(pack, current["scene_id"], requested_scene):
        return False, f"scene transition is not allowed: {current['scene_id']} -> {requested_scene}"

    session[WORLD_STATE_KEY] = {
        "scene_id": requested_scene,
        "location_id": requested_location,
    }
    return True, ""


def _initial_location(pack: dict[str, Any], scene_id: str) -> str:
    scene = _find_scene(pack, scene_id)
    if scene:
        location_ids = _text_list(scene.get("location_ids"))
        if location_ids:
            return location_ids[0]
    for location in pack.get("locations", []):
        if isinstance(location, dict) and str(location.get("scene_id") or "") == scene_id:
            return str(location.get("id") or "")
    return scene_id


def _scene_for_location(pack: dict[str, Any], location_id: str) -> str:
    location = _find_location(pack, location_id)
    if location and str(location.get("scene_id") or "").strip():
        return str(location["scene_id"]).strip()
    for scene in pack.get("scenes", []):
        if isinstance(scene, dict) and location_id in _text_list(scene.get("location_ids")):
            return str(scene.get("id") or "")
    return ""


def _find_scene(pack: dict[str, Any], scene_id: str) -> Optional[dict[str, Any]]:
    for scene in pack.get("scenes", []):
        if isinstance(scene, dict) and str(scene.get("id") or "") == scene_id:
            return scene
    return None


def _find_location(pack: dict[str, Any], location_id: str) -> Optional[dict[str, Any]]:
    for location in pack.get("locations", []):
        if isinstance(location, dict) and str(location.get("id") or "") == location_id:
            return location
    return None


def _scene_transition_allowed(pack: dict[str, Any], current_scene_id: str, target_scene_id: str) -> bool:
    if current_scene_id == target_scene_id:
        return True
    current_scene = _find_scene(pack, current_scene_id)
    if not current_scene:
        return True
    next_scene_ids = _text_list(current_scene.get("next_scene_ids"))
    return not next_scene_ids or target_scene_id in next_scene_ids


def _text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
