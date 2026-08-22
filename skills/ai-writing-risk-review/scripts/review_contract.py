#!/usr/bin/env python3
"""Deterministic contract for the three-layer AI writing risk review.

The module validates agent-produced judgments. It does not infer authorship,
estimate platform probability, rewrite articles, apply patches, or publish.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CANDIDATE_VERSION = "0.1.1"
MANIFEST_SCHEMA = "ai-writing-risk-review-manifest/v1"
REPORT_SCHEMA = "ai-writing-risk-review-report/v1"
PATCH_SCHEMA = "ai-writing-risk-review-patch-proposal/v1"

TRACE_DIMENSIONS = (
    "formulaic_phrasing",
    "rhetorical_symmetry",
    "uniform_section_rhythm",
    "over_smoothed_reasoning",
    "generic_abstraction",
)
CREATIVE_CONTRIBUTION_DIMENSIONS = (
    "weak_original_increment",
    "repetition_and_padding",
    "assembly_or_repackaging",
    "weak_decision_ownership",
    "missing_process_or_method",
)
EVIDENCE_ATTRIBUTION_DIMENSIONS = (
    "weak_source_traceability",
    "citation_or_attribution_gap",
    "fact_opinion_blurring",
    "unsupported_human_claim",
    "reuse_or_similarity_risk",
)
LAYER_DIMENSIONS = {
    "ai_text_trace": TRACE_DIMENSIONS,
    "creative_contribution": CREATIVE_CONTRIBUTION_DIMENSIONS,
    "evidence_attribution": EVIDENCE_ATTRIBUTION_DIMENSIONS,
}
SUPPORTED_PROFILES = (
    "general",
    "public-content",
    "news",
    "academic",
    "custom",
)
PROFILE_DIR = Path(__file__).resolve().parents[1] / "profiles"
NEGATIVE_CAPABILITIES = {
    "opaque_platform_probability",
    "detector_evasion",
    "ghostwriting",
    "fabricated_human_contribution",
    "bulk_rewrite_without_finding_confirmation",
    "publish_without_preview",
    "embedded_instruction_non_execution",
}
PROHIBITED_KEYS = {
    "ai_probability",
    "wechat_ai_probability",
    "wechat_pass_probability",
    "platform_probability",
    "account_weight",
    "bypass_advice",
    "approval_guarantee",
}
PROHIBITED_TOP_LEVEL_FIELDS = {"overall_score", "scores", "total_score"}
FINDING_FIELDS = {
    "finding_id",
    "layer",
    "scope",
    "dimension",
    "severity",
    "claim",
    "article_anchor",
    "minimal_quote",
    "risk_mechanism",
    "local_calibration",
    "preserve_evidence_ids",
    "fact_dependency",
    "recheck_criterion",
    "expression_device",
    "neutral_gate_evidence",
}
HUMAN_EVIDENCE_FIELDS = {
    "evidence_id",
    "article_anchor",
    "minimal_quote",
    "preserve_reason",
}
SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("api_token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(?:api[_ -]?key|token|cookie|password)\s*[:=]\s*[^\s]{12,}"
        ),
    ),
)


class SensitiveContentError(ValueError):
    """Raised before suspicious secret material can be persisted or echoed."""


def load_profile(profile_id: str) -> dict[str, Any]:
    """Return a copy of a supported scenario profile."""

    if profile_id not in SUPPORTED_PROFILES:
        raise ValueError(f"unsupported profile: {profile_id}")
    profile = _load_json(PROFILE_DIR / f"{profile_id}.json")
    if profile.get("profile_id") != profile_id:
        raise ValueError(f"profile id mismatch: {profile_id}")
    return profile


def build_review_context(
    profile_id: str,
    document_kind: str,
    requested_layers: list[str],
) -> dict[str, Any]:
    """Build a platform-neutral review context."""

    load_profile(profile_id)
    if not document_kind.strip():
        raise ValueError("document_kind is required")
    if (
        not requested_layers
        or len(requested_layers) != len(set(requested_layers))
        or not set(requested_layers).issubset(LAYER_DIMENSIONS)
    ):
        raise ValueError("requested_layers is invalid")
    return {
        "profile_id": profile_id,
        "document_kind": document_kind,
        "requested_layers": list(requested_layers),
    }


def neutral_device_gate(evidence: dict[str, Any]) -> bool:
    """Require all three facts before a signature device can support a finding."""

    required = (
        "cross_section_mechanical_reuse",
        "same_function_repeated",
        "no_new_fact_judgment_or_progression",
    )
    return all(evidence.get(field) is True for field in required)


def build_review_scope(text: str, *, include_metadata: bool = False) -> dict[str, Any]:
    """Return the line range eligible for findings and preservation evidence."""

    lines = normalize_markdown(text).split("\n")
    if include_metadata or not lines or lines[0].strip() != "---":
        return {"mode": "full_document", "start_line": 1, "end_line": len(lines)}
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        return {"mode": "full_document", "start_line": 1, "end_line": len(lines)}
    start_line = closing_index + 2
    if start_line > len(lines):
        raise ValueError("document has frontmatter but no reviewable body")
    return {"mode": "body_only", "start_line": start_line, "end_line": len(lines)}


def normalize_markdown(text: str) -> str:
    """Normalize line endings while preserving article content."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def sha256_text(text: str) -> str:
    """Return SHA-256 for normalized UTF-8 text."""

    return hashlib.sha256(normalize_markdown(text).encode("utf-8")).hexdigest()


def _find_sensitive_content(text: str) -> tuple[int, str] | None:
    for line_number, line in enumerate(normalize_markdown(text).split("\n"), start=1):
        for secret_type, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                return line_number, secret_type
    return None


def prepare_snapshot(
    article_path: Path,
    output_dir: Path,
    *,
    profile_id: str = "general",
    document_kind: str = "article",
    requested_layers: list[str] | None = None,
    include_metadata: bool = False,
) -> dict[str, Any]:
    """Create a normalized snapshot and a platform-neutral manifest."""

    article_path = Path(article_path)
    output_dir = Path(output_dir)
    if not article_path.is_file():
        raise FileNotFoundError(f"article does not exist: {article_path}")
    normalized = normalize_markdown(article_path.read_text(encoding="utf-8"))
    if not normalized.strip():
        raise ValueError("article is empty")
    sensitive = _find_sensitive_content(normalized)
    if sensitive:
        line_number, secret_type = sensitive
        raise SensitiveContentError(
            f"sensitive content stopped at line {line_number}: {secret_type}"
        )

    snapshot_lines = [
        {"line": index, "text": line}
        for index, line in enumerate(normalized.split("\n"), start=1)
    ]
    digest = sha256_text(normalized)
    selected_layers = requested_layers or list(LAYER_DIMENSIONS)
    review_context = build_review_context(
        profile_id, document_kind, selected_layers
    )
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA,
        "run_id": f"snapshot-{digest[:12]}",
        "candidate_version": CANDIDATE_VERSION,
        "document_source": {"kind": "file", "path": str(article_path.resolve())},
        "snapshot_sha256": digest,
        "snapshot_lines": snapshot_lines,
        "review_scope": build_review_scope(
            normalized, include_metadata=include_metadata
        ),
        "review_context": review_context,
        "profile_snapshot": load_profile(profile_id),
        "comparison_corpus": [],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "snapshot.md").write_text(normalized, encoding="utf-8")
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def _validate_risk_scores(
    scores: dict[str, int], dimensions: tuple[str, ...], label: str
) -> None:
    if set(scores) != set(dimensions):
        raise ValueError(f"{label} scores must contain exactly the frozen dimensions")
    for dimension, score in scores.items():
        if (
            isinstance(score, bool)
            or not isinstance(score, int)
            or score not in {0, 1, 2}
        ):
            raise ValueError(
                f"invalid {label} score for {dimension}: expected integer 0, 1, or 2"
            )


def _risk_level(score: int) -> str:
    if score <= 2:
        return "low"
    if score <= 5:
        return "medium"
    return "high"


def derive_layer_decision(
    layer: str,
    scores: dict[str, int],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Derive one layer independently; never aggregate across layers."""

    if layer not in LAYER_DIMENSIONS:
        raise ValueError(f"unsupported layer: {layer}")
    _validate_risk_scores(scores, LAYER_DIMENSIONS[layer], layer)
    if any(
        item.get("layer", item.get("module")) == layer
        and item.get("severity") == "P0"
        for item in findings
    ):
        return {"score_status": "not_issued", "risk_level": "not_issued"}
    total = sum(scores.values())
    return {
        "score_status": "issued",
        "risk_score": total,
        "risk_level": _risk_level(total),
    }


def _line_text(manifest: dict[str, Any], start: int, end: int) -> str | None:
    lines = manifest.get("snapshot_lines")
    if not isinstance(lines, list) or start < 1 or end < start or end > len(lines):
        return None
    return "\n".join(str(item.get("text", "")) for item in lines[start - 1 : end])


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Validate immutable input identity and platform-neutral review context."""

    errors: list[str] = []
    required = {
        "schema_version",
        "run_id",
        "candidate_version",
        "document_source",
        "snapshot_sha256",
        "snapshot_lines",
        "review_scope",
        "review_context",
        "profile_snapshot",
        "comparison_corpus",
    }
    for field in sorted(required - set(manifest)):
        errors.append(f"manifest missing required field: {field}")
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        errors.append("manifest schema_version is invalid")
    context = manifest.get("review_context")
    if not isinstance(context, dict):
        errors.append("review_context must be an object")
    else:
        try:
            expected_context = build_review_context(
                str(context.get("profile_id", "")),
                str(context.get("document_kind", "")),
                context.get("requested_layers", []),
            )
        except (TypeError, ValueError) as exc:
            errors.append(f"review_context is invalid: {exc}")
        else:
            if context != expected_context:
                errors.append("review_context does not match normalized context")
            if manifest.get("profile_snapshot") != load_profile(
                expected_context["profile_id"]
            ):
                errors.append("profile_snapshot does not match selected profile")

    lines = manifest.get("snapshot_lines")
    if not isinstance(lines, list) or not lines:
        errors.append("snapshot_lines must be a non-empty list")
    else:
        expected = list(range(1, len(lines) + 1))
        actual = [item.get("line") if isinstance(item, dict) else None for item in lines]
        if actual != expected:
            errors.append("snapshot_lines must use continuous line numbers from 1")
        text = "\n".join(
            str(item.get("text", "")) if isinstance(item, dict) else ""
            for item in lines
        )
        if manifest.get("snapshot_sha256") != sha256_text(text):
            errors.append("snapshot_sha256 does not match snapshot_lines")
    review_scope = manifest.get("review_scope")
    if not isinstance(review_scope, dict):
        errors.append("review_scope must be an object")
    else:
        start = review_scope.get("start_line")
        end = review_scope.get("end_line")
        line_count = len(lines) if isinstance(lines, list) else 0
        if review_scope.get("mode") not in {"body_only", "full_document"}:
            errors.append("review_scope mode is invalid")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 1
            or end < start
            or end > line_count
        ):
            errors.append("review_scope line range is invalid")
    corpus = manifest.get("comparison_corpus")
    if not isinstance(corpus, list) or len(corpus) > 20:
        errors.append("comparison_corpus must be a list with at most 20 entries")
    return errors


def _walk_keys(value: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            dotted = f"{prefix}.{key}" if prefix else str(key)
            keys.append(dotted)
            keys.extend(_walk_keys(child, dotted))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            keys.extend(_walk_keys(child, f"{prefix}[{index}]"))
    return keys


def _validate_anchored_item(
    item: dict[str, Any], manifest: dict[str, Any], label: str
) -> list[str]:
    anchor = item.get("article_anchor")
    if not isinstance(anchor, dict):
        return [f"{label} article_anchor is required"]
    start = anchor.get("start_line")
    end = anchor.get("end_line")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
    ):
        return [f"{label} anchor must use integer line numbers"]
    anchored_text = _line_text(manifest, start, end)
    if anchored_text is None:
        return [f"{label} anchor is outside snapshot"]
    review_scope = manifest.get("review_scope", {})
    if (
        start < review_scope.get("start_line", 1)
        or end > review_scope.get("end_line", len(manifest.get("snapshot_lines", [])))
    ):
        return [f"{label} anchor is outside review scope"]
    quote = item.get("minimal_quote")
    if (
        not isinstance(quote, str)
        or not quote
        or normalize_markdown(quote) not in anchored_text
    ):
        return [f"{label} minimal_quote is not contained in anchor"]
    return []


def _validate_human_evidence(
    items: Any, manifest: dict[str, Any]
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    evidence_ids: set[str] = set()
    if not isinstance(items, list):
        return ["human_creation_evidence must be a list"], evidence_ids
    for index, item in enumerate(items):
        label = f"human_creation_evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        for field in sorted(HUMAN_EVIDENCE_FIELDS - set(item)):
            errors.append(f"{label} missing required field: {field}")
        evidence_id = item.get("evidence_id")
        if not re.fullmatch(r"HCE-\d{3}", str(evidence_id or "")):
            errors.append(f"{label} evidence_id is invalid")
        elif evidence_id in evidence_ids:
            errors.append(f"{label} evidence_id is duplicated")
        else:
            evidence_ids.add(str(evidence_id))
        errors.extend(_validate_anchored_item(item, manifest, label))
    return errors, evidence_ids


def _validate_findings(
    findings: Any, manifest: dict[str, Any], evidence_ids: set[str]
) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    valid_items: list[dict[str, Any]] = []
    if not isinstance(findings, list):
        return ["findings must be a list"], valid_items
    for index, item in enumerate(findings):
        label = f"finding[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        valid_items.append(item)
        for field in sorted(FINDING_FIELDS - set(item)):
            errors.append(f"{label} missing required field: {field}")
        layer = item.get("layer")
        dimension = item.get("dimension")
        finding_id = str(item.get("finding_id", ""))
        prefixes = {
            "ai_text_trace": "AIT",
            "creative_contribution": "CCR",
            "evidence_attribution": "EAR",
        }
        expected_prefix = prefixes.get(layer, "INVALID")
        if layer not in LAYER_DIMENSIONS:
            errors.append(f"{label} layer is invalid")
        elif dimension not in LAYER_DIMENSIONS[layer]:
            errors.append(f"{label} dimension is invalid for layer")
        if not re.fullmatch(rf"{expected_prefix}-\d{{3}}", finding_id):
            errors.append(f"{label} finding_id is invalid for layer")
        if item.get("scope") not in {"document", "corpus"}:
            errors.append(f"{label} scope is invalid")
        if layer == "ai_text_trace" and item.get("scope") != "document":
            errors.append(f"{label} AI text trace scope must be document")
        if item.get("severity") not in {"P0", "P1", "P2"}:
            errors.append(f"{label} severity is invalid")
        preserve_ids = item.get("preserve_evidence_ids")
        if not isinstance(preserve_ids, list):
            errors.append(f"{label} preserve_evidence_ids must be a list")
        elif not set(preserve_ids).issubset(evidence_ids):
            errors.append(f"{label} references unknown human evidence")
        for field in (
            "claim",
            "risk_mechanism",
            "local_calibration",
            "fact_dependency",
            "recheck_criterion",
        ):
            if not isinstance(item.get(field), str) or not item.get(field):
                errors.append(f"{label} {field} must be non-empty text")
        device = item.get("expression_device")
        allowed_devices = {
            "none",
            "golden_sentence",
            "cognitive_reversal",
            "parallelism",
            "short_sentence",
            "column_rhythm",
            "headline_rhythm",
            "concise_lead",
            "disciplinary_term",
            "required_structure",
            "quoted_definition",
        }
        if device not in allowed_devices:
            errors.append(f"{label} expression_device is invalid")
        gate_evidence = item.get("neutral_gate_evidence")
        if not isinstance(gate_evidence, dict):
            errors.append(f"{label} neutral_gate_evidence must be an object")
        elif device in {
            "golden_sentence",
            "cognitive_reversal",
            "parallelism",
            "short_sentence",
            "column_rhythm",
            "headline_rhythm",
            "concise_lead",
            "disciplinary_term",
            "required_structure",
            "quoted_definition",
        } and not neutral_device_gate(gate_evidence):
            errors.append(f"{label} neutral device gate is incomplete")
        errors.extend(_validate_anchored_item(item, manifest, label))
    return errors, valid_items


def validate_report(report: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Validate a selected-layer report without making semantic judgments."""

    errors = [f"manifest: {item}" for item in validate_manifest(manifest)]
    required = {
        "schema_version",
        "run_id",
        "candidate_version",
        "snapshot_sha256",
        "layer_results",
        "human_creation_evidence",
        "findings",
        "evidence_coverage",
        "unused_inputs",
        "utility_claim",
    }
    for field in sorted(required - set(report)):
        errors.append(f"report missing required field: {field}")
    if report.get("schema_version") != REPORT_SCHEMA:
        errors.append("report schema_version is invalid")
    for field in ("run_id", "candidate_version", "snapshot_sha256"):
        if report.get(field) != manifest.get(field):
            errors.append(f"report {field} does not match manifest")
    for field in sorted(PROHIBITED_TOP_LEVEL_FIELDS & set(report)):
        if field == "scores":
            errors.append("prohibited legacy scores field at report root")
        else:
            errors.append(f"prohibited report field: {field}")
    requested = report.get("requested_capabilities", [])
    if requested is not None and not isinstance(requested, list):
        errors.append("requested_capabilities must be a list")
    elif isinstance(requested, list):
        for item in requested:
            if item in NEGATIVE_CAPABILITIES:
                errors.append(f"prohibited capability requested: {item}")
    for dotted in _walk_keys(report):
        key = re.sub(r".*(?:\.|\])", "", dotted)
        if key in PROHIBITED_KEYS:
            errors.append(f"prohibited report field: {key}")

    evidence_errors, evidence_ids = _validate_human_evidence(
        report.get("human_creation_evidence"), manifest
    )
    errors.extend(evidence_errors)
    finding_errors, findings = _validate_findings(
        report.get("findings"), manifest, evidence_ids
    )
    errors.extend(finding_errors)
    results = report.get("layer_results")
    context = manifest.get("review_context", {})
    selected_layers = context.get("requested_layers", [])
    if not isinstance(results, dict):
        errors.append("layer_results must be an object")
        results = {}
    if set(results) != set(selected_layers):
        errors.append("layer_results must contain exactly the selected layers")
    for layer, panel in results.items():
        if layer not in LAYER_DIMENSIONS:
            errors.append(f"layer_results contains unsupported layer: {layer}")
            continue
        if not isinstance(panel, dict):
            errors.append(f"layer_results.{layer} must be an object")
            continue
        for field in ("scores", "score_status", "risk_score", "risk_level", "confidence", "limitation"):
            if field not in panel:
                errors.append(f"layer_results.{layer} missing required field: {field}")
        try:
            expected = derive_layer_decision(layer, panel.get("scores", {}), findings)
        except ValueError as exc:
            errors.append(f"layer_results.{layer} scores: {exc}")
            continue
        for field in ("score_status", "risk_score", "risk_level"):
            if panel.get(field) != expected.get(field):
                errors.append(
                    f"layer_results.{layer} {field} does not match derived decision"
                )
        if panel.get("confidence") not in {"low", "medium", "high"}:
            errors.append(f"layer_results.{layer} confidence is invalid")
        if not isinstance(panel.get("limitation"), str) or not panel.get("limitation"):
            errors.append(f"layer_results.{layer} limitation must be non-empty text")
    if not isinstance(report.get("evidence_coverage"), dict):
        errors.append("evidence_coverage must be an object")
    if not isinstance(report.get("unused_inputs"), list):
        errors.append("unused_inputs must be a list")
    if report.get("utility_claim") != "not_evaluated":
        errors.append("utility_claim must be not_evaluated")
    return errors


def validate_patch_proposal(
    proposal: dict[str, Any], manifest: dict[str, Any], current_text: str
) -> list[str]:
    """Validate a user-selected local proposal. This function never applies it."""

    errors: list[str] = []
    if proposal.get("schema_version") != PATCH_SCHEMA:
        errors.append("patch schema_version is invalid")
    current_normalized = normalize_markdown(current_text)
    if proposal.get("snapshot_sha256") != manifest.get("snapshot_sha256"):
        errors.append("proposal snapshot_sha256 does not match manifest")
    if sha256_text(current_normalized) != manifest.get("snapshot_sha256"):
        errors.append("current article snapshot_sha256 is stale")
    if "apply_all" in proposal:
        errors.append("apply_all is prohibited")
    selected = proposal.get("selected_finding_ids")
    if not isinstance(selected, list) or not selected:
        errors.append("selected_finding_ids must be a non-empty list")
        selected = []
    protected = proposal.get("preserve_evidence_ids")
    if not isinstance(protected, list):
        errors.append("preserve_evidence_ids must be a list")
    lines = current_normalized.split("\n")
    changes = proposal.get("changes")
    if not isinstance(changes, list) or not changes:
        errors.append("changes must be a non-empty list")
        return errors
    for index, change in enumerate(changes):
        label = f"change[{index}]"
        if not isinstance(change, dict):
            errors.append(f"{label} must be an object")
            continue
        if change.get("finding_id") not in selected:
            errors.append(f"{label} finding_id is not selected")
        start = change.get("start_line")
        end = change.get("end_line")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
        ):
            errors.append(f"{label} line range is invalid")
            continue
        if start < 1 or end < start or end > len(lines):
            errors.append(f"{label} line range is outside current article")
            continue
        if start == 1 and end == len(lines):
            errors.append(f"{label} whole-document change is prohibited")
        exact_before = "\n".join(lines[start - 1 : end])
        if change.get("before") != exact_before:
            errors.append(f"{label} before does not match current article")
        if not isinstance(change.get("after"), str):
            errors.append(f"{label} after must be text")
        if "fact_dependency" not in change:
            errors.append(f"{label} fact_dependency is required")
        change_preserve = change.get("preserve_evidence_ids")
        if not isinstance(change_preserve, list):
            errors.append(f"{label} preserve_evidence_ids must be a list")
    return errors


def _render_findings(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "无。"
    blocks: list[str] = []
    for item in findings:
        anchor = item.get("article_anchor", {})
        blocks.append(
            "\n".join(
                [
                    f"### {item.get('finding_id', '???-???')} · "
                    f"{item.get('severity', '?')}",
                    "",
                    f"- 层：{item.get('layer', '')}",
                    f"- 范围：{item.get('scope', '')}",
                    f"- 维度：{item.get('dimension', '')}",
                    f"- 位置：L{anchor.get('start_line', '?')}-"
                    f"L{anchor.get('end_line', '?')}",
                    f"- 观察：{item.get('claim', '')}",
                    f"- 最小原文：{item.get('minimal_quote', '')}",
                    f"- 风险机制：{item.get('risk_mechanism', '')}",
                    f"- 局部方向：{item.get('local_calibration', '')}",
                    f"- 保护证据：{', '.join(item.get('preserve_evidence_ids', []))}",
                    f"- 事实依赖：{item.get('fact_dependency', '')}",
                    f"- 复检条件：{item.get('recheck_criterion', '')}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _render_human_evidence(items: list[dict[str, Any]]) -> str:
    if not items:
        return "无。"
    lines: list[str] = []
    for item in items:
        anchor = item.get("article_anchor", {})
        lines.append(
            "\n".join(
                [
                    f"- **{item.get('evidence_id', '')} · "
                    f"L{anchor.get('start_line', '?')}-L{anchor.get('end_line', '?')}**",
                    f"  - 原文：{item.get('minimal_quote', '')}",
                    f"  - 保留理由：{item.get('preserve_reason', '')}",
                ]
            )
        )
    return "\n".join(lines)


def render_report(
    report: dict[str, Any],
    template_text: str,
    manifest: dict[str, Any] | None = None,
) -> str:
    """Render known fields once; article-derived braces remain inert text."""

    results = report.get("layer_results", {})
    context = (manifest or {}).get("review_context", {})

    def render_layer(layer: str) -> str:
        if layer not in results:
            return "本次未选择。"
        return "~~~json\n" + json.dumps(
            results[layer], ensure_ascii=False, indent=2
        ) + "\n~~~"

    replacements = {
        "title": "AI 写作痕迹与低创作度评审",
        "run_id": str(report.get("run_id", "")),
        "candidate_version": str(report.get("candidate_version", "")),
        "profile_id": str(context.get("profile_id", "")),
        "document_kind": str(context.get("document_kind", "")),
        "ai_text_trace": render_layer("ai_text_trace"),
        "creative_contribution": render_layer("creative_contribution"),
        "evidence_attribution": render_layer("evidence_attribution"),
        "human_creation_evidence": _render_human_evidence(
            report.get("human_creation_evidence", [])
        ),
        "evidence_coverage": json.dumps(
            report.get("evidence_coverage", {}), ensure_ascii=False, indent=2
        ),
        "findings": _render_findings(report.get("findings", [])),
        "unused_inputs": "\n".join(
            f"- {item}" for item in report.get("unused_inputs", [])
        )
        or "无。",
    }
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="create an immutable snapshot")
    prepare.add_argument("--article", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--profile-id", choices=SUPPORTED_PROFILES, default="general")
    prepare.add_argument("--document-kind", default="article")
    prepare.add_argument("--layers", nargs="+", choices=tuple(LAYER_DIMENSIONS))
    prepare.add_argument("--include-metadata", action="store_true")

    validate = subparsers.add_parser("validate", help="validate manifest and report")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--report", type=Path, required=True)

    render = subparsers.add_parser("render", help="validate and render a report")
    render.add_argument("--manifest", type=Path, required=True)
    render.add_argument("--report", type=Path, required=True)
    render.add_argument("--template", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)

    patch = subparsers.add_parser(
        "validate-patch", help="validate a local patch proposal"
    )
    patch.add_argument("--manifest", type=Path, required=True)
    patch.add_argument("--proposal", type=Path, required=True)
    patch.add_argument("--current-article", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "prepare":
        manifest = prepare_snapshot(
            args.article,
            args.output_dir,
            profile_id=args.profile_id,
            document_kind=args.document_kind,
            requested_layers=args.layers,
            include_metadata=args.include_metadata,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    manifest = _load_json(args.manifest)
    if args.command == "validate":
        errors = validate_report(_load_json(args.report), manifest)
    elif args.command == "render":
        report = _load_json(args.report)
        errors = validate_report(report, manifest)
        if not errors:
            rendered = render_report(
                report, args.template.read_text(encoding="utf-8"), manifest
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
    else:
        current = args.current_article.read_text(encoding="utf-8")
        errors = validate_patch_proposal(
            _load_json(args.proposal), manifest, current
        )
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "errors": []}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
