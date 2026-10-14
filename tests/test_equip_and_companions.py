from __future__ import annotations

import unittest
from copy import deepcopy

from host import shops, state
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session


class EquipAndCompanionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(DEFAULT_SCENARIO)

    def session(self, character="hero"):
        session = fresh_session(deepcopy(self.pack), character)
        state.apply_state_delta(session, {"current_location": "forge"}, allow_world_transition=True)
        return session

    def test_bought_armor_and_weapon_can_be_equipped_from_the_bag(self):
        session = self.session()
        session["character"]["gold"] = 500
        shops.trade(session, "forge_shop", "adamantite_armor", 1)
        self.assertNotIn("アダマンタイトの鎧", session["character"]["equipment"])
        self.assertIn("装備した", shops.use_item(session, "adamantite_armor"))
        self.assertIn("アダマンタイトの鎧", session["character"]["equipment"])
        with self.assertRaises(shops.ShopError):
            shops.use_item(session, "adamantite_armor")

        staff = next(item for item in session["scenario_pack"]["items"] if item["id"] == "earth_staff")
        state.apply_state_delta(session, {"inventory_add": [{**staff, "quantity": 1}]})
        shops.use_item(session, "earth_staff")
        weapons = [name for name in session["character"]["equipment"] if name in {"鉄の剣", "大地の杖"}]
        self.assertEqual(weapons, ["大地の杖"])

    def test_every_companion_acts_in_battle_and_says_so(self):
        for companion in self.pack["companions"]:
            with self.subTest(companion=companion["id"]):
                self.assertTrue(companion.get("round_start_effects"))
                self.assertIn("ラウンド", companion["description"])


if __name__ == "__main__":
    unittest.main()
