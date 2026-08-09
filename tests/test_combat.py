import json
import random
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from host import app as app_module
from host import combat, state
from host.item_mechanics import item_mechanic_warning, structured_item_effect
from host.scenario_context import current_action_choices


class CombatEngineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd() / ".tmp-test" / f"combat-{uuid.uuid4().hex}"
        self.root.mkdir(parents=True)
        self.original_save_dir = state.SAVE_DIR
        state.SAVE_DIR = self.root / "saves"

    def tearDown(self):
        state.SAVE_DIR = self.original_save_dir

    def write_pack(self, enemy=None, character=None, combat_rules=None) -> Path:
        enemy = enemy or {
            "id": "dummy",
            "name": "訓練人形",
            "hp": 5,
            "max_hp": 5,
            "combat": {"basic_attack": {"name": "反撃", "damage": "2", "accuracy": 0}},
            "rewards": {"gold": 7, "flags": ["won_training"]},
        }
        character = character or {
            "id": "hero",
            "name": "勇者",
            "default_name": "アルス",
            "hp": 20,
            "max_hp": 20,
            "mp": 10,
            "max_mp": 10,
            "sp": 10,
            "max_sp": 10,
            "attributes": {"str": 10, "dex": 10, "int": 10, "end": 10},
            "inventory": [],
            "equipment": [],
            "skills": [],
            "combat": {"basic_attack": {"name": "テスト攻撃", "damage": "10", "accuracy": 100}},
        }
        pack = {
            "meta": {"title": "戦闘試験", "language": "ja", "initial_scene": "arena"},
            "rules": [],
            "combat_rules": combat_rules or {"sp_regen_per_round": 0, "flee_formula": "20", "flee_dc": 12},
            "scenes": [{"id": "arena", "title": "闘技場", "location_ids": ["arena"]}],
            "locations": [{"id": "arena", "title": "闘技場", "enemy_ids": [enemy["id"]], "combat": {"flee_allowed": True}}],
            "enemies": [enemy],
            "characters": [character],
            "fallback_choices": [{"text": "周囲を確認する", "preview": "", "risk": "判定不要"}],
        }
        path = self.root / "combat.json"
        path.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
        return path

    def create(self, **kwargs):
        character = kwargs.get("character") or {}
        character_id = character.get("id", "hero")
        public = state.create_session(str(self.write_pack(**kwargs)), character_id=character_id)
        return state.load_session(public["id"])

    def test_attack_resolves_victory_and_engine_rewards(self):
        session = self.create()

        result = combat.perform_combat_action(session, "attack", rng=random.Random(1))
        delta = combat.consume_combat_state_delta(session)

        self.assertEqual(result["status"], "victory")
        self.assertTrue(session["combat"]["pending_resolution"])
        self.assertEqual(delta["gold_change"], 7)
        self.assertIn("won_training", delta["flags_set"])
        self.assertTrue(session["flags"]["combat_defeated:arena:dummy"])

    def test_defend_reduces_enemy_damage_without_llm(self):
        enemy = {
            "id": "soldier",
            "name": "兵士",
            "hp": 30,
            "max_hp": 30,
            "combat": {"basic_attack": {"name": "強打", "damage": "10", "accuracy": 100}},
        }
        session = self.create(enemy=enemy, combat_rules={"defend_multiplier": 0.5, "sp_regen_per_round": 0})

        combat.perform_combat_action(session, "defend", rng=random.Random(2))

        self.assertEqual(session["character"]["hp"], 15)
        self.assertTrue(any(entry["kind"] == "defend" for entry in session["combat"]["log"]))

    def test_skill_consumes_resource_and_uses_structured_damage(self):
        enemy = {
            "id": "target",
            "name": "標的",
            "hp": 20,
            "max_hp": 20,
            "combat": {"basic_attack": {"damage": "1", "accuracy": 0}},
        }
        character = {
            "id": "mage",
            "name": "魔法使い",
            "hp": 15,
            "max_hp": 15,
            "mp": 8,
            "max_mp": 8,
            "sp": 0,
            "max_sp": 0,
            "attributes": {"int": 12, "dex": 8, "end": 8},
            "inventory": [],
            "equipment": [],
            "skills": [{"id": "ice", "name": "氷槍", "kind": "attack", "damage": "10", "accuracy": 100, "element": "ice", "cost": 3, "cost_type": "mp"}],
        }
        session = self.create(enemy=enemy, character=character, combat_rules={"sp_regen_per_round": 0})

        combat.perform_combat_action(session, "skill", action_id="ice", rng=random.Random(3))

        self.assertEqual(session["character"]["mp"], 5)
        self.assertEqual(session["combat"]["enemies"][0]["hp"], 10)

    def test_equipped_item_reduces_structured_skill_cost(self):
        enemy = {
            "id": "target",
            "name": "target",
            "hp": 20,
            "max_hp": 20,
            "combat": {"basic_attack": {"damage": "1", "accuracy": 0}},
        }
        character = {
            "id": "mage",
            "name": "mage",
            "hp": 12,
            "max_hp": 12,
            "mp": 20,
            "max_mp": 20,
            "sp": 0,
            "max_sp": 0,
            "attributes": {"int": 12, "dex": 8, "end": 8},
            "inventory": [{
                "id": "mage_robe",
                "name": "mage robe",
                "quantity": 1,
                "combat": {"kind": "equipment", "cost_reduction": {"mp": 1}},
            }],
            "equipment": ["mage robe"],
            "skills": [{
                "id": "ice_arrow",
                "name": "ice arrow",
                "kind": "attack",
                "damage": "10",
                "accuracy": 100,
                "cost": 3,
                "cost_type": "mp",
            }],
        }
        session = self.create(enemy=enemy, character=character, combat_rules={"sp_regen_per_round": 0})

        skill_action = next(action for action in combat.combat_actions(session) if action["id"] == "ice_arrow")
        combat.perform_combat_action(session, "skill", action_id="ice_arrow", rng=random.Random(3))

        self.assertEqual(skill_action["cost"], 2)
        self.assertEqual(session["character"]["mp"], 18)

    def test_structured_mp_restore_item_is_available_and_consumed(self):
        enemy = {
            "id": "target",
            "name": "target",
            "hp": 20,
            "max_hp": 20,
            "combat": {"basic_attack": {"damage": "1", "accuracy": 0}},
        }
        character = {
            "id": "mage",
            "name": "mage",
            "hp": 12,
            "max_hp": 12,
            "mp": 2,
            "max_mp": 20,
            "sp": 0,
            "max_sp": 0,
            "attributes": {"int": 12, "dex": 8, "end": 8},
            "inventory": [{
                "id": "mp_potion",
                "name": "MP potion",
                "quantity": 1,
                "combat": {"kind": "restore", "resource": "mp", "amount": "10", "consumable": True},
            }],
            "equipment": [],
            "skills": [],
        }
        session = self.create(enemy=enemy, character=character, combat_rules={"sp_regen_per_round": 0})

        item_action = next(action for action in combat.combat_actions(session) if action["id"] == "mp_potion")
        combat.perform_combat_action(session, "item", action_id="mp_potion", rng=random.Random(3))

        self.assertEqual(item_action["kind"], "restore")
        self.assertEqual(session["character"]["mp"], 12)
        self.assertFalse(any(item.get("id") == "mp_potion" for item in session["character"]["inventory"]))

    def test_model_combat_log_cannot_claim_uncommitted_full_restore(self):
        session = self.create()
        with patch.object(app_module, "chat_completion") as completion:
            combat.perform_combat_action(session, "attack", rng=random.Random(1))
            delta = combat.consume_combat_state_delta(session)
            state.apply_state_delta(session, delta)
            completion.return_value = json.dumps({
                "gm_text": "battle ended",
                "system_log": "HP and MP fully restored",
                "dice_type": "1d20",
                "dice_dc": 0,
                "state_delta": {},
                "choices": [],
            })
            app_module._run_combat_resolution(session)

        public_logs = [entry["text"] for entry in state.public_session(session)["system_logs"]]
        self.assertNotIn("HP and MP fully restored", public_logs)
        self.assertTrue(any(entry.get("kind") == "combat_resolved" for entry in session.get("event_log", [])))

    def test_flee_finishes_without_enemy_phase(self):
        session = self.create()
        before_hp = session["character"]["hp"]

        result = combat.perform_combat_action(session, "flee", rng=random.Random(4))

        self.assertEqual(result["status"], "fled")
        self.assertEqual(session["character"]["hp"], before_hp)

    def test_regular_turn_is_rejected_while_combat_is_active(self):
        session = self.create()
        request = app_module.TurnRequest(text="自由入力")

        with self.assertRaises(HTTPException) as caught:
            app_module._run_turn(session, request)

        self.assertEqual(caught.exception.status_code, 409)

    def test_llm_is_called_only_when_finished_result_is_resolved(self):
        session = self.create()
        with patch.object(app_module, "chat_completion") as completion:
            combat.perform_combat_action(session, "attack", rng=random.Random(1))
            delta = combat.consume_combat_state_delta(session)
            state.apply_state_delta(session, delta)
            self.assertEqual(completion.call_count, 0)

            completion.return_value = json.dumps({
                "gm_text": "敵を倒し、闘技場に静けさが戻った。",
                "system_log": "戦闘結果を反映しました。",
                "dice_type": "1d20",
                "dice_dc": 0,
                "state_delta": {},
                "choices": [{"text": "周囲を確認する", "preview": "", "risk": "判定不要"}],
            }, ensure_ascii=False)
            app_module._run_combat_resolution(session)

        self.assertEqual(completion.call_count, 1)
        self.assertIsNone(session["combat"])
        self.assertEqual(session["last_combat_result"]["outcome"], "victory")
        self.assertTrue(session["choices"])

    def test_base_and_hybrid_combat_data_stay_aligned(self):
        scenario_root = Path("host/prompt/processed")
        base = json.loads((scenario_root / "dragon_rpg.json").read_text(encoding="utf-8-sig"))
        hybrid = json.loads((scenario_root / "dragon_rpg_hybrid.json").read_text(encoding="utf-8-sig"))

        self.assertEqual(base.get("combat_rules"), hybrid.get("combat_rules"))
        for section, fields in {
            "locations": ("enemy_ids", "combat"),
            "enemies": ("hp", "max_hp", "combat", "resistances", "rewards", "skills"),
            "characters": ("combat", "skills", "inventory", "equipment"),
        }.items():
            base_records = {record["id"]: record for record in base.get(section, []) if record.get("id")}
            hybrid_records = {record["id"]: record for record in hybrid.get(section, []) if record.get("id")}
            self.assertEqual(set(base_records), set(hybrid_records), section)
            for record_id, base_record in base_records.items():
                for field in fields:
                    self.assertEqual(
                        base_record.get(field),
                        hybrid_records[record_id].get(field),
                        f"{section}.{record_id}.{field}",
                    )

        base_items = {record["id"]: record for record in base.get("items", []) if record.get("id")}
        hybrid_items = {record["id"]: record for record in hybrid.get("items", []) if record.get("id")}
        combat_item_ids = {
            record_id
            for record_id, record in {**base_items, **hybrid_items}.items()
            if record.get("combat")
        }
        for item_id in combat_item_ids:
            self.assertIn(item_id, base_items)
            self.assertIn(item_id, hybrid_items)
            self.assertEqual(base_items[item_id].get("combat"), hybrid_items[item_id].get("combat"))

        post_combat_session = {
            "scenario_pack": base,
            "current_scene": "dark_forest",
            "current_location": "dark_forest_loc",
            "flags": {"combat_defeated:dark_forest_loc:slime": True},
            "character": {},
        }
        post_combat_choices = state.annotate_choices_for_session(
            current_action_choices(post_combat_session),
            post_combat_session,
        )
        post_combat_by_id = {choice.get("action_id"): choice for choice in post_combat_choices}
        self.assertFalse(post_combat_by_id["attack_slime"]["enabled"])
        self.assertFalse(post_combat_by_id["bypass_slime"]["enabled"])
        self.assertNotEqual(post_combat_by_id["go_village"].get("enabled"), False)

    def test_item_effect_text_is_derived_from_structured_mechanics(self):
        robe = {
            "name": "robe",
            "description": "magic robe",
            "effect": "untrusted prose claim",
            "combat": {"kind": "equipment", "cost_reduction": {"mp": 1}},
        }
        unsupported = {"name": "mystery", "description": "does something", "effect": "power +99"}

        self.assertEqual(structured_item_effect(robe), "MP消費を1軽減")
        self.assertEqual(item_mechanic_warning(robe), "")
        self.assertTrue(item_mechanic_warning(unsupported))

    def test_dragon_scenario_shop_items_and_mage_robe_have_engine_mechanics(self):
        pack = json.loads(Path("host/prompt/processed/dragon_rpg.json").read_text(encoding="utf-8-sig"))
        items = {item["name"]: item for item in pack["items"]}
        mage = next(character for character in pack["characters"] if character["id"] == "mage")
        robe = next(item for item in mage["inventory"] if item["name"] == "魔法のローブ")

        self.assertEqual(items["魔法の巻物"]["combat"]["kind"], "damage")
        self.assertTrue(items["魔法の巻物"]["combat"]["consumable"])
        self.assertEqual(items["MP回復薬"]["combat"], {"kind": "restore", "resource": "mp", "amount": "10", "consumable": True})
        self.assertEqual(robe["combat"]["cost_reduction"]["mp"], 1)


if __name__ == "__main__":
    unittest.main()
