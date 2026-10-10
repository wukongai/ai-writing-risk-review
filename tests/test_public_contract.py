from pathlib import Path
import re
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "ai-writing-risk-review"


class PublicContractTest(unittest.TestCase):
    def test_validation_command_is_portable_after_install(self) -> None:
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("tests/skills/author-voice-review", skill_md)
        self.assertIn("{{skill_root}}/scripts/self_test.py", skill_md)

    def test_version_is_synchronized(self) -> None:
        contract = (SKILL_ROOT / "skill.contract.yaml").read_text(encoding="utf-8")
        runtime = (SKILL_ROOT / "scripts" / "review_contract.py").read_text(encoding="utf-8")
        manifest_schema = (SKILL_ROOT / "references" / "schemas" / "manifest.schema.json").read_text(encoding="utf-8")
        report_schema = (SKILL_ROOT / "references" / "schemas" / "report.schema.json").read_text(encoding="utf-8")

        contract_version = re.search(r"^version: ([0-9.]+)$", contract, re.MULTILINE)
        runtime_version = re.search(r'^CANDIDATE_VERSION = "([0-9.]+)"$', runtime, re.MULTILINE)
        self.assertIsNotNone(contract_version)
        self.assertIsNotNone(runtime_version)
        version = contract_version.group(1)
        self.assertEqual(version, runtime_version.group(1))
        self.assertEqual(json.loads(manifest_schema)["properties"]["candidate_version"]["const"], version)
        self.assertEqual(json.loads(report_schema)["properties"]["candidate_version"]["const"], version)


if __name__ == "__main__":
    unittest.main()
