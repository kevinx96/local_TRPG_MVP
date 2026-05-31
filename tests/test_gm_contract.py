import unittest

from host.gm_contract import STATE_MARKER, sanitize_visible_text, split_visible_and_json


class GmContractTests(unittest.TestCase):
    def test_split_visible_and_json_with_marker(self):
        text = (
            "城門が静かに開いた。\n"
            f"{STATE_MARKER}\n"
            '{"gm_text":"城門が静かに開いた。","system_log":"罠によりHPが減少。",'
            '"state_delta":{"hp_change":-1},"choices":[{"text":"扉を調べる"}]}'
        )

        visible, payload, warning = split_visible_and_json(text)

        self.assertEqual(visible, "城門が静かに開いた。")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["state_delta"]["hp_change"], -1)
        self.assertEqual(payload["choices"][0]["text"], "扉を調べる")
        self.assertIsNone(warning)

    def test_split_pure_structured_json(self):
        text = (
            '{"gm_text":"城門が静かに開いた。",'
            '"system_log":"なし",'
            '"dice_type":"1d20",'
            '"state_delta":{"current_scene":"forest"},'
            '"choices":[{"text":"森へ進む","preview":"先へ進む","risk":"判定不要"}]}'
        )

        visible, payload, warning = split_visible_and_json(text)

        self.assertEqual(visible, "城門が静かに開いた。")
        self.assertEqual(payload["state_delta"]["current_scene"], "forest")
        self.assertEqual(payload["choices"][0]["text"], "森へ進む")
        self.assertIsNone(warning)

    def test_split_visible_and_json_falls_back_to_plain_text(self):
        visible, payload, warning = split_visible_and_json("普通の文章だけです。")

        self.assertEqual(visible, "普通の文章だけです。")
        self.assertIsNone(payload)
        self.assertIsNotNone(warning)

    def test_internal_prompt_and_inline_choices_are_hidden(self):
        text = (
            "王の間。国王は重い使命を告げた。\n\n"
            "次の選択肢:\n"
            "1. 薬草でHPを回復し、情報収集へ向かう\n"
            "2. 支度金50ゴールドで道具屋で買い物をする\n"
            "3. スライムの森に赴く\n\n"
            "GM本文の後には次のJSON形式で状態を出力してください。\n"
            f"{STATE_MARKER}\n"
            '{"gm_text":"王の間。国王は重い使命を告げた。",'
            '"system_log":"","state_delta":{},'
            '"choices":[{"text":"国王に詳しい話を聞く","preview":"","risk":"判定不要"}]}'
        )

        visible, payload, warning = split_visible_and_json(text)

        self.assertEqual(visible, "王の間。国王は重い使命を告げた。")
        self.assertNotIn("GM本文", visible)
        self.assertNotIn("次の選択肢", visible)
        self.assertEqual(payload["choices"][0]["text"], "薬草でHPを回復し、情報収集へ向かう")
        self.assertIsNone(warning)

    def test_recovers_choice_cards_when_json_is_missing(self):
        text = (
            "GM:\n\n"
            "霧の深い地下道が続いている。\n\n"
            "以下の選択肢から行動を選んでください。\n\n"
            "1. 扉を調べる\n"
            "2. 仲間に話しかける\n"
            "3. 慎重に先へ進む\n"
        )

        visible, payload, warning = split_visible_and_json(text)

        self.assertEqual(visible, "霧の深い地下道が続いている。")
        self.assertIsNotNone(payload)
        self.assertEqual(
            [choice["text"] for choice in payload["choices"]],
            ["扉を調べる", "仲間に話しかける", "慎重に先へ進む"],
        )
        self.assertIsNotNone(warning)

    def test_text_choices_override_incomplete_json_choices(self):
        text = (
            "森の入口に暗い道が続いている。\n\n"
            "以下の選択肢から行動を選んでください。\n\n"
            "1. 王の間で情報収集\n"
            "2. スライムの森に足を踏み入れる\n"
            f"\n{STATE_MARKER}\n"
            '{"gm_text":"森の入口に暗い道が続いている。",'
            '"state_delta":{},'
            '"choices":[{"text":"城外の村へ向かう"}]}'
        )

        visible, payload, warning = split_visible_and_json(text)

        self.assertEqual(visible, "森の入口に暗い道が続いている。")
        self.assertEqual(
            [choice["text"] for choice in payload["choices"]],
            ["王の間で情報収集", "スライムの森に足を踏み入れる"],
        )
        self.assertIsNone(warning)

    def test_recovers_multiline_numbered_choices(self):
        text = (
            "次に、どうする？\n"
            "行動を選択してください\n\n"
            "1\n"
            "鉄の剣でスライムを攻撃する\n"
            "戦闘チュートリアルを進めます\n"
            "1d20判定が必要（DC10）\n\n"
            "2\n"
            "森を抜けて村へ向かう\n"
            "第3章へ進みます\n"
            "判定不要\n"
        )

        visible, payload, warning = split_visible_and_json(text)

        self.assertEqual(visible, "")
        self.assertEqual(
            [choice["text"] for choice in payload["choices"]],
            ["鉄の剣でスライムを攻撃する", "森を抜けて村へ向かう"],
        )
        self.assertIsNotNone(warning)

    def test_protocol_tail_after_json_label_is_hidden(self):
        text = (
            "白い城造りの城。国王は使命を告げた。\n\n"
            "では、まずは支度金を得てから任務に臨むべきか？それとも邪竜の弱点を探ることから始めるべき？\n"
            " JSON:\n"
            "現在あなたは「Gundam」。ゲーム状況は上記JSON内に示しています。次のステップは何をしますか？"
        )

        visible, payload, warning = split_visible_and_json(text)

        self.assertEqual(visible, "白い城造りの城。国王は使命を告げた。")
        self.assertIsNone(payload)
        self.assertIsNotNone(warning)

    def test_thinking_blocks_are_hidden(self):
        self.assertEqual(
            sanitize_visible_text("<think>\ninternal planning\n</think>\n城門が開いた。"),
            "城門が開いた。",
        )
        self.assertEqual(sanitize_visible_text("山道。\n<think>\ninternal planning"), "山道。")


if __name__ == "__main__":
    unittest.main()
