import unittest

from host.gm_contract import STATE_MARKER, split_visible_and_json


class GmContractTests(unittest.TestCase):
    def test_split_visible_and_json_with_marker(self):
        text = (
            "扉が静かに開いた。"
            f"\n{STATE_MARKER}\n"
            '{"gm_text":"扉が静かに開いた。","system_log":"なし","state_delta":{"hp_change":-1}}'
        )

        visible, payload, warning = split_visible_and_json(text)

        self.assertEqual(visible, "扉が静かに開いた。")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["state_delta"]["hp_change"], -1)
        self.assertIsNone(warning)

    def test_split_visible_and_json_falls_back_to_plain_text(self):
        visible, payload, warning = split_visible_and_json("普通の文章だけ")

        self.assertEqual(visible, "普通の文章だけ")
        self.assertIsNone(payload)
        self.assertIsNotNone(warning)


if __name__ == "__main__":
    unittest.main()
