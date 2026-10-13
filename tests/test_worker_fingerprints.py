from __future__ import annotations

import unittest

from scripts import worker_fingerprints


class WorkerFingerprintTests(unittest.TestCase):
    def test_proxy_fingerprints_match_current_prompts(self):
        # A stale list would make the demo proxy reject every request after a prompt edit.
        self.assertEqual(worker_fingerprints.TARGET.read_text(encoding="utf-8"), worker_fingerprints.render())


if __name__ == "__main__":
    unittest.main()
