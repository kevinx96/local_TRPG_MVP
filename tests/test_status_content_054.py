from __future__ import annotations

import json
import math
import random
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "tests"))

from fastapi import HTTPException
from host import app, combat, difficulty, free_actions, state, status_effects
from host.shops import trade
from scripts.balance import checkpoints
from scripts.scenario import normal_tuning_052, status_content_054 as content
from test_combat_mechanics_v2 import session as arena
from combat_v2_golden import stable


def index(records):
    return {record["id"]: record for record in records}


def ability_at(enemy, path):
    if path == "combat.basic_attack":
        return enemy["combat"]["basic_attack"]
    identifier = path.split("@id=", 1)[1]
    return next((skill for skill in enemy.get("skills", []) if skill["id"] == identifier), None)


class StatusContent054Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.normal = difficulty.apply_difficulty(cls.base, "normal")
        cls.baby = difficulty.apply_difficulty(cls.base, "baby")

    def session(self, character="hero", location="goblin_fort_second_choice"):
        value = checkpoints.fresh_session(deepcopy(self.normal), character, "normal", effective=True)
        value["world_state"] = {"scene_id": index(value["scenario_pack"]["locations"])[location]["scene_id"],
                                "location_id": location}
        value["character"].update(hp=100, max_hp=100, statuses=[], gold=1000)
        return value

    def test_baby_active_content_matches_except_reviewed_shared_changes(self):
        frozen = json.loads((ROOT / "host/prompt/processed/difficulty/baby_numeric_freeze.json").read_text(encoding="utf-8"))
        def active(pack):
            pack = difficulty.apply_difficulty(pack, "baby")
            pack.pop("status_defs", None)
            pack.pop("difficulty_overlays", None)
            pack["meta"].pop("content_revision", None)
            next(item for item in pack["items"] if item["id"] == "poison_dart").pop("description", None)
            return json.dumps(pack, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            raw = json.loads((ROOT / "host/prompt/processed" / name).read_text(encoding="utf-8"))
            original = json.loads(subprocess.check_output(
                ["git", "show", f"HEAD:host/prompt/processed/{name}"], cwd=ROOT, encoding="utf-8"))
            old_defs, new_defs = index(original["status_defs"]), index(raw["status_defs"])
            self.assertEqual(set(new_defs) - set(old_defs), {"haze"} if "haze" not in old_defs else set())
            for sid in ("poison", "paralysis", "weaken", "blind"):
                old_defs[sid]["tags"] = [sid, "debuff"]
            for sid, definition in old_defs.items():
                self.assertEqual(new_defs[sid], definition)
            self.assertEqual(active(raw), active(original), name)
            self.assertEqual(difficulty.numeric_snapshot(difficulty.apply_difficulty(raw, "baby")), frozen[name])

    def test_all_enemy_placements_boss_limits_and_explicit_kind(self):
        normal, baby = index(self.normal["enemies"]), index(self.baby["enemies"])
        for eid, path, sid, chance, stacks, duration in content.STATUS_ATTACKS:
            ability = ability_at(normal[eid], path)
            self.assertEqual(ability["on_hit_status"], content._status(sid, chance, stacks, duration))
            old = ability_at(baby[eid], path)
            self.assertFalse(old and "damage" not in old.get("on_hit_status", {}) and old.get("on_hit_status", {}).get("id") == sid)
            if sid == "stun":
                self.assertTrue(ability.get("telegraph") or ability.get("damage_max_hp_ratio"))
        for row in content.PERIODIC_ATTACKS:
            skill = ability_at(normal[row[0]], "skills.@id=" + row[1])
            self.assertEqual(skill["kind"], "attack")
            self.assertEqual(combat._ability_kind({**skill, "description": "防御と回復"}), "attack")
            self.assertIsNone(ability_at(baby[row[0]], "skills.@id=" + row[1]))
        prayer = index(self.normal["items"])["purifying_bell"]["combat"]["grants_skills"][0]
        self.assertEqual(prayer["kind"], "cleanse")
        bosses = {eid for loc in self.normal["locations"] if loc.get("combat", {}).get("encounter_class") == "boss"
                  for eid in loc["combat"].get("enemy_ids", [])}
        for eid in bosses:
            skills = [skill for skill in normal[eid].get("skills", []) if skill.get("on_hit_status")]
            self.assertLessEqual(len(skills), 1, eid)
            self.assertFalse(any(skill["on_hit_status"]["id"] == "stun" for skill in skills), eid)

    def test_200_seeded_attacks_per_enemy_status_and_baby_zero_v2(self):
        normal, baby = index(self.normal["enemies"]), index(self.baby["enemies"])
        rows = [(eid, path, sid, chance) for eid, path, sid, chance, *_ in content.STATUS_ATTACKS]
        rows += [(row[0], "skills.@id=" + row[1], row[3], 100) for row in content.PERIODIC_ATTACKS]
        for mode, catalog in (("normal", normal), ("baby", baby)):
            for eid, path, sid, chance in rows:
                with self.subTest(mode=mode, enemy=eid, path=path):
                    ability = ability_at(catalog[eid], path)
                    if ability is None:
                        continue
                    value = arena(mode)
                    value["scenario_pack"]["status_defs"] = deepcopy(self.normal["status_defs"])
                    enemy = value["combat"]["enemies"][0]
                    enemy.update(deepcopy(catalog[eid]))
                    enemy.update(id=eid + ":1", hp=100000, max_hp=100000)
                    value["combat"]["enemies"] = [enemy]
                    value["character"].update(hp=10000, max_hp=10000, inventory=[], equipment=[])
                    value["character"]["combat"]["defense"] = 0
                    value["character"]["attributes"]["dex"] = 0
                    value["character"]["resistances"] = {}
                    rng, landed, applied = random.Random(20261023), 0, 0
                    for turn in range(1, 201):
                        value["combat"].update(round=turn, log=[])
                        value["character"].update(hp=10000, statuses=[])
                        combat._execute_enemy_ability(value, enemy, deepcopy(ability), rng)
                        damage = [log for log in value["combat"]["log"] if log["kind"] == "damage"]
                        if any(log["data"]["damage"] > 0 for log in damage) or (
                                ability.get("status_on_hit") and not any(log["kind"] == "miss" for log in value["combat"]["log"])):
                            landed += 1
                        applied += any(status_effects.modern(status) and status["id"] == sid
                                       for status in value["character"].get("statuses", []))
                    if mode == "baby":
                        self.assertEqual(applied, 0)
                    else:
                        self.assertGreater(applied, 0)
                        expected = chance / 100
                        tolerance = max(.10, 4 * math.sqrt(expected * (1 - expected) / max(1, landed)))
                        self.assertAlmostEqual(applied / landed, expected, delta=tolerance)

    def test_g2_periodic_only_falls_back_and_coexists_with_052b(self):
        for row in content.PERIODIC_ATTACKS:
            value = arena()
            value["scenario_pack"]["combat_rules"]["elite_percentage_round_cap"] = .30
            enemy = value["combat"]["enemies"][0]
            source = deepcopy(index(self.normal["enemies"])[row[0]])
            enemy.update(source)
            periodic = next(skill for skill in enemy["skills"] if skill["id"] == row[1])
            enemy["skills"] = [periodic]
            for turn in range(1, 10):
                value["combat"]["round"] = turn
                selected = combat._choose_enemy_ability(enemy, value, random.Random(turn))
                self.assertEqual(selected.get("id") == row[1], turn % 3 == 0)
            enemy["skills"] = source["skills"]
            value["scenario_pack"]["combat_rules"]["elite_percentage_round_cap"] = .30
            for turn in (3, 6, 9):
                value["combat"]["round"] = turn
                self.assertEqual(combat._choose_enemy_ability(enemy, value, random.Random(turn))["id"], row[1])

    def test_g1_accepts_v2_and_rejects_legacy_unknown_and_invalid_numbers(self):
        addresses = (("enemies", "heat_lizard", "combat.basic_attack.on_hit_status"),
                     ("enemies", "lava_drake", "skills.@id=lava_breath.on_hit_status"),
                     ("items", "poison_dart", "combat.on_hit_status"))
        invalid = ({}, {"id": "missing"}, {"id": []}, {"id": "burn", "damage": "1"},
                   {"id": "burn", "remaining_rounds": 2}, {"id": "burn", "target": "self"},
                   *({"id": "burn", field: value} for field, values in (
                       ("chance", (0, 101, True, 50.5)), ("stacks", (0, 4, True, 1.5)),
                       ("duration", (0, 4, True, 1.5))) for value in values))
        for entity, eid, path in addresses:
            for spec in invalid:
                pack = deepcopy(self.base)
                pack["difficulty_overlays"]["normal"] = [{"entity": entity, "id": eid, "path": path, "set": spec}]
                with self.subTest(entity=entity, spec=spec), self.assertRaises(ValueError):
                    difficulty.validate_difficulty(pack)
            for spec in ({"id": "burn"}, {"id": "poison", "chance": 1, "stacks": 3, "duration": 3, "target": "target"}):
                pack = deepcopy(self.base)
                pack["difficulty_overlays"]["normal"] = [{"entity": entity, "id": eid, "path": path, "set": spec}]
                difficulty.validate_difficulty(pack)
            for reverse in (False, True):
                pack = deepcopy(self.base)
                entries = [{"entity": entity, "id": eid, "path": path, "set": {"id": "burn"}},
                           {"entity": entity, "id": eid, "path": path + ".damage", "set": "2"}]
                pack["difficulty_overlays"]["normal"] = entries[::-1] if reverse else entries
                with self.assertRaises(ValueError):
                    difficulty.validate_difficulty(pack)

    def test_undead_only_poison_immunity_and_validation(self):
        normal, baby = index(self.normal["enemies"]), index(self.baby["enemies"])
        for eid in content.UNDEAD:
            self.assertIn("poison", normal[eid]["status_immunity"])
            self.assertNotIn("poison", baby[eid].get("status_immunity", []))
            value = arena()
            enemy = value["combat"]["enemies"][0]
            enemy.update(normal[eid])
            self.assertFalse(status_effects.apply(value, enemy, "poison", value["character"], random.Random(1)))
        for eid in ("fire_elemental", "ice_elemental", "ruby_golem", "prism_tree"):
            self.assertNotIn("poison", normal[eid].get("status_immunity", []))
        for bad in ("poison", ["missing"], ["poison", "poison"], [1]):
            pack = deepcopy(self.base)
            pack["difficulty_overlays"]["normal"] = [{"entity": "enemies", "id": "ghoul", "path": "status_immunity", "set": bad}]
            with self.assertRaises(ValueError):
                difficulty.validate_difficulty(pack)

    def test_cleanse_tags_and_two_countermeasures_for_each_status(self):
        items = index(self.normal["items"])
        expected = {"antidote_herb": {"poison"}, "burn_salve": {"burn"},
                    "smelling_salts": {"paralysis", "weaken", "blind"},
                    "panacea": {"poison", "burn", "paralysis", "weaken", "blind", "suffocation"}}
        for iid, removed in expected.items():
            value = arena()
            value["scenario_pack"]["status_defs"] = deepcopy(self.normal["status_defs"])
            actor = value["character"]
            for sid in ("poison", "burn", "paralysis", "weaken", "blind", "suffocation", "stun", "haze"):
                status_effects.apply(value, actor, sid, actor, random.Random(1))
            before = {status["id"] for status in actor["statuses"]}
            status_effects.cleanse(value, actor, items[iid]["combat"]["cleanse"])
            self.assertEqual(before - {status["id"] for status in actor["statuses"]}, removed)
        for sid in ("poison", "burn", "paralysis", "weaken", "blind", "suffocation"):
            tags = set(index(self.normal["status_defs"])[sid]["tags"])
            counters = [iid for iid, item in items.items() if tags.intersection(item.get("combat", {}).get("cleanse", {}).get("tags", []))]
            counters += ["purify_prayer"]
            self.assertGreaterEqual(len(counters), 2, sid)
        self.assertIn("blinding_powder", items)
        self.assertIn("haze_ball", items)

    def test_powder_zero_damage_oil_fire_cap_and_haze_evade_cap(self):
        items = index(self.normal["items"])
        for category in ("trash", "elite", "boss"):
            value = arena(category=category)
            value["scenario_pack"]["status_defs"] = deepcopy(self.normal["status_defs"])
            enemy, actor = value["combat"]["enemies"][0], value["character"]
            enemy.update(hp=20, max_hp=20)
            with patch.object(combat, "attack_chance", return_value=100):
                combat._resolve_attack(value, actor, enemy, items["blinding_powder"]["combat"], "player", random.Random(1))
                self.assertEqual(enemy["hp"], 20)
                blind = next(status for status in enemy["statuses"] if status["id"] == "blind")
                self.assertEqual(blind["modifiers"]["accuracy_penalty"], 20 if category == "boss" else 30)
                combat._resolve_attack(value, actor, enemy, items["oil_flask"]["combat"], "player", random.Random(1))
            before = enemy["hp"]
            status_effects.tick(value, enemy, random.Random(1))
            self.assertEqual(before - enemy["hp"], 1 if category in {"elite", "boss"} else 2)
            actor["attributes"]["dex"] = 100
            status_effects.apply(value, actor, {"id": "haze", "duration": 9}, actor, random.Random(1))
            actor["statuses"].append({"status_v2": True, "modifiers": {"evade_bonus": 50}})
            self.assertEqual(combat.actor_evade(value, actor), 40)
            self.assertEqual(actor["statuses"][0]["remaining_rounds"], 2)

    def test_g5_bell_all_classes_buy_equip_cost_cooldown_and_free_action(self):
        for cid in ("hero", "cleric", "mage", "thief"):
            value = self.session(cid, "magic_shop")
            trade(value, "magic_shop", "purifying_bell", 1)
            self.assertTrue(any(item.get("id") == "purifying_bell" for item in value["character"]["inventory"]))
        value = arena()
        value["scenario_pack"]["status_defs"] = deepcopy(self.normal["status_defs"])
        actor = value["character"]
        bell = deepcopy(index(self.normal["items"])["purifying_bell"])
        actor["inventory"] = [{**bell, "quantity": 1}]
        self.assertNotIn("purify_prayer", {a["id"] for a in combat.combat_actions(value)})
        actor["equipment"] = [bell["name"]]
        actor["mp"] = 10
        status_effects.apply(value, actor, "poison", value["combat"]["enemies"][0], random.Random(1))
        before = actor["mp"]
        combat.perform_combat_action(value, "skill", "purify_prayer", rng=random.Random(1))
        self.assertEqual(actor["mp"], before - 3)
        self.assertFalse(any(status["id"] == "poison" for status in actor["statuses"]))
        action = next(a for a in combat.combat_actions(value) if a["id"] == "purify_prayer")
        self.assertFalse(action["enabled"])
        with self.assertRaises(combat.CombatError):
            combat.perform_combat_action(value, "skill", "purify_prayer", rng=random.Random(1))
        combat.perform_combat_action(value, "defend", rng=random.Random(1))
        self.assertTrue(next(a for a in combat.combat_actions(value) if a["id"] == "purify_prayer")["enabled"])
        actor["mp"] = 0
        with self.assertRaises(combat.CombatError):
            combat.perform_combat_action(value, "skill", "purify_prayer", rng=random.Random(1))
        with patch.object(app, "load_session", return_value=value), patch.object(app, "save_session") as save:
            with self.assertRaises(HTTPException) as caught:
                app.api_combat_action("test", app.CombatActionRequest(action_type="skill", action_id="purify_prayer"))
            self.assertEqual(caught.exception.status_code, 409)
            save.assert_not_called()
        actor["mp"] = 10
        plan = {"kind": "combat", "action_id": "purify_prayer", "operation": "skill", "target_id": "",
                "item_id": "", "advance": False, "approach": "清めの祈り", "reply": ""}
        result = free_actions.adjudicate(value, plan)
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(value["character"]["mp"], 7)

    def test_g6_ruby_charm_applies_to_burn_ticks(self):
        for equipped, expected in ((False, 2), (True, 1)):
            value = arena()
            actor = value["character"]
            charm = deepcopy(index(self.normal["items"])["ruby_charm"])
            actor["inventory"] = [{**charm, "quantity": 1}]
            actor["equipment"] = [charm["name"]] if equipped else []
            status_effects.apply(value, actor, "burn", value["combat"]["enemies"][0], random.Random(1))
            status_effects.tick(value, actor, random.Random(1))
            self.assertEqual(100 - actor["hp"], expected)

    def test_hazards_dc_rewards_nonlethal_pending_status_and_advantages(self):
        for row in content.TRAPS:
            number, location, kind, skill, dc, ratio, sid, rewards, clue = row
            for success in (False, True):
                with self.subTest(number=number, success=success):
                    value = self.session(location=location)
                    value["flags"]["cleared_cave_crystal_corridor"] = True
                    action = state.resolve_action(value, action_id=f"hazard_054_{number:02d}")
                    self.assertEqual(action["hazard"], {"kind": kind, "warning": action["preview"]})
                    self.assertEqual((action["roll"]["skill"], action["roll"]["dc"]), (skill, dc))
                    value["character"]["hp"] = 1
                    roll = {"dc": dc, "success": success, "total": 20 if success else 1,
                            "critical_success": False, "critical_failure": False}
                    state.apply_action_result(value, action, roll)
                    self.assertGreaterEqual(value["character"]["hp"], 1)
                    for iid, count in rewards:
                        actual = sum(i.get("quantity", 1) for i in value["character"]["inventory"] if i.get("id") == iid)
                        if number in (7, 8) and not success:
                            self.assertEqual(actual, 0, (number, iid))
                        else:
                            self.assertGreaterEqual(actual, count)
                    if sid and not success:
                        status = next(s for s in value["character"]["statuses"] if s["id"] == sid)
                        value["world_state"] = {"scene_id": "forest_wolves", "location_id": "forest_wolves"}
                        value["combat_start_requested"] = True
                        combat.ensure_combat_started(value)
                        self.assertIn(status, value["character"]["statuses"])
                    if number == 7:
                        self.assertTrue(value["flags"]["passed_gorge_rockfall_path"])
                        self.assertFalse(value.get("combat_start_requested"))
                    if number == 8:
                        self.assertEqual(value["character"]["gold"], 1015 if success else 1000)
            for source in ("thief", "probe", "clue"):
                value = self.session("thief" if source == "thief" else "hero", location)
                value["flags"]["cleared_cave_crystal_corridor"] = True
                value["character"]["inventory"] = []
                if source == "probe":
                    value["character"]["inventory"] = [{"id": "trap_probe", "name": "探り棒", "quantity": 1}]
                elif source == "clue":
                    if "flag" in clue:
                        value["flags"][clue["flag"]] = True
                    else:
                        value["character"]["inventory"] = [{"id": "rusted_badge", "name": clue["has_item"], "quantity": 1}]
                action = state.resolve_action(value, action_id=f"hazard_054_{number:02d}")
                check = state.dice_check_info(value, action["roll"]["dice_type"], dc, roll=action["roll"])
                self.assertEqual(check["advantage"], "advantage", (number, source, check))

    def test_holy_water_branch_shared_once_and_clue_success_only(self):
        value = self.session(location="bone_field")
        value["character"]["inventory"] = [{"id": "holy_water", "name": "聖水", "quantity": 2}]
        action = state.resolve_action(value, action_id="hazard_054_05_holy_water")
        self.assertNotIn("roll", action)
        state.apply_action_result(value, action, {})
        self.assertEqual(next(i for i in value["character"]["inventory"] if i["id"] == "holy_water")["quantity"], 1)
        self.assertTrue(value["flags"]["hazard_054_05_done"])
        for success in (False, True):
            value = self.session()
            action = state.resolve_action(value, action_id="listen_fort_corridors")
            state.apply_action_result(value, action, {"dc": 10, "success": success, "total": 20 if success else 1})
            self.assertEqual(bool(value["flags"].get("fort_corridors_heard_054")), success)

    def test_normal_only_items_shops_hazards_and_cleric_spring_reward(self):
        new_ids = set(content.ITEM_TEXTS) - {"poison_dart"}
        self.assertTrue(new_ids <= index(self.normal["items"]).keys())
        self.assertFalse(new_ids & index(self.baby["items"]).keys())
        for location in self.baby["locations"]:
            self.assertFalse(any(a["id"].startswith("hazard_054_") for a in location.get("actions", [])))
        for shop in self.normal["shops"]:
            expected = content.SHOP_ITEMS.get(shop["id"], ())
            for iid, price, stock in expected:
                row = next(item for item in shop["items"] if item["item_id"] == iid)
                self.assertEqual((row["price"], row["stock"]), (price, stock))
                if iid == "purifying_bell":
                    self.assertNotIn("requirements", row)
        for cid in ("hero", "cleric", "mage", "thief"):
            value = self.session(cid, "elf_spring")
            state.apply_action_result(value, state.resolve_action(value, action_id="commune_spring"),
                                      {"dc": 10, "success": True, "total": 20})
            found = any(i.get("id") == "purifying_bell" for i in value["character"]["inventory"])
            self.assertEqual(found, cid == "cleric")

    def test_log_text_precedes_resolution_and_absence_leaves_log_and_rng_unchanged(self):
        row = content.PERIODIC_ATTACKS[0]
        skill = ability_at(index(self.normal["enemies"])[row[0]], "skills.@id=" + row[1])
        value = arena()
        enemy = value["combat"]["enemies"][0]
        before = len(value["combat"]["log"])
        combat._execute_enemy_ability(value, enemy, skill, random.Random(1))
        first = value["combat"]["log"][before]
        self.assertEqual(first["text"], skill["log_text"].replace("{enemy}", enemy["name"]))
        self.assertEqual(first["kind"], "status")
        base = {"id": "hit", "name": "攻撃", "kind": "attack", "damage": "1", "accuracy": 100}
        first, second = arena("baby"), arena("baby")
        a, b = random.Random(7), random.Random(7)
        combat._execute_enemy_ability(first, first["combat"]["enemies"][0], base, a)
        combat._execute_enemy_ability(second, second["combat"]["enemies"][0], {**base, "log_text": ""}, b)
        self.assertEqual(stable(first["combat"]["log"]), stable(second["combat"]["log"]))
        self.assertEqual(a.getstate(), b.getstate())

    def test_migration_pure_idempotent_and_preserves_052_numbers(self):
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads((ROOT / "host/prompt/processed" / name).read_text(encoding="utf-8"))
            before = deepcopy(pack)
            self.assertEqual(content.migrate(pack), pack)
            self.assertEqual(pack, before)
            self.assertEqual(normal_tuning_052.migrate(pack), pack)
            effective = difficulty.apply_difficulty(pack, "normal")
            self.assertEqual(effective["progression"]["exp_table"], normal_tuning_052.PROGRESSION["exp_table"])
            for eid, fields in normal_tuning_052.ENEMIES.items():
                for path, expected in fields.items():
                    expected = normal_tuning_052.BOSSES_052B.get(eid, {}).get(path, expected)
                    parent, key, _ = difficulty._destination(index(effective["enemies"])[eid], path)
                    self.assertEqual(parent[key], expected, (eid, path))

    def test_full_chain_from_head_and_second_application(self):
        from scripts.scenario import spring_postgame, combat_mechanics_v2, levels_skills_v2
        from scripts.scenario import holy_sword_049, mina_reborrow_055

        def chain(pack):
            result = deepcopy(pack)
            spring_postgame.apply(result)
            for module in (combat_mechanics_v2, levels_skills_v2, holy_sword_049,
                           mina_reborrow_055, normal_tuning_052, content, normal_tuning_052):
                result = module.migrate(result)
            return result

        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            original = json.loads(subprocess.check_output(
                ["git", "show", f"HEAD:host/prompt/processed/{name}"], cwd=ROOT, encoding="utf-8"))
            current = json.loads((ROOT / "host/prompt/processed" / name).read_text(encoding="utf-8"))
            self.assertEqual(chain(original), current)
            self.assertEqual(chain(current), current)

    def test_redundancy_three_distinct_reachable_source_types(self):
        from scripts.scenario import redundancy

        opening = ["@opening", "check_supplies", "go_castle_town"]
        routes = checkpoints.proposed_routes()
        manifest = {"routes": {"normal": {"landmark": "castle"}}, "keys": []}
        examples = {
            "antidote_herb": [
                ("battle", "slime_ambush_one", "@victory", routes["slime_ambush_one"] + ["@victory"]),
                ("exploration", "elf_spring", "gather_antidote_herb_054",
                 routes["forest_wolves"][:-1] + ["gather_antidote_herb_054"]),
            ],
            "burn_salve": [
                ("battle", "cave_heat_corridor", "@victory", routes["cave_heat_corridor"] + ["@victory"]),
                ("exploration", "cave_heat_corridor", "hazard_054_02:success",
                 routes["cave_heat_corridor"] + ["hazard_054_02:success"]),
            ],
            "smelling_salts": [
                ("battle", "goblin_fort_second_left", "@victory",
                 routes["goblin_fort_second_left"] + ["@victory", "use_fort_healing_circle"]),
                ("exploration", "cave_crystal_corridor", "hazard_054_03:success",
                 routes["cave_crystal_corridor"] + ["@victory", "@victory", "prism_back", "hazard_054_03:success",
                                                    "pass_crystal_corridor"]),
            ],
        }
        fresh = checkpoints.fresh_session
        replay_step = checkpoints.replay_step

        def normal_step(value, step):
            # The legacy witness helper assumes victory without creating combat; EXP needs its ID.
            if step == "@victory":
                value["combat_start_requested"] = True
                combat.ensure_combat_started(value)
            event = replay_step(value, step)
            if step == "@victory":
                value["combat"] = None
            return event

        with patch.object(checkpoints, "fresh_session", side_effect=lambda pack, character:
                          fresh(pack, character, "normal", effective=True)), \
                patch.object(checkpoints, "replay_step", side_effect=normal_step):
            for iid, sources in examples.items():
                shop_step = "shop:sarah_shop:" + iid
                sources = [("purchase", "item_shop", shop_step,
                            ["go_item_shop", shop_step, "return_castle_from_item_shop"] + routes["forest_wolves"]), *sources]
                key = {"id": iid, "minimum": 3, "sources": []}
                for kind, location, step, suffix in sources:
                    if location == "cave_heat_corridor":
                        suffix = suffix + (["@victory"] if kind == "exploration" else []) + [
                            "cave_right", "hot_spring_forward", "@victory", "@victory", "leave_prism_tree"]
                    elif location == "cave_crystal_corridor":
                        suffix = suffix + ["leave_prism_tree"]
                    steps = redundancy.finish_witness(self.normal, opening + suffix, "hero")
                    key["sources"].append({"id": kind, "type": kind, "location": location, "step": step,
                                           "reward": {"item": iid}, "witnesses": {"normal": steps}})
                self.assertEqual(len({source["type"] for source in key["sources"]}), 3)
                manifest["keys"].append(key)
            result = redundancy.check(self.normal, manifest)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["counts"]["normal"], dict.fromkeys(examples, 3))

    def test_actual_ai_200_turns_applies_status_for_all_20_enemies(self):
        enemies = index(self.normal["enemies"])
        expected = {}
        for eid, _, sid, *_ in content.STATUS_ATTACKS:
            expected.setdefault(eid, set()).add(sid)
        for eid, _, _, sid, *_ in content.PERIODIC_ATTACKS:
            expected.setdefault(eid, set()).add(sid)
        self.assertEqual(len(expected), 20)
        missing = set()
        for eid, statuses in expected.items():
            value = self.session(location="forest_wolves")
            value["combat_start_requested"] = True
            combat.ensure_combat_started(value)
            actor = value["character"]
            actor["combat"]["defense"] = 0
            actor["attributes"]["dex"] = 0
            actor.update(hp=10000, max_hp=10000, resistances={})
            enemy = deepcopy(enemies[eid])
            enemy.update(id=eid + ":1", hp=99999, max_hp=100000)
            value["combat"]["enemies"] = [enemy]
            seen, rng = set(), random.Random(20261023)
            for turn in range(1, 201):
                actor.update(hp=10000, statuses=[])
                value["combat"].update(round=turn, log=[])
                combat._enemy_phase(value, rng)
                seen.update(status["id"] for status in actor.get("statuses", []) if status_effects.modern(status))
            missing.update((eid, sid) for sid in statuses - seen)
        self.assertEqual(missing, set())

    def test_2026_10_23_design_rulings_1_to_5(self):
        overlays = self.normal["difficulty_overlays"]["normal"]
        phantom_status = [entry for entry in overlays if entry["entity"] == "enemies"
                          and entry["id"] == "xanxus_phantom" and entry["path"].endswith("on_hit_status")]
        self.assertEqual([entry["path"] for entry in phantom_status],
                         ["skills.@id=inferno_focus.on_hit_status"])
        poison_dart = index(self.normal["items"])["poison_dart"]
        self.assertEqual(poison_dart["description"], "毒を塗った投げ矢。敵単体にわずかなダメージを与え、毒を付与する。")
        actions = {action["id"]: action for location in self.normal["locations"]
                   for action in location.get("actions", [])}
        trap_07, trap_08 = actions["hazard_054_07"], actions["hazard_054_08"]
        item_ids = lambda effects: {effect["add_item"]["id"] for effect in effects if "add_item" in effect}
        self.assertIn("antidote_herb", item_ids(trap_07["success_effects"]))
        self.assertNotIn("antidote_herb", item_ids(trap_07["failure_effects"]))
        self.assertEqual(trap_08["hazard"]["kind"], "trap")
        failure_status = next(effect["apply_status"]["id"] for effect in trap_08["failure_effects"]
                              if "apply_status" in effect)
        self.assertEqual(failure_status, "burn")
        self.assertEqual(item_ids(trap_08["success_effects"]), {"oil_flask"})
        self.assertFalse(item_ids(trap_08["failure_effects"]))
        self.assertIn({"gold_change": 15}, trap_08["success_effects"])
        self.assertNotIn({"gold_change": 15}, trap_08["failure_effects"])


if __name__ == "__main__":
    unittest.main()
