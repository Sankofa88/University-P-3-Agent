import tempfile
import unittest
from pathlib import Path

from p3_agent_system import build_master, load_config


class FixtureRunTest(unittest.TestCase):
    def test_fixture_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = load_config(use_fixture_data=True, output_dir=tmp_dir)
            outputs = build_master(config).run()
            self.assertEqual(
                set(outputs),
                {
                    "json_report",
                    "csv_ranked_sites",
                    "excel_ranked_sites",
                    "ceo_markdown_report",
                    "draft_unsolicited_proposal_package",
                },
            )
            for path in outputs.values():
                self.assertTrue(Path(path).exists())
            report = Path(outputs["ceo_markdown_report"]).read_text(encoding="utf-8")
            self.assertIn("Florida University P3 Opportunity Report", report)


if __name__ == "__main__":
    unittest.main()
