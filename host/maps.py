from __future__ import annotations

from copy import deepcopy
from typing import Any

from .world_state import current_location_id


def public_maps(session: dict[str, Any]) -> dict[str, Any]:
    from .state import _session_requirement_passes

    location = current_location_id(session)
    maps = [m for m in session.get('scenario_pack', {}).get('maps', [])
            if _session_requirement_passes(m.get('requirements'), session)]
    visited = set(session.get("visited_locations", []))
    flags = session.get("flags", {})
    current = next((m for m in sorted(maps, key=lambda m: not bool(m.get('parent')))
                    if any(location in n['location_ids'] for n in m['nodes'])), None)
    if not current:
        return {"current_map_id": None, "maps": []}
    result = []
    for source in maps:
        edges = [e for e in source["edges"] if not e.get("visible_after") or flags.get(e["visible_after"])]
        seen = {n["id"] for n in source["nodes"] if visited.intersection(n["location_ids"])
                or (n.get("known_after") and flags.get(n["known_after"]))}
        neighbors = {e[end] for e in edges for end, other in (("from", "to"), ("to", "from")) if e[other] in seen}
        nodes = []
        for node in source["nodes"]:
            visibility = "visited" if node["id"] in seen else "adjacent-unknown" if node["id"] in neighbors else "hidden"
            if node.get("locked_until") and node["id"] in seen and not flags.get(node["locked_until"]):
                visibility = "locked"
            public = {"id": node["id"], "x": node["x"], "y": node["y"], "visibility": visibility,
                      "current": location in node["location_ids"]}
            if visibility in {"visited", "locked"}:
                public.update({k: deepcopy(node[k]) for k in ("label", "kind", "description", "recommended", "submap") if k in node})
                location_record = next((loc for loc in session.get("scenario_pack", {}).get("locations", [])
                                        if loc.get("id") == next(iter(node["location_ids"]), None)), {})
                for variant in location_record.get("description_variants", []):
                    if _session_requirement_passes(variant.get("requirements"), session):
                        public["description"] = variant["text"]
                        break
                if node.get("locked_until") and flags.get(node["locked_until"]):
                    public["kind"] = "branch"
            nodes.append(public)
        visible = {n["id"] for n in nodes if n["visibility"] != "hidden"}
        result.append({"id": source["id"], "title": source["title"], "parent": source.get("parent"),
                       "nodes": nodes, "edges": [{"from": e["from"], "to": e["to"], "visited": e["from"] in seen and e["to"] in seen}
                       for e in edges if e["from"] in visible and e["to"] in visible]})
    return {"current_map_id": current["id"], "maps": result}


def movement_action(session: dict[str, Any], node_id: str) -> dict[str, Any]:
    from .state import action_requirement_status, resolve_action

    if session.get("game_over"):
        raise ValueError("物語はすでに終了しています。")
    if session.get("combat"):
        raise ValueError("戦闘中は移動できません。")
    location = current_location_id(session)
    current_map = public_maps(session)['current_map_id']
    for map_data in session.get("scenario_pack", {}).get("maps", []):
        if map_data['id'] != current_map:
            continue
        source = next((n for n in map_data["nodes"] if location in n["location_ids"]), None)
        if not source:
            continue
        edge = next((e for e in map_data["edges"] if e["from"] == source["id"] and e["to"] == node_id
                     and (not e.get("visible_after") or session.get("flags", {}).get(e["visible_after"]))), None)
        if not edge:
            raise ValueError("隣接する場所を選んでください。")
        action_id = edge.get("action_by_location", {}).get(location, edge.get("action_id"))
        if not action_id:
            raise ValueError("この場所へは行動を選んで進んでください。")
        action = resolve_action(session, action_id=action_id)
        if action is None:
            raise ValueError("この行動はまだ選択できません。")
        enabled, reason = action_requirement_status(action, session)
        if not enabled:
            raise ValueError(reason)
        return action
    raise ValueError("現在の場所には地図がありません。")
