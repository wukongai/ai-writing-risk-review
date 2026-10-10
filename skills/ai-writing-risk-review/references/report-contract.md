# 三层报告合同

## Manifest v1

ai-writing-risk-review-manifest/v1 绑定运行、候选版本、文档来源、SHA、连续行数组、review_scope、运行上下文、Profile 快照和可选比较语料。默认 review_scope 为读者可见正文；不得用运营 frontmatter 推断其他 Skill 的发布状态，也不得写死公众号或其他平台。

## Human Creation Evidence

每项使用 HCE-###，包含当前快照锚点、最短原文和保留理由。它只用于保护真实内容和表达资产，不降低任何层的风险分。

## Finding v1

- AIT-### 属于 ai_text_trace；
- CCR-### 属于 creative_contribution；
- EAR-### 属于 evidence_attribution；
- scope 为 document 或 corpus；
- 必须包含锚点、最短原文、风险机制、局部方向、保护证据、事实依赖和复检条件；
- 必须声明 expression_device；非 none 时，neutral_gate_evidence 三项必须全部成立。

## Report v1

ai-writing-risk-review-report/v1 使用 layer_results，且只能包含 manifest 中选择的层。每层包含五维分、独立风险分、风险等级、置信度和限制。

报告还包含 HCE 清单、findings、证据覆盖、未使用输入和 utility_claim=not_evaluated。禁止 overall_score、旧聚合分、AI 来源概率、平台通过率、账号权重、抄袭定罪、规避建议和效果保证。

## Patch Proposal v1

提案绑定 SHA、用户选择的 finding 和 HCE，并逐项记录行范围、exact before、after、事实依赖及保护证据。校验器拒绝 apply_all、整篇范围、未选择 finding、SHA 漂移、before 失配和缺少保护字段。

校验通过只表示提案结构有效，不授权修改原文、安装、同步或发布。

## v0.2.0 默认展示

默认模板先输出完整中文体检，再输出完整依据。健康概览使用表格，避免依赖特定宿主图表插件；最多三项优先动作只来源于已登记 finding。每层解释包含现状、问题依据、局部方向、限制和五项风险分。未选择层不输出。P0 时 risk_score 为 null，risk_level 和 score_status 为 not_issued。

健康分仅在渲染时计算，不改变 JSON 内部风险字段。历史报告不自动改版本；重新评审须重新生成 manifest。模板仅替换一次，文章中的双花括号不作为指令执行。
