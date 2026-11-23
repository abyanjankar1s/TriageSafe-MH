import unittest
from pathlib import Path
import yaml



class TestM4Models(unittest.TestCase):
    def test_subject_registry(self):
        config = yaml.safe_load(Path("configs/models.yaml").read_text())
        self.assertEqual(config["subject_models"]["qwen3_4b"]["checkpoint"], "Qwen/Qwen3-4B")

    def test_independent_judge_registry(self):
        config = yaml.safe_load(Path("configs/models.yaml").read_text())
        self.assertEqual(config["judge_models"]["phi35_mini"]["family"], "Phi")

    def test_template_option_guarded(self):
        for filename in ("src/run_models.py", "src/judge_responses.py"):
            code = Path(filename).read_text()
            self.assertIn('if "qwen3" in', code)
            self.assertIn('template_kwargs["enable_thinking"] = False', code)
