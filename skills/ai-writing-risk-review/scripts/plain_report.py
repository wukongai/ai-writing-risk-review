"""Plain-language presentation; judgments remain in review_contract."""
from __future__ import annotations

LAYER_NAMES = {
    "ai_text_trace": "表达自然度",
    "creative_contribution": "创作充实度",
    "evidence_attribution": "证据清晰度",
}
DIMENSION_NAMES = {
    "formulaic_phrasing": "模板句式",
    "rhetorical_symmetry": "机械对称",
    "uniform_section_rhythm": "章节节奏过齐",
    "over_smoothed_reasoning": "推理过度顺滑",
    "generic_abstraction": "空泛抽象",
    "weak_original_increment": "原创增量不足",
    "repetition_and_padding": "重复填充",
    "assembly_or_repackaging": "材料拼装",
    "weak_decision_ownership": "判断归属不清",
    "missing_process_or_method": "过程与方法缺口",
    "weak_source_traceability": "来源追溯缺口",
    "citation_or_attribution_gap": "引用归属缺口",
    "fact_opinion_blurring": "事实观点混淆",
    "unsupported_human_claim": "真人贡献依据不足",
    "reuse_or_similarity_risk": "复用相似风险",
}
LEVEL_NAMES = {"low": "低", "medium": "中", "high": "高", "not_issued": "未评分"}
INPUT_NAMES = {
    "source_materials": "原始来源材料",
    "comparison_corpus": "可比较文章",
    "recent_publications": "近期公开文章",
    "external_detector_signals": "外部检测器结果",
    "confirmed_human_evidence": "作者确认的创作证据",
    "platform_policy_snapshot": "平台规则快照",
}


def plain_sections(report: dict) -> dict[str, str]:
    """Derive presentation only from the selected, validated report fields."""
    results = report.get("layer_results", {})
    findings = [f for f in report.get("findings", []) if f.get("layer") in results]
    ordered = sorted(findings, key=lambda f: (f.get("severity", "P3"), f.get("finding_id", "")))
    overview = ["| 维度 | 健康分 | 风险 | 置信度 |", "|---|---|---|---|"]
    details = []
    for layer, panel in results.items():
        name = LAYER_NAMES[layer]
        issued = panel.get("score_status") == "issued"
        score = f"{10 - panel['risk_score']}/10" if issued else "未评分"
        risk = LEVEL_NAMES.get(panel.get("risk_level"), "未评分")
        confidence = LEVEL_NAMES.get(panel.get("confidence"), "未知")
        overview.append(f"| {name} | {score} | {risk} | {confidence} |")
        local = [f for f in ordered if f.get("layer") == layer]
        details.extend([f"### {name}", "", f"现在怎么样：{score}；风险{risk}。", "",
                        "为什么：" + ("；".join(f["claim"] for f in local) if local
                                      else "本次未记录满足问题门槛的具体发现；不代表已证明没有问题。"), "",
                        "直接怎么改：" + ("；".join(f["local_calibration"] for f in local)
                                           if issued and local else
                                           "先由作者核验停止原因，不自动修改。" if not issued else
                                           "保留现有表达，不为提高分数强行改写。"), "",
                        f"判断限制：{panel.get('limitation', '')}", "",
                        "| 细项 | 风险分（0—2，越低越好） |", "|---|---|"])
        for dimension, value in panel.get("scores", {}).items():
            details.append(f"| {DIMENSION_NAMES.get(dimension, dimension)} | {value if issued else '未评分'} |")
        details.append("")
    priorities = [
        f"{i}. **{f['finding_id']} · {f['claim']}**：{f['local_calibration']}（需先核对：{f['fact_dependency']}）"
        for i, f in enumerate(ordered[:3], 1)
    ]
    questions = list(dict.fromkeys(f["fact_dependency"] for f in ordered if f.get("fact_dependency")))
    if report.get("unused_inputs"):
        questions.append("本次未使用：" + "、".join(INPUT_NAMES.get(v, v) for v in report["unused_inputs"]))
    stopped = any(p.get("score_status") != "issued" for p in results.values())
    summary = ("有检查层尚不能评分，先核验对应证据。" if stopped else
               f"本次记录 {len(findings)} 项待核对问题，按下方优先动作逐条确认。" if findings else
               "本次未记录满足证据门槛的问题；结论仅限当前输入与所选检查层。")
    return {
        "plain_summary": summary,
        "health_overview": "\n".join(overview),
        "priority_actions": "\n".join(priorities) or "没有可排序的问题，不生成凑数修改。",
        "plain_layers": "\n".join(details),
        "author_questions": "\n".join("- " + q for q in questions) or "当前问题记录没有新增补充要求。",
    }
