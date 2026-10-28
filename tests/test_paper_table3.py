from __future__ import annotations

import shutil
import unittest
import uuid

from scripts.eval import paper_table3
from scripts.eval.snapshots import ROOT


def fake_cell(run_id: str, n: int, s01: int, s3: int) -> dict:
    return {"run_id": run_id, "n": n, "s01": s01, "s3": s3}


class PaperTable3Tests(unittest.TestCase):
    def test_paired_report_rows_are_checked_against_recomputed_cells(self):
        directory = ROOT / ".tmp-test" / f"table3-{uuid.uuid4().hex}"
        directory.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        report = directory / "paired.md"
        report.write_text("| `run-a` | default / dev | cache replay | p | 190/194 | 0.0% / 0.0% | 0.5% / 2.6%（n=190） |\n"
                          "| `run-b` | lenient / dev | cache replay | p | 194/194 | 90.7% / 3.6% | 92.8% / 3.6%（n=194） |\n",
                          encoding="utf-8")
        reported = paper_table3.paired_report_cells(report)
        self.assertEqual(reported["run-a"], ("0.5%", "2.6%", 190))
        cells = {"run-a": fake_cell("run-a", 190, 1, 5), "run-b": fake_cell("run-b", 194, 180, 6)}
        problems = paper_table3.check_against_paired(cells, reported)
        self.assertEqual(len(problems), 1)
        self.assertIn("run-b", problems[0])

    def test_best_breaks_ties_by_lower_s3_then_column_order(self):
        row = {"Flat-Strict": fake_cell("a", 190, 10, 1), "Flat-Lenient": fake_cell("b", 190, 60, 6),
               "Union-Enum": fake_cell("c", 190, 60, 38), "Union-NoEnum": fake_cell("d", 190, 60, 29)}
        self.assertEqual(paper_table3.best(row)[0], "Flat-Lenient")
        row["Flat-Lenient"] = fake_cell("b", 190, 60, 29)
        self.assertEqual(paper_table3.best(row)[0], "Flat-Lenient")


if __name__ == "__main__":
    unittest.main()
