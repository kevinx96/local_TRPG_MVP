import unittest

from host.generate_hybrid_scenario import (
    _should_fallback_gemini_error,
    apply_hybrid_scene,
    build_gemini_prompt,
    model_names_from_args,
)


class GenerateHybridScenarioTests(unittest.TestCase):
    def pack(self):
        return {
            "meta": {"title": "Demo", "language": "ja", "initial_scene": "start"},
            "rules": ["Do not act for the player."],
            "scenes": [
                {
                    "id": "start",
                    "title": "Start",
                    "description": "Opening scene.",
                    "fallback_choices": [{"text": "Look around", "preview": "", "risk": ""}],
                }
            ],
            "locations": [],
            "npcs": [],
            "items": [],
            "clues": [],
            "fallback_choices": [],
        }

    def test_build_gemini_prompt_wraps_runtime_messages_and_authoring_task(self):
        pack = self.pack()
        prompt = build_gemini_prompt(
            [{"role": "system", "content": "runtime contract"}, {"role": "user", "content": "latest turn"}],
            pack,
            pack["scenes"][0],
        )

        self.assertIn("--- SYSTEM MESSAGE 1 ---", prompt)
        self.assertIn("runtime contract", prompt)
        self.assertIn("--- OFFLINE HYBRID AUTHORING TASK ---", prompt)
        self.assertIn('"scene_id": "start"', prompt)
        self.assertIn('"Return JSON only."', prompt)
        self.assertIn("pre-cooked GM response pack", prompt)
        self.assertIn('"prepared_turns"', prompt)
        self.assertIn('"draft"', prompt)
        self.assertIn('"gm_text"', prompt)

    def test_apply_hybrid_scene_adds_hybrid_data_and_choices(self):
        pack = self.pack()
        apply_hybrid_scene(
            pack,
            "start",
            {
                "scene_id": "start",
                "hybrid": {
                    "mode": "prepared_gm_turns",
                    "summary": "Fixed draft.",
                    "prepared_turns": [
                        {
                            "id": "opening turn",
                            "purpose": "opening",
                            "player_intent": "start",
                            "trigger_keywords": ["start"],
                            "draft": {
                                "gm_text": "GM: The hall opens before you.",
                                "system_log": "Opening.",
                                "dice_type": "1d20",
                                "dice_dc": "bad",
                                "state_delta": "bad",
                                "choices": [{"text": "Step forward"}],
                            },
                            "rewrite_notes": ["Keep the hall."],
                        }
                    ],
                    "dialogue_turns": [
                        {
                            "id": "intro turn",
                            "trigger_keywords": ["start"],
                            "gm_text": "GM: The hall opens before you.",
                            "choices": [{"text": "Step forward"}],
                            "followups": [
                                {
                                    "choice_text": "Step forward",
                                    "gm_text": "GM: Your boots echo across the stone.",
                                    "state_delta": "bad",
                                }
                            ],
                        }
                    ],
                    "beats": [
                        {
                            "id": "opening beat",
                            "trigger_keywords": ["hall"],
                            "text": "A quiet hall waits.",
                            "choices": ["Inspect banners"],
                        }
                    ],
                    "branches": [{"id": "branch 1", "from_choice": "Inspect banners", "state_delta": "bad"}],
                    "gm_notes": ["Tune later."],
                },
                "fallback_choices": ["Inspect banners"],
            },
        )

        scene = pack["scenes"][0]
        self.assertEqual(scene["hybrid"]["mode"], "prepared_gm_turns")
        self.assertEqual(scene["hybrid"]["summary"], "Fixed draft.")
        self.assertEqual(scene["hybrid"]["prepared_turns"][0]["id"], "opening_turn")
        self.assertEqual(scene["hybrid"]["prepared_turns"][0]["purpose"], "opening")
        self.assertEqual(scene["hybrid"]["prepared_turns"][0]["draft"]["gm_text"], "GM: The hall opens before you.")
        self.assertEqual(scene["hybrid"]["prepared_turns"][0]["draft"]["dice_dc"], 10)
        self.assertEqual(scene["hybrid"]["prepared_turns"][0]["draft"]["state_delta"], {})
        self.assertEqual(scene["hybrid"]["dialogue_turns"][0]["id"], "intro_turn")
        self.assertEqual(scene["hybrid"]["dialogue_turns"][0]["gm_text"], "GM: The hall opens before you.")
        self.assertEqual(scene["hybrid"]["dialogue_turns"][0]["followups"][0]["state_delta"], {})
        self.assertEqual(scene["hybrid"]["beats"][0]["id"], "opening_beat")
        self.assertEqual(scene["hybrid"]["beats"][0]["choices"][0]["text"], "Inspect banners")
        self.assertEqual(scene["hybrid"]["branches"][0]["state_delta"], {})
        self.assertEqual(scene["fallback_choices"][0]["text"], "Inspect banners")

    def test_model_names_from_args_dedupes_single_and_fallback_list(self):
        names = model_names_from_args("gemini-flash-latest", "gemini-flash-latest, gemini-2.5-flash gemini-2.0-flash")

        self.assertEqual(names, ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"])

    def test_should_fallback_on_quota_errors(self):
        self.assertTrue(_should_fallback_gemini_error(RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded")))
        self.assertTrue(_should_fallback_gemini_error(RuntimeError("model returned malformed JSON")))
        self.assertFalse(_should_fallback_gemini_error(RuntimeError("invalid API key")))


if __name__ == "__main__":
    unittest.main()
