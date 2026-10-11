from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from host import state
from scripts.balance import checkpoints
from .redundancy import MANIFEST, finish_witness


def generate() -> dict[str, Any]:
    start = ["check_supplies", "go_inn", "invite_robin:success", "ask_robin_rumor", "return_castle_from_inn", "go_dark_forest:success", "@victory"]
    fortress = ["help_lost_goblin", "enter_goblin_fort", "@victory", "@victory", "explore_fort_right", "bypass_hobgoblin:success", "give_correct_password", "@victory", "return_lost_goblin_box"]
    main = ["crossroads_forward", "continue_from_elf_spring", "@victory"]
    cave_trip = ["exit_back", "wolves_back", "inspect_spring_wall", "decode_seal:success", "@victory", "cave_right", "hot_spring_forward", "@victory", "@victory", "leave_prism_tree", "continue_from_elf_spring", "pass_cleared_wolves"]
    paths = {"spring": start + ["ignore_lost_goblin:success", "@victory"] + main,
             "fort": start + fortress + main,
             "cave": start + ["ignore_lost_goblin:success", "@victory"] + main + cave_trip}
    keys = []

    def key(identifier: str, minimum: int) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        keys.append(dict(id=identifier, minimum=minimum, sources=sources))
        return sources

    def add(sources: list[dict[str, Any]], identifier: str, location: str, step: str, kind: str,
            reward: dict[str, str], witnesses: dict[str, list[str]], **extra: Any) -> None:
        sources.append(dict(id=identifier, location=location, step=step, type=kind, reward=reward, witnesses=witnesses, **extra))

    town = {r: p + ["return_inn_after_forest", "return_castle_from_inn"] for r, p in paths.items()}
    house = {r: p + ["leave_forest_for_village", "approach_burning_village_carefully:success", "@victory"] for r, p in paths.items()}
    frozen = {r: p + ["leave_burning_house"] for r, p in house.items()}
    ice = {r: p + ["investigate_frozen_village"] for r, p in frozen.items()}
    after = {r: p + ["@victory", "@victory"] for r, p in ice.items()}
    village = {r: p + ["visit_village"] for r, p in after.items()}
    valley_steps = ["accept_ian_request", "@victory", "cross_lava_bridge:success", "enter_dragon_nest"]
    last = {r: p + valley_steps + ["@victory"] for r, p in after.items()}

    def tail(paths: dict[str, list[str]], *steps: str) -> dict[str, list[str]]:
        return {r: p + list(steps) for r, p in paths.items()}

    funding = key("supplies", 0)
    add(funding, "supplies", "castle", "check_supplies", "story", {"gold": "50"}, tail(paths, "leave_forest_for_village"))
    cold = key("ice_options", 2)
    add(cold, "village_shop", "village", "shop:village_shop:ice_charm", "purchase", {"item": "ice_charm", "name": "氷の護符"}, tail(village, "shop:village_shop:ice_charm"))
    add(cold, "fusion", "forge", "accept_sword_fusion", "quest", {"name": "氷鉄の大剣"}, tail(town, "go_forge", "show_sword_to_blacksmith", "accept_sword_fusion"))
    add(cold, "ian", "ian_ice_katana_aftermath", "accept_ian_request", "quest", {"name": "氷鉄の大剣"}, tail(after, "accept_ian_request"))
    add(cold, "sarah", "item_shop", "shop:sarah_shop:ice_charm", "purchase", {"item": "ice_charm"}, tail(village, "return_castle_from_village", "go_item_shop", "shop:sarah_shop:ice_charm"))
    craft = ["visit_village", "return_castle_from_village", "go_forge", "forge_ice_charm"]
    add(cold, "ice_battle_craft", "ice_elemental_encounter", "@victory", "battle_craft", {"item": "ice_crystal"}, tail(after, *craft), crafted_item="ice_charm")
    add(cold, "ice_observe_craft", "ice_elemental_encounter", "observe:frost_crystal", "observe_craft", {"item": "ice_crystal"}, tail(ice, "observe:frost_crystal", "bypass_ice_elemental:success", "@victory", *craft), crafted_item="ice_charm")
    add(cold, "mage_ice", "dragon_valley_loc", "@skill:mage_lv5_a", "class_skill", {}, tail(after, *valley_steps, "@skill:mage_lv5_a"), character="mage", skill="mage_lv5_a", element="ice")
    holy = key("holy_options", 2)
    add(holy, "supplies", "castle", "check_supplies", "story", {"item": "holy_water"}, tail(paths, "leave_forest_for_village"))
    add(holy, "sarah", "item_shop", "shop:sarah_shop:holy_water", "purchase", {"item": "holy_water"}, tail(town, "go_item_shop", "shop:sarah_shop:holy_water"))
    add(holy, "general", "castle", "ask_general_advice:success", "dialogue", {"item": "holy_water"}, tail(town, "ask_general_advice:success"))
    add(holy, "cleric", "ian_ice_katana_aftermath", "accept_ian_request", "class_skill", {}, tail(after, "accept_ian_request"), character="cleric", skill="cleric_lv3_a", element="holy")
    password = key("knows_fort_password", 2)
    fort_paths = {r: (start if r == "fort" else town[r] + ["go_dark_forest:success", "pass_cleared_forest"]) for r in paths}
    # Every witness goes through its main branch; spring can revisit the crossroads.
    for identifier, location, step, kind, extension in [
        ("lost_goblin", "lost_goblin_crossroads", "help_lost_goblin", "quest", ["help_lost_goblin"]),
        ("hobgoblin", "goblin_fort_second_right", "bypass_hobgoblin:success", "sneak", fortress[:6]),
        ("window", "goblin_fort_third_gate", "observe:iron_gate_window", "observe", fortress[:6] + ["observe:iron_gate_window"]),
        ("robin", "goblin_fort_third_gate", "@entry", "companion_hint", fortress[:6] + ["@entry"]),
    ]:
        witnesses = tail(fort_paths, *extension)
        if identifier == "lost_goblin":
            witnesses["fort"] += ["enter_goblin_fort", "@victory"]
        if identifier == "robin":
            approach = ["accept_robin_goblin_quest", "@victory", "@victory", "explore_fort_right", "@victory", "@entry"]
            witnesses = {r: (start[:4] + approach if r == "fort" else town[r] + ["go_inn", *approach]) for r in paths}
        add(password, identifier, location, step, kind, {"flag": "knows_fort_password"}, witnesses)
    scale = key("white_dragon_scale", 3)
    add(scale, "frost_core", "village_frozen_clue", "inspect_frost_core:success", "exploration", {"item": "white_dragon_scale"}, tail(frozen, "inspect_frost_core:success"))
    add(scale, "wolf", "frost_wolf_battle", "@victory", "battle", {"item": "white_dragon_scale"}, after)
    add(scale, "wound", "ignis_last_breath", "examine_ignis_wound", "exploration", {"item": "white_dragon_scale"}, tail(last, "examine_ignis_wound"))
    robin = tail(paths, "return_inn_after_forest", "ask_robin_stolen_scale")
    for r in ("spring", "cave"):
        robin[r] = paths[r] + ["return_inn_after_forest", "accept_robin_goblin_quest", *fortress[2:], "fort_shortcut", "return_inn_after_forest", "ask_robin_stolen_scale"]
    add(scale, "robin", "inn", "ask_robin_stolen_scale", "quest", {"item": "white_dragon_scale"}, robin)
    add(scale, "merchant", "alley_night", "buy_white_scale", "purchase", {"item": "white_dragon_scale"}, tail(town, "go_alley", "wait_for_night_in_alley", "buy_white_scale"))
    fire = key("fire_options", 2)
    add(fire, "core", "dragon_valley_loc", "@victory", "story", {"item": "red_dragon_core"}, last)
    add(fire, "bat", "item_shop", "borrow_fire_bat_dragon", "companion", {"companion": "fire_bat_dragon"}, tail(town, "go_item_shop", "borrow_fire_bat_dragon"))
    add(fire, "sarah", "item_shop", "shop:sarah_shop:fireball_scroll", "purchase", {"item": "fireball_scroll"}, tail(town, "go_item_shop", "shop:sarah_shop:fireball_scroll"))
    add(fire, "mage", "ian_ice_katana_aftermath", "accept_ian_request", "class_skill", {}, tail(after, "accept_ian_request"), character="mage", skill="mage_lv3_b", element="fire")
    for flag, location, step, path in [
        ("frost_trace_seen", "village_frozen_clue", "inspect_frost_core:failure", tail(frozen, "inspect_frost_core:failure")),
        ("heard_human_caused_dragon_return", "magic_shop", "ask_blue_mage_rumor", tail(town, "go_magic_shop", "ask_blue_mage_rumor")),
        ("heard_ignis_last_words", "ignis_last_breath", "hear_ignis_last_words", tail(last, "hear_ignis_last_words")),
        ("noticed_general_frost", "castle", "observe:general_breath", tail(town, "observe:general_breath")),
        ("heard_treaty_lore", "village", "ask_elder_treaty", tail(village, "ask_elder_treaty")),
    ]:
        sources = key(flag, 0)
        add(sources, flag, location, step, "observe" if step.startswith("observe:") else "dialogue", {"flag": flag}, path)
        if flag == "heard_treaty_lore":
            add(sources, "ian", "inn", "ask_ian_dragon_tale", "dialogue", {"flag": flag}, tail(town, "go_inn", "ask_ian_dragon_tale"))
            add(sources, "riku", "village", "return_riku", "quest", {"flag": flag}, tail(house, "break_burning_beam:success", "visit_village", "return_riku"))
        if flag == "noticed_general_frost":
            add(sources, "general_high_roll", "castle", "ask_general_advice:high", "dialogue", {"flag": flag}, tail(town, "ask_general_advice:high"))
    betrayal = key("heard_xanxus_betrayal", 0)
    phantom_paths = tail(frozen, "skip_frozen_clue_before_xanxus", "bluff_xanxus:failure", "@defeat", "accept_xanxus_fire_seed",
        "investigate_frozen_village", "@victory", "@victory", "accept_ian_request", "@victory", "cross_lava_bridge:success", "cleanse_fire_seed", "@victory")
    add(betrayal, "phantom", "xanxus_phantom_battle", "@victory", "battle", {"flag": "heard_xanxus_betrayal"}, phantom_paths)
    rescue_paths = deepcopy(frozen)
    for steps in rescue_paths.values():
        index = steps.index("go_dark_forest:success")
        steps[index:index] = ["go_magic_shop", "invite_blue_mage", "return_castle_from_magic_shop"]
    rescue_paths = tail(rescue_paths, "skip_frozen_clue_before_xanxus", "bluff_xanxus:failure", "@defeat", "refuse_xanxus_with_rescue", "@victory",
        "investigate_frozen_village", "@victory", "@victory", *valley_steps[:-1], "@entry")
    add(betrayal, "warlock", "warlock_at_nest", "@entry", "companion_hint", {"flag": "heard_xanxus_betrayal"}, rescue_paths)
    knowledge = key("purification_knowledge", 2)
    for entry in list(keys):
        if entry["id"] in {"frost_trace_seen", "noticed_general_frost", "heard_treaty_lore", "white_dragon_scale"}:
            for source in entry["sources"]:
                if source["location"] == "ignis_last_breath":
                    continue
                if entry["id"] == "white_dragon_scale" and source["id"] == "frost_core":
                    continue  # The same investigation is already counted via frost_trace_seen.
                clone = deepcopy(source)
                clone["id"] = entry["id"] + "_" + source["id"]
                knowledge.append(clone)
    means = key("purification_means", 2)
    means.extend(deepcopy([source for source in holy if source["type"] != "class_skill"]))
    add(means, "cleric_prayer", "dragon_valley_loc", "@skill:purify_ignis_prayer", "class_special", {},
        tail(after, *valley_steps, "@skill:purify_ignis_prayer"), character="cleric",
        special_action="purify_ignis_prayer")
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    for entry in keys:
        for source in entry["sources"]:
            for branch, steps in source["witnesses"].items():
                source["witnesses"][branch] = finish_witness(pack, steps, source.get("character", "hero"))
    return dict(routes={"spring": {"landmark": "elf_spring"}, "fort": {"landmark": "goblin_fort"}, "cave": {"landmark": "cave_seal"}},
                notes=["路线允许返回城镇及砦支线；每个来源单独重放合法动作及成功战斗，不把所有来源同时领取。",
                       "职业来源只计相应职业；不叠加职业。资金是一次性修复，线索是可替代证据，逐一核验但不要求每个可选 flag 有两个来源。"], keys=keys)


if __name__ == "__main__":
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(generate(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
