import unittest

from host.llm_client import model_candidates


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


if __name__ == "__main__":
    unittest.main()
