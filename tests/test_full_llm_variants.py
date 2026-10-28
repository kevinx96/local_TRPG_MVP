from __future__ import annotations

import hashlib
import unittest

from scripts.eval.full_llm import PROMPTS

FLAGS_SENTENCE = "flags には提示された効果に含まれるIDだけを設定する。状態の欄にない出来事（戦闘の開始、準備など）は reply にだけ書く。"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FullLlmVariantTests(unittest.TestCase):
    def test_three_variants_exist(self):
        self.assertEqual(set(PROMPTS), {"full_naive", "full_guarded", "full_guarded_flags"})

    def test_first_two_prompts_unchanged(self):
        # Their text is part of the cache key; changing it would invalidate the recorded E8 runs.
        self.assertEqual(digest(PROMPTS["full_naive"]), "69b3af1d70ef88d8e613616b8cd85357f7b36d9178eab8611d8186956f27ee7e")
        self.assertEqual(digest(PROMPTS["full_guarded"]), "9a7156fcabc9d81ec168243505bb0fea22a8aa9c58568db313387a8fb11bcf63")

    def test_flags_variant_extends_guarded(self):
        self.assertTrue(PROMPTS["full_guarded_flags"].startswith(PROMPTS["full_guarded"]))
        self.assertEqual(PROMPTS["full_guarded_flags"], PROMPTS["full_guarded"] + "\n" + FLAGS_SENTENCE)


if __name__ == "__main__":
    unittest.main()
