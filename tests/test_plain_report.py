from pathlib import Path
import importlib.util

p = Path(__file__).resolve().parents[1] / "skills/ai-writing-risk-review/tests/test_plain_report.py"
spec = importlib.util.spec_from_file_location("portable_plain_report_tests", p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PlainReportTest = module.PlainReportTest
