import unittest

from host.llm_client import _apply_response_format, _message_role_summary, model_candidates


class LLMClientTests(unittest.TestCase):
    def test_model_candidates_prefers_primary_then_fallbacks(self):
        backend = {
            "model": "elyza-jp-8b-local",
            "fallback_models": [
                "qwen2.5-7b-instruct-local",
                "qwen2.5:7b-instruct",
            ],
        }

        self.assertEqual(
            model_candidates(backend),
            [
                "elyza-jp-8b-local",
                "qwen2.5-7b-instruct-local",
                "qwen2.5:7b-instruct",
            ],
        )

    def test_model_candidates_removes_duplicates(self):
        backend = {
            "model": "elyza-jp-8b-local",
            "fallback_models": [
                "elyza-jp-8b-local",
                "qwen2.5-7b-instruct-local",
            ],
        }

        self.assertEqual(
            model_candidates(backend),
            [
                "elyza-jp-8b-local",
                "qwen2.5-7b-instruct-local",
            ],
        )

    def test_message_role_summary(self):
        self.assertEqual(
            _message_role_summary([
                {"role": "system", "content": "a"},
                {"role": "assistant", "content": "b"},
                {"role": "user", "content": "c"},
                {"role": "system", "content": "d"},
            ]),
            "assistant:1,system:2,user:1",
        )

    def test_apply_response_format_json_object(self):
        payload = {}
        _apply_response_format(payload, {"response_format": "json_object"})
        self.assertEqual(payload["response_format"], {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
