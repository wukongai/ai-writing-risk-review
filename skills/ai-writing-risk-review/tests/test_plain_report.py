from pathlib import Path
import sys
import unittest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import review_contract as c


def report_for(layers=None):
    selected = layers or list(c.LAYER_DIMENSIONS)
    return {
        "run_id": "test", "candidate_version": c.CANDIDATE_VERSION,
        "layer_results": {
            layer: {**c.derive_layer_decision(layer, {d: 0 for d in c.LAYER_DIMENSIONS[layer]}, []),
                    "scores": {d: 0 for d in c.LAYER_DIMENSIONS[layer]},
                    "confidence": "medium", "limitation": "仅当前正文"}
            for layer in selected
        },
        "findings": [], "human_creation_evidence": [], "unused_inputs": [],
        "evidence_coverage": {}, "utility_claim": "not_evaluated",
    }


class PlainReportTest(unittest.TestCase):
    def render(self, report):
        return c.render_report(report, (SKILL / "assets/report-template.md").read_text())

    def test_unselected_findings_are_rejected_and_hidden(self):
        r = report_for(["ai_text_trace"])
        r["findings"] = [{
            "finding_id": "EAR-001", "layer": "evidence_attribution",
            "severity": "P2", "dimension": "weak_source_traceability",
            "scope": "document", "claim": "outside selected scope",
            "article_anchor": {"start_line": 1, "end_line": 1},
            "minimal_quote": "test", "risk_mechanism": "test",
            "local_calibration": "test", "fact_dependency": "test",
            "preserve_evidence_ids": [], "recheck_criterion": "test",
            "expression_device": "none", "neutral_gate_evidence": {},
        }]
        text = "test"
        m = {
            "schema_version": c.MANIFEST_SCHEMA, "run_id": "test",
            "candidate_version": c.CANDIDATE_VERSION,
            "document_source": {"kind": "file", "path": "fixture.md"},
            "snapshot_sha256": c.sha256_text(text),
            "snapshot_lines": [{"line": 1, "text": text}],
            "review_scope": c.build_review_scope(text),
            "review_context": c.build_review_context("general", "article", ["ai_text_trace"]),
            "profile_snapshot": c.load_profile("general"), "comparison_corpus": [],
        }
        r.update(schema_version=c.REPORT_SCHEMA, snapshot_sha256=m["snapshot_sha256"])
        errors = c.validate_report(r, m)
        self.assertTrue(any("unselected layer" in error for error in errors), errors)
        self.assertNotIn("EAR-001", self.render(r))

    def test_health_direction_and_detail(self):
        r = report_for()
        scores = r["layer_results"]["creative_contribution"]["scores"]
        scores["weak_original_increment"] = 2
        scores["missing_process_or_method"] = 1
        r["layer_results"]["creative_contribution"].update(
            c.derive_layer_decision("creative_contribution", scores, []))
        text = self.render(r)
        self.assertIn("| 创作充实度 | 7/10 |", text)
        self.assertIn("越高越好", text)
        self.assertIn("过程与方法缺口", text)
        self.assertNotIn("~~~json", text)

    def test_unselected_layers_not_rendered(self):
        text = self.render(report_for(["ai_text_trace"]))
        self.assertIn("表达自然度", text)
        self.assertNotIn("创作充实度", text)
        self.assertNotIn("证据清晰度", text)

    def test_stop_does_not_issue_health_score(self):
        r = report_for(["ai_text_trace"])
        r["layer_results"]["ai_text_trace"].update(
            c.derive_layer_decision("ai_text_trace",
                                   r["layer_results"]["ai_text_trace"]["scores"],
                                   [{"layer": "ai_text_trace", "severity": "P0"}]))
        text = self.render(r)
        self.assertIn("未评分", text)
        self.assertNotIn("10/10", text)
        self.assertIsNone(r["layer_results"]["ai_text_trace"].get("risk_score"))

    def test_source_placeholders_stay_literal(self):
        r = report_for()
        r["run_id"] = "{{candidate_version}}"
        text = c.render_report(r, "{{run_id}} / {{candidate_version}}")
        self.assertEqual(text, "{{candidate_version}} / " + c.CANDIDATE_VERSION)

    def test_no_findings_does_not_invent_actions(self):
        text = self.render(report_for())
        self.assertIn("没有可排序的问题", text)

    def test_action_is_traceable_to_finding(self):
        r = report_for(["creative_contribution"])
        r["findings"] = [{
            "finding_id": "CCR-001", "layer": "creative_contribution", "severity": "P2",
            "dimension": "missing_process_or_method", "claim": "缺少运行例子",
            "article_anchor": {"start_line": 3, "end_line": 3},
            "minimal_quote": "自动完成", "risk_mechanism": "读者无法复核",
            "local_calibration": "补一次真实运行", "preserve_evidence_ids": [],
            "fact_dependency": "实际运行记录", "recheck_criterion": "可复核",
        }]
        text = self.render(r)
        self.assertIn("CCR-001", text)
        self.assertIn("补一次真实运行", text)
        self.assertIn("实际运行记录", text)
        self.assertLess(text.index("优先动作"), text.index("完整依据"))


if __name__ == "__main__":
    unittest.main()
