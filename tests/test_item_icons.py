from __future__ import annotations

import json
import struct
import unittest
from copy import deepcopy

from host import combat, shops, state
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session
from scripts.scenario.item_icons import PACKS, PILOTS, ROOT, apply, catalog, records


class ItemIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs = [json.loads(DEFAULT_SCENARIO.with_name(name).read_text(encoding="utf-8")) for name in PACKS]

    def test_all_catalog_and_inline_items_have_existing_icons(self):
        shared = {}
        for pack in self.packs:
            for item in records(pack):
                with self.subTest(pack=pack["meta"]["title"], item=item["name"]):
                    icon = item.get("icon", "")
                    self.assertRegex(icon, r"^/static/images/icon_[a-z0-9_]+\.png$")
                    self.assertTrue((ROOT / "client" / icon.removeprefix("/static/")).is_file(), icon)
                    self.assertEqual(shared.setdefault(item["name"], icon), icon)
        self.assertEqual(len(shared), 76)

    def test_all_icons_are_128px_rgba_and_under_two_megabytes(self):
        icons = list((ROOT / "client/images").glob("icon_*.png"))
        self.assertEqual({p.name for p in icons}, {e["id"] + ".png" for e in catalog()})
        for path in icons:
            with self.subTest(icon=path.name):
                header = path.read_bytes()[:33]
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(header[12:16], b"IHDR")
                self.assertEqual(struct.unpack(">II", header[16:24]), (128, 128))
                self.assertEqual(header[24:26], bytes([8, 6]), "8-bit RGBA required")
        self.assertLess(sum(p.stat().st_size for p in icons), 2_000_000)

    def test_manifest_covers_every_icon_with_review_status(self):
        manifest = json.loads((ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
        by_file = {entry["file"]: entry for entry in manifest["images"]}
        for entry in catalog():
            with self.subTest(icon=entry["id"]):
                registered = by_file[entry["file"]]
                self.assertIsInstance(registered["approved"], bool)
                self.assertEqual(registered["task"], "034" if entry["retained_from"] else entry["task"])
        self.assertEqual(len([e for e in catalog() if e["retained_from"]]), len(PILOTS))

    def test_apply_is_idempotent_and_changes_only_icon_metadata(self):
        for pack in self.packs:
            updated = deepcopy(pack)
            for item in records(updated):
                item.pop("icon", None)
            updated["meta"].pop("item_icons_v036", None)
            apply(updated)
            self.assertEqual(updated, pack)
            apply(updated)
            self.assertEqual(updated, pack)
        self.assertEqual({i["name"]: i["icon"] for i in records(self.packs[0])},
                         {i["name"]: i["icon"] for i in records(self.packs[1])})

    def test_initial_inventory_and_all_shop_rows_expose_icons(self):
        pack = self.packs[0]
        for character in pack["characters"]:
            session = fresh_session(deepcopy(pack), character["id"])
            public = state.public_session(session)
            self.assertTrue(all(i.get("icon") for i in public["character"]["inventory"]))
        for shop in pack["shops"]:
            session = fresh_session(deepcopy(pack), "hero")
            location = next(loc for loc in pack["locations"] if loc["id"] == shop["location_id"])
            session["world_state"] = dict(scene_id=location["scene_id"], location_id=location["id"])
            session["flags"]["saved_gald"] = True
            public = shops.public_shop(session, shop["id"])
            for row in public["items"] + public["sell_items"]:
                self.assertTrue(row.get("icon"), (shop["id"], row["name"]))

    def test_combat_item_actions_preserve_icons_and_iconless_items_work(self):
        session = fresh_session(deepcopy(self.packs[0]), "hero")
        state.apply_state_delta(session, {"inventory_add": [dict(item, quantity=1) for item in self.packs[0]["items"]]})
        actions = combat.combat_actions(session)
        icons = {item["name"]: item["icon"] for item in session["character"]["inventory"]}
        self.assertGreater(len([a for a in actions if a["type"] == "item"]), 5)
        for action in actions:
            if action["type"] == "item":
                self.assertEqual(action["icon"], icons[action["name"]])
            else:
                self.assertNotIn("icon", action)
        for item in session["character"]["inventory"]:
            item.pop("icon", None)
        without = combat.combat_actions(session)
        self.assertEqual(without, [{k: v for k, v in a.items() if k != "icon"} for a in actions])

    def test_reforged_armor_keeps_original_icon(self):
        for character_id in ("hero", "cleric", "mage", "thief"):
            session = fresh_session(deepcopy(self.packs[0]), character_id)
            original = next(i for i in session["character"]["inventory"] if i.get("slot") == "armor")
            state._reforge_equipped_armor(session, dict(suffix="＋", defense_bonus=1, fallback_item="守護団の鎖帷子"))
            upgraded = next(i for i in session["character"]["inventory"] if i["name"] == original["name"] + "＋")
            self.assertEqual(upgraded["icon"], original["icon"])
        for armor in (i for i in self.packs[0]["items"] if i.get("slot") == "armor"):
            session = fresh_session(deepcopy(self.packs[0]), "hero")
            state.apply_state_delta(session, {"inventory_add": [dict(armor, quantity=1)], "equip_item": armor["name"]})
            state._reforge_equipped_armor(session, dict(suffix="＋", defense_bonus=1, fallback_item="守護団の鎖帷子"))
            upgraded = next(i for i in session["character"]["inventory"] if i["name"] == armor["name"] + "＋")
            self.assertEqual(upgraded["icon"], armor["icon"])


if __name__ == "__main__":
    unittest.main()
