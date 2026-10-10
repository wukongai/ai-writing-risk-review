#!/usr/bin/env python3
"""Portable self-test for the platform-neutral three-layer candidate."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import review_contract as contract

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    article = (ROOT / "tests/fixtures/self-test-article.md").read_text(
        encoding="utf-8"
    )
    normalized = contract.normalize_markdown(article)
    lines = [
        {"line": index, "text": line}
        for index, line in enumerate(normalized.split("\n"), start=1)
    ]
    context = contract.build_review_context(
        "general",
        "article",
        [
            "ai_text_trace",
            "creative_contribution",
            "evidence_attribution",
        ],
    )
    manifest = {
        "schema_version": contract.MANIFEST_SCHEMA,
        "run_id": "self-test-run",
        "candidate_version": contract.CANDIDATE_VERSION,
        "document_source": {
            "kind": "file",
            "path": "tests/fixtures/self-test-article.md",
        },
        "snapshot_sha256": contract.sha256_text(normalized),
        "snapshot_lines": lines,
        "review_scope": contract.build_review_scope(normalized),
        "review_context": context,
        "profile_snapshot": contract.load_profile("general"),
        "comparison_corpus": [],
    }
    scores = {
        layer: {dimension: 0 for dimension in dimensions}
        for layer, dimensions in contract.LAYER_DIMENSIONS.items()
    }
    scores["evidence_attribution"]["weak_source_traceability"] = 1
    finding = {
        "finding_id": "EAR-001",
        "layer": "evidence_attribution",
        "scope": "document",
        "dimension": "weak_source_traceability",
        "severity": "P2",
        "claim": "运行失败缺少可复核标识。",
        "article_anchor": {"start_line": 3, "end_line": 3},
        "minimal_quote": "自动流程在缺少来源日期的情况下仍生成了结论",
        "risk_mechanism": "核心失败事实缺少可复核来源。",
        "local_calibration": "有真实记录时补日期或标识；没有则声明未保存。",
        "preserve_evidence_ids": ["HCE-001"],
        "fact_dependency": "用户确认是否有可公开运行记录",
        "recheck_criterion": "不新增虚构记录，失败与修正事实仍完整。",
        "expression_device": "none",
        "neutral_gate_evidence": {},
    }
    report = {
        "schema_version": contract.REPORT_SCHEMA,
        "run_id": manifest["run_id"],
        "candidate_version": manifest["candidate_version"],
        "snapshot_sha256": manifest["snapshot_sha256"],
        "layer_results": {
            layer: {
                **contract.derive_layer_decision(layer, layer_scores, [finding]),
                "scores": layer_scores,
                "confidence": "medium",
                "limitation": "只诊断可观察风险，不判断文本来源。",
            }
            for layer, layer_scores in scores.items()
        },
        "human_creation_evidence": [
            {
                "evidence_id": "HCE-001",
                "article_anchor": {"start_line": 3, "end_line": 3},
                "minimal_quote": "第一次演练时",
                "preserve_reason": "具体失败过程和修正决定必须保留。",
            }
        ],
        "findings": [finding],
        "evidence_coverage": {"sections_reviewed": 2, "sections_total": 2},
        "unused_inputs": ["source_materials", "comparison_corpus"],
        "utility_claim": "not_evaluated",
    }

    errors = contract.validate_report(report, manifest)

    rejected_capability = copy.deepcopy(report)
    rejected_capability["requested_capabilities"] = ["detector_evasion"]
    capability_errors = contract.validate_report(rejected_capability, manifest)
    if not any("detector_evasion" in item for item in capability_errors):
        errors.append("detector evasion capability was not rejected")

    rejected_gate = copy.deepcopy(report)
    rejected_gate["findings"][0]["expression_device"] = "cognitive_reversal"
    rejected_gate["findings"][0]["neutral_gate_evidence"] = {
        "cross_section_mechanical_reuse": True,
        "same_function_repeated": True,
        "no_new_fact_judgment_or_progression": False,
    }
    gate_errors = contract.validate_report(rejected_gate, manifest)
    if not any("neutral device gate" in item for item in gate_errors):
        errors.append("incomplete neutral device gate was not rejected")

    proposal = {
        "schema_version": contract.PATCH_SCHEMA,
        "snapshot_sha256": manifest["snapshot_sha256"],
        "selected_finding_ids": ["EAR-001"],
        "preserve_evidence_ids": ["HCE-001"],
        "changes": [
            {
                "finding_id": "EAR-001",
                "start_line": 3,
                "end_line": 3,
                "before": lines[2]["text"],
                "after": lines[2]["text"],
                "fact_dependency": "用户确认是否有可公开运行记录",
                "preserve_evidence_ids": ["HCE-001"],
            }
        ],
    }
    patch_errors = contract.validate_patch_proposal(proposal, manifest, normalized)
    errors.extend(patch_errors)

    rendered = contract.render_report(report, (ROOT / "assets/report-template.md").read_text(), manifest)
    plain_ok = "| 证据清晰度 | 9/10 |" in rendered and "优先动作" in rendered
    if not plain_ok:
        errors.append("plain report health presentation failed")

    payload = {
        "version": contract.CANDIDATE_VERSION,
        "ok": not errors,
        "checks": {
            "plain_report_rendered": plain_ok,
            "valid_three_layer_report": not contract.validate_report(report, manifest),
            "detector_evasion_rejected": bool(capability_errors),
            "neutral_device_gate_enforced": bool(gate_errors),
            "local_patch_shape_valid": not patch_errors,
        },
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
