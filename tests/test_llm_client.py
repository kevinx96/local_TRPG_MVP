import unittest

from host.llm_client import model_candidates


class LLMClientTests(unittest.TestCase):
    def test_model_candidates_prefers_primary_then_fallbacks(self):
        backend = {
            "model": "Llama-3-ELYZA-JP-8B-q4_k_m",
            "fallback_models": [
                "qwen2.5-7b-instruct-q4_k_m",
                "qwen2.5:7b-instruct",
            ],
        }

        self.assertEqual(
            model_candidates(backend),
            [
                "Llama-3-ELYZA-JP-8B-q4_k_m",
                "qwen2.5-7b-instruct-q4_k_m",
                "qwen2.5:7b-instruct",
            ],
        )

    def test_model_candidates_removes_duplicates(self):
        backend = {
            "model": "Llama-3-ELYZA-JP-8B-q4_k_m",
            "fallback_models": [
                "Llama-3-ELYZA-JP-8B-q4_k_m",
                "qwen2.5-7b-instruct-q4_k_m",
            ],
        }

        self.assertEqual(
            model_candidates(backend),
            [
                "Llama-3-ELYZA-JP-8B-q4_k_m",
                "qwen2.5-7b-instruct-q4_k_m",
            ],
        )


if __name__ == "__main__":
    unittest.main()
