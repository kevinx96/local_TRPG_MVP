from __future__ import annotations

import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import item_mechanics, state
from scripts.balance import checkpoints
from scripts.scenario.ruby_names import NAMES, PACKS, apply


class RubyNameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs = [json.loads(checkpoints.DEFAULT_SCENARIO.with_name(name).read_text(encoding="utf-8")) for name in PACKS]

    def test_migration_is_idempotent_and_text_is_japanese(self):
        for pack in self.packs:
            again = deepcopy(pack)
            apply(again)
            self.assertEqual(again, pack)
            text = json.dumps({k: v for k, v in pack.items() if k != "meta"}, ensure_ascii=False)
            self.assertEqual(text.count("Xanxus"), 1, "only the keyword players may type")
            self.assertNotRegex(text, r"(physical|fire|ice|arcane|holy|dark|water|earth)属性")
            self.assertEqual(pack["meta"]["ruby_names"], NAMES)

    def test_every_glossary_name_appears_in_the_scenario(self):
        text = json.dumps(self.packs[0], ensure_ascii=False)
        for kana in NAMES:
            self.assertGreater(text.count(kana), 1, kana)

    def test_element_labels_and_frozen_legacy_ids(self):
        sword = {"combat": {"kind": "weapon", "damage": "1d8", "accuracy": 90, "element": "physical"}}
        self.assertIn("物理属性", item_mechanics.structured_item_effect(sword))
        with patch.object(item_mechanics, "LEGACY_ELEMENT_IDS", True):
            self.assertIn("physical属性", item_mechanics.structured_item_effect(sword))

    def test_public_session_exposes_the_glossary(self):
        session = checkpoints.fresh_session(deepcopy(self.packs[0]), "hero")
        public = state.public_session(session)
        self.assertEqual(public["ruby"]["names"]["ザンザス"], "Xanxus")
        self.assertEqual(public["ruby"]["elements"]["ice"], "氷")
        self.assertNotIn("scenario_pack", public)


if __name__ == "__main__":
    unittest.main()
