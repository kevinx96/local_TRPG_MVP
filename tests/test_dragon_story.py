import json
import random
import unittest
from pathlib import Path
from unittest.mock import patch

from host import app as app_module
from host import combat, state
from host.scenario_context import select_hybrid_prepared_turn


SCENARIO_ROOT = Path("host/prompt/processed")
SCENARIO_FILES = ("dragon_rpg.json", "dragon_rpg_hybrid.json")


def records(pack, section):
    return {record["id"]: record for record in pack.get(section, []) if record.get("id")}


def iter_actions(actions):
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        yield action
        yield from iter_actions(action.get("children"))


class DragonStoryTests(unittest.TestCase):
    def load_raw(self, filename="dragon_rpg_hybrid.json"):
        return json.loads((SCENARIO_ROOT / filename).read_text(encoding="utf-8-sig"))

    def create_runtime_session(self, character_id="hero"):
        public = state.create_session(
            str(SCENARIO_ROOT / "dragon_rpg_hybrid.json"),
            gm_mode="semi",
            character_id=character_id,
        )
        return state.load_session(public["id"])

    def test_base_and_hybrid_have_the_same_public_title_and_current_revision(self):
        for filename in SCENARIO_FILES:
            with self.subTest(filename=filename):
                meta = self.load_raw(filename)["meta"]
                self.assertEqual(meta["title"], "紅き邪竜イグニス")
                self.assertEqual(meta["content_revision"], "2026-09-08-death-game-over")

    def test_client_keeps_hybrid_scenarios_selectable(self):
        source = Path("client/app.js").read_text(encoding="utf-8")
        self.assertNotIn('!scenario.filename.endsWith("_hybrid.json")', source)
        self.assertIn('s.filename === "dragon_rpg_hybrid.json"', source)
        self.assertIn('return `${title}（Hybrid）`', source)

    def test_client_has_dialogue_pair_attributes_and_defeat_surfaces(self):
        html = Path("client/index.html").read_text(encoding="utf-8")
        css = Path("client/styles.css").read_text(encoding="utf-8")
        source = Path("client/app.js").read_text(encoding="utf-8")

        for element_id in (
            "locationPortraits", "playerPortrait", "npcPortrait", "characterAttributes",
            "combatPlayerImage", "endingOverlay",
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn(".combat-terminal .combat-command-deck", css)
        self.assertIn("function renderScenePortraits", source)
        self.assertIn("function renderAbilityTags", source)

    def test_client_has_precombat_intro_surface(self):
        html = Path("client/index.html").read_text(encoding="utf-8")
        css = Path("client/styles.css").read_text(encoding="utf-8")
        source = Path("client/app.js").read_text(encoding="utf-8")

        for element_id in ("combatIntro", "combatIntroText", "combatIntroContinue"):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn(".combat-intro", css)
        self.assertIn("function renderCombatIntro", source)

    def test_portrait_staging_uses_equal_visual_height_and_count_aware_ensemble_sizes(self):
        css = Path("client/styles.css").read_text(encoding="utf-8")
        source = Path("client/app.js").read_text(encoding="utf-8")

        self.assertIn(".dialogue-mode .gal-sprite", css)
        self.assertIn("height: 84vh", css)
        self.assertIn('.location-portrait-group[data-count="1"]', css)
        self.assertIn('.location-portrait-group[data-count="2"]', css)
        self.assertIn("els.locationPortraits.dataset.count = String(locationNpcs.length)", source)

    def test_town_catalog_and_companions_are_complete(self):
        for filename in SCENARIO_FILES:
            with self.subTest(filename=filename):
                pack = self.load_raw(filename)
                locations = records(pack, "locations")
                items = records(pack, "items")
                companions = records(pack, "companions")

                magic_actions = {action["id"]: action for action in iter_actions(locations["magic_shop"]["actions"])}
                self.assertEqual(
                    [child["id"] for child in magic_actions["blue_mage_shop"]["children"]],
                    ["buy_earth_staff", "buy_healing_scroll", "buy_fireball_scroll"],
                )
                self.assertEqual(magic_actions["buy_earth_staff"]["requirements"]["gold_gte"], 40)
                self.assertEqual(magic_actions["ask_blue_mage_rumor"]["roll"]["dc"], 14)
                self.assertIn("critical_failure", magic_actions["ask_blue_mage_rumor"]["silent_outcomes"])

                item_actions = {action["id"]: action for action in iter_actions(locations["item_shop"]["actions"])}
                herb_actions = [action_id for action_id in item_actions if action_id.startswith("buy_sarah_herb_")]
                self.assertEqual(len(herb_actions), 3)
                self.assertFalse(item_actions["borrow_fire_bat_dragon"]["critical_enabled"])

                self.assertEqual(items["earth_staff"]["combat"]["grants_skills"][0]["damage"], "1d10+int/2")
                self.assertTrue(items["earth_staff"]["combat"]["grants_skills"][0]["all_targets"])
                self.assertEqual(items["healing_scroll"]["combat"]["healing"], "30")
                self.assertEqual(items["fireball_scroll"]["combat"]["damage"], "1d6+5")
                self.assertEqual(items["poison_dart"]["combat"]["on_hit_status"]["damage"], "4")
                self.assertEqual(
                    items["activated_ice_charm"]["combat"]["basic_attack_followup"]["damage"],
                    "1d8+int/2",
                )
                self.assertEqual(companions["blue_robed_mage"]["round_start_effects"][0]["amount"], "8")
                self.assertEqual(companions["fire_bat_dragon"]["round_start_effects"][0]["damage"], "2d3")
                self.assertEqual(locations["item_shop"]["npc_ids"], ["sarah", "fire_bat_dragon"])
                forge_actions = {entry["id"]: entry for entry in locations["forge"]["actions"]}
                self.assertEqual(forge_actions["activate_ice_charm"]["hidden_for_character"], "hero")

    def test_visual_assets_are_wired_and_present(self):
        client_root = Path("client")
        for filename in SCENARIO_FILES:
            with self.subTest(filename=filename):
                pack = self.load_raw(filename)
                locations = records(pack, "locations")
                npcs = records(pack, "npcs")
                enemies = records(pack, "enemies")
                companions = records(pack, "companions")

                self.assertEqual(locations["forge"]["portrait_image"], "/static/images/npc_blacksmith.png")
                self.assertEqual(locations["inn"]["portrait_image"], "/static/images/npc_ian.png")
                self.assertEqual(locations["village_approach"]["background_image"], "/static/images/bg_burning_village.png")
                self.assertEqual(enemies["frost_dire_wolf"]["image"], "/static/images/enemy_frost_dire_wolf.png")
                self.assertEqual(companions["fire_bat_dragon"]["image"], "/static/images/companion_fire_bat_dragon.png")

                asset_urls = {
                    record[key]
                    for section, key in (
                        (pack.get("locations", []), "background_image"),
                        (pack.get("locations", []), "portrait_image"),
                        (pack.get("npcs", []), "image"),
                        (pack.get("enemies", []), "image"),
                        (pack.get("companions", []), "image"),
                    )
                    for record in section
                    if isinstance(record, dict) and record.get(key)
                }
                missing = [
                    url for url in sorted(asset_urls)
                    if not (client_root / url.removeprefix("/static/")).is_file()
                ]
                self.assertEqual(missing, [])

    def test_public_session_uses_enemy_portrait_during_combat(self):
        session = self.create_runtime_session()
        state.commit_world_position(session, location_id="dark_forest_loc")
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))

        public = state.public_session(session)

        self.assertEqual(public["active_portrait_image"], "/static/images/enemy_slime.png")

    def test_blue_mage_critical_results_and_pet_opt_out(self):
        critical = self.create_runtime_session()
        state.commit_world_position(critical, location_id="magic_shop")
        action = state.resolve_action(critical, action_id="ask_blue_mage_rumor")
        roll = state.roll_dice(critical, *state.action_dice_settings(action), client_rolls=[20])
        result = state.apply_action_result(critical, action, roll)
        self.assertEqual(result["outcome"], "critical_success")
        self.assertTrue(critical["flags"].get("heard_name_xanxus"))

        fumble = self.create_runtime_session()
        state.commit_world_position(fumble, location_id="magic_shop")
        action = state.resolve_action(fumble, action_id="ask_blue_mage_rumor")
        roll = state.roll_dice(fumble, *state.action_dice_settings(action), client_rolls=[1])
        result = state.apply_action_result(fumble, action, roll)
        self.assertEqual(result["outcome"], "critical_failure")
        self.assertTrue(app_module._should_skip_turn_narration(fumble, action, result, action["text"]))

        pet = self.create_runtime_session()
        state.commit_world_position(pet, location_id="item_shop")
        action = state.resolve_action(pet, action_id="borrow_fire_bat_dragon")
        roll = state.roll_dice(pet, *state.action_dice_settings(action), client_rolls=[1])
        result = state.apply_action_result(pet, action, roll)
        self.assertEqual(result["outcome"], "failure")
        self.assertTrue(pet["flags"].get("fire_bat_dragon_dislikes_player"))

    def test_runtime_keeps_companion_passive_data(self):
        session = self.create_runtime_session()
        state.commit_world_position(session, location_id="magic_shop")
        action = state.resolve_action(session, action_id="invite_blue_mage")
        state.apply_action_result(
            session,
            action,
            {"expression": "none", "rolls": [], "total": 0, "dc": 0},
        )
        self.assertEqual(session["companion"]["id"], "blue_robed_mage")
        self.assertEqual(session["companion"]["round_start_effects"][0]["amount"], "8")

    def test_alley_and_forest_routes_are_structured(self):
        for filename in SCENARIO_FILES:
            with self.subTest(filename=filename):
                pack = self.load_raw(filename)
                locations = records(pack, "locations")
                enemies = records(pack, "enemies")
                items = records(pack, "items")

                self.assertEqual(
                    [action["id"] for action in locations["alley"]["actions"]],
                    ["wait_for_night_in_alley", "return_castle_from_alley"],
                )
                self.assertEqual(enemies["zebok"]["hp"], -100)
                self.assertEqual(enemies["zebok"]["combat"]["life_rule"], "negative_undead")
                self.assertEqual(items["cursed_holy_staff"]["combat"]["extra_actions_per_round"], 1)
                self.assertEqual(items["cursed_dagger"]["combat"]["on_hit_status"]["damage"], "3")

                self.assertEqual(locations["slime_ambush_one"]["combat"]["enemy_ids"], ["slime"] * 3)
                self.assertEqual(locations["slime_ambush_two"]["combat"]["enemy_ids"], ["slime"] * 3)
                self.assertEqual(locations["goblin_fort_second_left"]["combat"]["enemy_ids"], ["war_hound"] * 5)
                self.assertEqual(
                    locations["goblin_fort_fourth"]["combat"]["enemy_ids"],
                    ["goblin_king", "goblin_archer", "goblin_archer"],
                )
                self.assertTrue(locations["goblin_fort_fourth"]["combat"]["auto_start"])
                self.assertEqual(enemies["goblin_king"]["rewards"]["gold"], 100)

    def test_ignored_lost_goblin_steals_gold_and_branches(self):
        wealthy = self.create_runtime_session()
        state.commit_world_position(wealthy, location_id="lost_goblin_crossroads")
        wealthy["character"]["gold"] = 50
        action = state.resolve_action(wealthy, action_id="ignore_lost_goblin")
        roll = state.roll_dice(wealthy, *state.action_dice_settings(action), client_rolls=[1])
        state.apply_action_result(wealthy, action, roll)
        self.assertEqual(wealthy["character"]["gold"], 20)
        self.assertEqual(state.current_location_id(wealthy), "elf_spring")

        poor = self.create_runtime_session()
        state.commit_world_position(poor, location_id="lost_goblin_crossroads")
        poor["character"]["gold"] = 20
        action = state.resolve_action(poor, action_id="ignore_lost_goblin")
        roll = state.roll_dice(poor, *state.action_dice_settings(action), client_rolls=[1])
        state.apply_action_result(poor, action, roll)
        self.assertEqual(poor["character"]["gold"], 0)
        self.assertTrue(state.ensure_combat_started(poor))
        self.assertEqual(poor["combat"]["enemies"][0]["template_id"], "goblin")

    def test_cross_location_combat_uses_source_prepared_turn(self):
        session = self.create_runtime_session()
        session["world_state"] = {"scene_id": "village", "location_id": "xanxus_confrontation"}
        action = state.resolve_action(session, action_id="bluff_xanxus")
        roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[10])

        result = state.apply_action_result(session, action, roll)
        prepared_turn = select_hybrid_prepared_turn(session, action["text"])

        self.assertEqual(result["source_location_id"], "xanxus_confrontation")
        self.assertEqual(state.current_location_id(session), "xanxus_battle")
        self.assertEqual(prepared_turn["id"], "xanxus_bluff_failed")
        self.assertIn("炎", prepared_turn["draft"]["gm_text"])

    def test_castle_departure_has_prepared_transition_for_both_outcomes(self):
        for rolls, expected_turn_id in (([18], "castle_departure_success"), ([1], "castle_departure_failure")):
            with self.subTest(expected_turn_id=expected_turn_id):
                session = self.create_runtime_session()
                session["world_state"] = {"scene_id": "start", "location_id": "castle"}
                action = state.resolve_action(session, action_id="go_dark_forest")
                roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=rolls)
                state.apply_action_result(session, action, roll)

                prepared_turn = select_hybrid_prepared_turn(session, action["text"])

                self.assertEqual(prepared_turn["id"], expected_turn_id)
                self.assertTrue(prepared_turn["draft"]["gm_text"].strip())

    def test_lost_goblin_and_xanxus_show_intro_before_combat_without_llm(self):
        cases = (
            ("dark_forest", "lost_goblin_crossroads", "ignore_lost_goblin", [10], "財布"),
            ("village", "xanxus_confrontation", "bluff_xanxus", [10], "Xanxus"),
        )
        for scene_id, location_id, action_id, rolls, expected_text in cases:
            with self.subTest(action_id=action_id):
                session = self.create_runtime_session()
                session["world_state"] = {"scene_id": scene_id, "location_id": location_id}
                action = state.resolve_action(session, action_id=action_id)
                with patch.object(app_module, "chat_completion") as completion, patch.object(state.random, "randint", side_effect=rolls):
                    result = app_module._run_turn(
                        session,
                        app_module.TurnRequest(
                            text=action["text"],
                            action_id=action_id,
                            client_dice={"rolls": rolls},
                        ),
                    )

                completion.assert_not_called()
                self.assertTrue(result["in_combat"])
                self.assertIn(expected_text, result["combat"]["intro_text"])
                self.assertEqual(result["messages"][-1]["text"], result["combat"]["intro_text"])

    @patch.object(state.random, "randint", return_value=3)
    def test_lost_goblin_robbery_uses_combat_specific_text_when_gold_runs_out(self, _roll):
        session = self.create_runtime_session()
        session["world_state"] = {"scene_id": "dark_forest", "location_id": "lost_goblin_crossroads"}
        session["character"]["gold"] = 20
        action = state.resolve_action(session, action_id="ignore_lost_goblin")

        with patch.object(app_module, "chat_completion") as completion:
            result = app_module._run_turn(
                session,
                app_module.TurnRequest(
                    text=action["text"],
                    action_id=action["id"],
                    client_dice={"rolls": [1]},
                ),
            )

        completion.assert_not_called()
        self.assertTrue(result["in_combat"])
        self.assertIn("口封じ", result["combat"]["intro_text"])
        self.assertNotIn("泉へ向かって", result["combat"]["intro_text"])

    def test_combat_entries_have_player_visible_introductions(self):
        required_action_ids = {
            "betray_cursed_merchant",
            "attack_slime",
            "ignore_lost_goblin",
            "rest_at_elf_spring",
            "continue_from_elf_spring",
            "fight_fort_first_guard",
            "fight_fort_second_guards",
            "fort_second_bypass",
            "explore_fort_left",
            "fight_hobgoblin",
            "give_correct_password",
            "admit_no_password",
            "steal_lost_goblin_box",
            "approach_burning_village_carefully",
            "enter_burning_village_directly",
            "bluff_xanxus",
            "ambush_xanxus",
            "flee_from_xanxus",
            "refuse_xanxus_with_rescue",
            "fight_ice_elemental",
            "bypass_ice_elemental",
        }
        for filename in SCENARIO_FILES:
            with self.subTest(filename=filename):
                pack = self.load_raw(filename)
                prepared_actions = {
                    str(turn.get("action_id") or "")
                    for location in pack.get("locations", [])
                    for turn in ((location.get("hybrid") or {}).get("prepared_turns") or [])
                    if str(((turn.get("draft") or {}).get("gm_text") or "")).strip()
                }
                self.assertEqual(required_action_ids - prepared_actions, set())

                locations = records(pack, "locations")
                self.assertIn("victory", locations["slime_ambush_one"]["combat"]["result_texts"])
                self.assertIn("victory", locations["slime_ambush_two"]["combat"]["result_texts"])
                self.assertIn("victory", locations["goblin_fort_third_guards"]["combat"]["result_texts"])


    def test_slime_ambush_locations_belong_to_dark_forest(self):
        for filename in SCENARIO_FILES:
            with self.subTest(filename=filename):
                pack = self.load_raw(filename)
                locations = records(pack, "locations")
                forest_location_ids = set(records(pack, "scenes")["dark_forest"]["location_ids"])
                for location_id in ("slime_ambush_one", "slime_ambush_two", "slime_king_battle"):
                    self.assertEqual(locations[location_id]["scene_id"], "dark_forest")
                    self.assertIn(location_id, forest_location_ids)


    def test_burning_village_replaces_old_hybrid_scene(self):
        for filename in SCENARIO_FILES:
            with self.subTest(filename=filename):
                pack = self.load_raw(filename)
                locations = records(pack, "locations")
                enemies = records(pack, "enemies")
                characters = records(pack, "characters")
                scene = records(pack, "scenes")["village"]

                self.assertNotIn("village_shop", locations)
                self.assertNotIn("hybrid", scene)
                self.assertEqual(locations["xanxus_battle"]["combat"]["enemy_ids"], ["xanxus"])
                self.assertEqual(enemies["xanxus"]["hp"], 999)
                self.assertEqual(enemies["xanxus"]["attributes"]["int"], 50)
                self.assertEqual(enemies["xanxus"]["resistances"]["fire"], 0.0)
                self.assertEqual(enemies["xanxus"]["resistances"]["dark"], 0.0)
                self.assertEqual(characters["warlock"]["hp"], 100)
                self.assertEqual(characters["warlock"]["attributes"]["int"], 100)
                self.assertEqual(len(characters["warlock"]["skills"]), 3)
                self.assertFalse(characters["warlock"]["selectable"])

    def test_blue_mage_leaves_and_village_extreme_rolls_branch(self):
        session = self.create_runtime_session()
        state.commit_world_position(session, location_id="magic_shop")
        invite = state.resolve_action(session, action_id="invite_blue_mage")
        state.apply_action_result(session, invite, {"expression": "none", "rolls": [], "total": 0, "dc": 0})
        self.assertEqual(session["companion"]["id"], "blue_robed_mage")

        session["world_state"] = {"scene_id": "dark_forest", "location_id": "forest_exit"}
        leave = state.resolve_action(session, action_id="leave_forest_for_village")
        state.apply_action_result(session, leave, {"expression": "none", "rolls": [], "total": 0, "dc": 0})
        self.assertIsNone(session["companion"])
        self.assertTrue(session["flags"].get("warlock_disappeared_at_village"))
        self.assertEqual(state.current_location_id(session), "village_approach")
        self.assertEqual(session["character"]["background_image"], "/static/images/bg_burning_village.png")
        self.assertTrue(Path("client/images/bg_burning_village.png").is_file())

        critical = self.create_runtime_session()
        critical["world_state"] = {"scene_id": "village", "location_id": "village_approach"}
        action = state.resolve_action(critical, action_id="approach_burning_village_carefully")
        roll = state.roll_dice(critical, *state.action_dice_settings(action), client_rolls=[20])
        result = state.apply_action_result(critical, action, roll)
        self.assertEqual(result["outcome"], "critical_success")
        self.assertEqual(state.current_location_id(critical), "village_frozen_clue")
        self.assertFalse(critical.get("combat_start_requested", False))

        fumble = self.create_runtime_session()
        fumble["world_state"] = {"scene_id": "village", "location_id": "village_approach"}
        before_hp = fumble["character"]["hp"]
        action = state.resolve_action(fumble, action_id="approach_burning_village_carefully")
        roll = state.roll_dice(fumble, *state.action_dice_settings(action), client_rolls=[1])
        result = state.apply_action_result(fumble, action, roll)
        self.assertEqual(result["outcome"], "critical_failure")
        self.assertEqual(fumble["character"]["hp"], max(0, before_hp - 10))
        self.assertEqual(state.current_location_id(fumble), "village_fire_elemental")
        self.assertTrue(state.ensure_combat_started(fumble))
        self.assertEqual(fumble["combat"]["enemies"][0]["template_id"], "fire_elemental")

    def test_xanxus_checks_are_impossible_and_rescue_choice_is_exclusive(self):
        session = self.create_runtime_session()
        session["world_state"] = {"scene_id": "village", "location_id": "xanxus_confrontation"}
        action = state.resolve_action(session, action_id="bluff_xanxus")
        roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[20])
        result = state.apply_action_result(session, action, roll)
        self.assertEqual(result["outcome"], "failure")
        self.assertEqual(state.current_location_id(session), "xanxus_battle")
        self.assertTrue(state.ensure_combat_started(session))

        no_rescue = self.create_runtime_session()
        no_rescue["world_state"] = {"scene_id": "village", "location_id": "xanxus_ultimatum"}
        no_rescue["choices"] = state.fallback_choices_for_session(no_rescue)
        visible = {choice.get("action_id") for choice in state.public_session(no_rescue)["choices"]}
        self.assertIn("refuse_xanxus_without_rescue", visible)
        self.assertNotIn("refuse_xanxus_with_rescue", visible)

        rescued = self.create_runtime_session()
        rescued["flags"]["warlock_rescue_available"] = True
        rescued["world_state"] = {"scene_id": "village", "location_id": "xanxus_ultimatum"}
        rescued["choices"] = state.fallback_choices_for_session(rescued)
        visible = {choice.get("action_id") for choice in state.public_session(rescued)["choices"]}
        self.assertIn("refuse_xanxus_with_rescue", visible)
        self.assertNotIn("refuse_xanxus_without_rescue", visible)

    def test_fire_seed_is_passive_and_non_removable(self):
        session = self.create_runtime_session()
        state.apply_state_delta(session, {"inventory_add": [{"name": "火種", "quantity": 1}]})
        seed = next(item for item in session["character"]["inventory"] if item.get("name") == "火種")
        self.assertEqual(seed["combat"]["damage_taken_multipliers"]["fire"], 0.5)
        self.assertEqual(seed["combat"]["damage_taken_multipliers"]["ice"], 2.0)
        state.apply_state_delta(session, {"inventory_remove": [{"name": "火種", "quantity": 1}]})
        self.assertIn("火種", {item.get("name") for item in session["character"]["inventory"]})

    def test_warlock_battle_temporarily_replaces_and_restores_player(self):
        session = self.create_runtime_session()
        original_name = session["character"]["name"]
        original_hp = session["character"]["hp"]
        session["world_state"] = {"scene_id": "village", "location_id": "warlock_rescue_battle"}
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))
        self.assertEqual(session["character"]["character_id"], "warlock")
        self.assertEqual(session["character"]["attributes"]["int"], 100)
        action_ids = {entry["id"] for entry in combat.combat_actions(session) if entry["type"] == "skill"}
        self.assertEqual(action_ids, {"element_counter", "element_switch", "element_prayer"})

        combat._finish_combat(session, "victory", "test victory")
        delta = combat.consume_combat_state_delta(session)
        state.apply_state_delta(session, delta, allow_world_transition=True)
        combat.clear_combat_after_resolution(session)
        self.assertEqual(session["character"]["name"], original_name)
        self.assertEqual(session["character"]["hp"], original_hp)
        self.assertEqual(state.current_location_id(session), "village_frozen_clue")

    def test_xanxus_field_rebirth_and_warlock_element_skills(self):
        field_session = self.create_runtime_session()
        field_session["world_state"] = {"scene_id": "village", "location_id": "xanxus_battle"}
        field_session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(field_session))
        field_session["character"]["hp"] = 100
        field_session["character"]["max_hp"] = 100
        enemy = field_session["combat"]["enemies"][0]
        enemy["skills"] = [next(skill for skill in enemy["skills"] if skill["id"] == "flame_vortex")]
        combat.perform_combat_action(field_session, "defend", rng=random.Random(2))
        self.assertEqual(len(field_session["combat"].get("fields") or []), 1)
        self.assertEqual(field_session["character"]["hp"], 88)

        warlock = self.create_runtime_session()
        warlock["world_state"] = {"scene_id": "village", "location_id": "warlock_rescue_battle"}
        warlock["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(warlock))
        enemy = warlock["combat"]["enemies"][0]
        enemy["hp"] = 210
        combat._player_skill(warlock, "element_counter", enemy["id"], random.Random(3))
        self.assertIn("rebirth_in_fire", enemy.get("auto_triggered") or [])
        self.assertGreater(enemy["hp"], 0)

        combat._player_skill(warlock, "element_switch", enemy["id"], random.Random(4))
        self.assertIn("fire", warlock["character"].get("combat_immunities") or [])
        self.assertEqual(combat._resistance_multiplier(warlock["character"], "fire"), 0.0)

        enemy["hp"] = enemy["max_hp"]
        enemy["auto_triggered"] = ["rebirth_in_fire"]
        before_logs = len(warlock["combat"]["log"])
        combat._player_skill(warlock, "element_prayer", enemy["id"], random.Random(5))
        attack_logs = [entry for entry in warlock["combat"]["log"][before_logs:] if entry.get("kind") == "damage"]
        self.assertGreaterEqual(len(attack_logs), 20)
        self.assertLess(enemy["hp"], enemy["max_hp"])

    def test_prepared_boss_result_skips_llm(self):
        session = self.create_runtime_session()
        session["world_state"] = {"scene_id": "village", "location_id": "frost_wolf_battle"}
        self.assertTrue(combat.ensure_combat_started(session))
        combat._finish_combat(session, "victory", "prepared victory")
        delta = combat.consume_combat_state_delta(session)
        state.apply_state_delta(session, delta, allow_world_transition=True)

        with patch.object(app_module, "chat_completion") as completion:
            result = app_module._run_combat_resolution(session)

        completion.assert_not_called()
        self.assertEqual(state.current_location_id(session), "ian_ice_katana_aftermath")
        self.assertIn("氷の太刀", result["messages"][-1]["text"])

    def test_prepared_turn_is_used_when_llm_is_unavailable(self):
        session = self.create_runtime_session()
        state.commit_world_position(session, location_id="magic_shop")
        state.save_session(session)

        with (
            patch.object(app_module, "load_config", return_value={"debug_llm": False, "demo_fallback_on_error": True}),
            patch.object(app_module, "chat_completion", side_effect=app_module.LLMClientError("offline")),
        ):
            public = app_module._run_turn(
                session,
                app_module.TurnRequest(text="パーティーへ招く", action_id="invite_blue_mage"),
            )

        self.assertEqual(
            public["messages"][-1]["text"],
            "魔法使いは背の杖を確かめ、静かに頷いた。「しばらく同行しましょう。傷の手当ては任せてください」",
        )
        self.assertEqual(public["companion"]["id"], "blue_robed_mage")

    def test_first_slime_result_introduces_stolen_box_without_contradiction(self):
        pack = self.load_raw()
        dark_forest = records(pack, "locations")["dark_forest_loc"]
        victory_text = dark_forest["combat"]["result_texts"]["victory"]

        self.assertIn("箱を盗まれ", victory_text)
        self.assertNotIn("箱を抱えて", victory_text)

    def test_location_portraits_switch_from_ensemble_to_dialogue_pair(self):
        session = self.create_runtime_session("mage")
        state.commit_world_position(session, location_id="inn")

        arrival = state.public_session(session)
        self.assertEqual(
            [npc["id"] for npc in arrival["location_npc_portraits"]],
            ["ian", "robin"],
        )
        self.assertFalse(arrival["dialogue_active"])
        self.assertEqual(arrival["player_portrait_image"], "/static/images/char_mage_v2.png")

        session["last_action_result"] = {"action_id": "ask_robin_rumor", "outcome": "success"}
        dialogue = state.public_session(session)
        self.assertTrue(dialogue["dialogue_active"])
        self.assertEqual(dialogue["dialogue_portrait_image"], "/static/images/npc_robin.png")

    def test_selectable_characters_use_refreshed_rgba_portraits(self):
        pack = self.load_raw()
        expected = {
            "hero": "/static/images/char_male_hero_v2.png",
            "cleric": "/static/images/char_cleric_v2.png",
            "mage": "/static/images/char_mage_v2.png",
            "thief": "/static/images/char_thief_v2.png",
        }
        characters = records(pack, "characters")
        for character_id, image in expected.items():
            self.assertEqual(characters[character_id]["image"], image)
            png = Path("client") / image.removeprefix("/static/")
            self.assertEqual(png.read_bytes()[25], 6, f"{png} must be RGBA")
        self.assertEqual(characters["hero"]["image_female"], "/static/images/char_female_hero_v2.png")
        for image in (
            "/static/images/char_female_hero_v2.png",
            "/static/images/npc_ian_serious.png",
        ):
            png = Path("client") / image.removeprefix("/static/")
            self.assertEqual(png.read_bytes()[25], 6, f"{png} must be RGBA")

    def test_old_save_portrait_paths_migrate_to_refreshed_art(self):
        session = self.create_runtime_session("thief")
        session["character"]["character_image"] = "/static/images/char_thief.png"
        state.save_session(session)

        loaded = state.load_session(session["id"])

        self.assertEqual(loaded["character"]["character_image"], "/static/images/char_thief_v2.png")

    def test_ian_uses_serious_variant_only_at_ice_katana_aftermath(self):
        session = self.create_runtime_session()
        state.commit_world_position(session, location_id="inn")
        inn = state.public_session(session)
        self.assertEqual(inn["location_npc_portraits"][0]["image"], "/static/images/npc_ian.png")

        state.ensure_world_state(session).update({
            "scene_id": "village",
            "location_id": "ian_ice_katana_aftermath",
        })
        aftermath = state.public_session(session)
        self.assertEqual(
            aftermath["location_npc_portraits"][0]["image"],
            "/static/images/npc_ian_serious.png",
        )
        session["last_action_result"] = {"action_id": "accept_ian_request", "outcome": "neutral"}
        dialogue = state.public_session(session)
        self.assertEqual(dialogue["dialogue_portrait_image"], "/static/images/npc_ian_serious.png")

    def test_explicit_retry_can_start_combat_after_a_defeat_lock(self):
        session = self.create_runtime_session()
        state.commit_world_position(session, location_id="goblin_fort_first_second")
        session["combat_blocked_location"] = "goblin_fort_first_second"
        session["combat_start_requested"] = True

        self.assertTrue(combat.ensure_combat_started(session))
        self.assertEqual(session["combat"]["status"], "active")
        self.assertNotIn("combat_blocked_location", session)

    def test_non_hero_can_activate_ice_charm_for_basic_attack_followup(self):
        session = self.create_runtime_session("mage")
        if "氷の護符" not in {item.get("name") for item in session["character"]["inventory"]}:
            state.apply_state_delta(session, {"inventory_add": [{"name": "氷の護符", "quantity": 1}]})
        state.commit_world_position(session, location_id="forge")

        forge_action = state.resolve_action(session, action_id="activate_ice_charm")
        self.assertIsNotNone(forge_action)
        state.apply_action_result(
            session,
            forge_action,
            {"expression": "none", "rolls": [], "total": 0, "dc": 0},
        )
        item_names = {item.get("name") for item in session["character"]["inventory"]}
        self.assertNotIn("氷の護符", item_names)
        self.assertIn("氷の護符(活性化済)", item_names)
        self.assertIn("氷の護符(活性化済)", session["character"]["equipment"])

        state.commit_world_position(session, location_id="goblin_fort")
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))
        basic_action = next(entry for entry in combat.combat_actions(session) if entry["id"] == "basic_attack")
        self.assertEqual(basic_action["followups"][0]["damage"], "1d8+int/2")
        target = session["combat"]["enemies"][0]
        combat._player_attack(session, target["id"], random.Random(7))
        self.assertTrue(
            any("氷の護符の追撃" in entry.get("text", "") for entry in session["combat"]["log"])
        )

    def test_combat_actions_expose_structured_effect_details(self):
        session = self.create_runtime_session("mage")
        state.commit_world_position(session, location_id="goblin_fort")
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))

        actions = {entry["id"]: entry for entry in combat.combat_actions(session)}
        self.assertIn("damage", actions["basic_attack"])
        self.assertIn("accuracy", actions["basic_attack"])
        self.assertEqual(actions["fireball"]["damage"], "1d6+int/2+3")
        self.assertEqual(actions["fireball"]["element"], "fire")


if __name__ == "__main__":
    unittest.main()
