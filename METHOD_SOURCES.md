# 方法来源与开源项目对比

`ai-writing-risk-review` 不是下列项目的拼装或复刻。它对七个代表性开源项目进行能力拆分，重新定义了三套独立证据：可观察表达、创作贡献和证据归属。

| 项目 | 项目类型 | 本项目吸收的方法启发 | 没有继承的结论 |
|---|---|---|---|
| [blader/humanizer](https://github.com/blader/humanizer) | Agent Skill | 公开列举 AI 写作模式、保护事实、局部处理文本 | 不把模式命中当作 AI 来源证明，不默认全文改写 |
| [keez97/humanizer](https://github.com/keez97/humanizer) | Agent Skill + 评分脚本 | 分层检查、区分写作质量与检测器判定、公开能力限制 | 不复用其规则文本、评分代码或检测器结论 |
| [DetectGPT](https://github.com/eric-mitchell/detect-gpt) | 研究实现 | 来源检测依赖特定概率模型与实验条件 | 不把概率曲率改写成通用 AI 概率 |
| [Fast-DetectGPT](https://github.com/baoguangsheng/fast-detect-gpt) | 研究实现 | 更高效的零样本检测仍依赖采样模型、评分模型与环境 | 不把模型分数用于文章价值或创作贡献判断 |
| [Binoculars](https://github.com/ahans30/Binoculars) | 研究实现 | 双模型零样本检测及固定阈值的适用边界 | 不把全局阈值当作跨语言、跨模型通用裁决 |
| [RAID](https://github.com/liamdugan/raid) | 检测基准 | 检测器必须面对多模型、多文体和扰动条件评估 | 不把 benchmark 当作改稿工具或单篇来源结论 |
| [text-dedup](https://github.com/ChenghaoMou/text-dedup) | 去重工具 | 精确匹配、MinHash、SimHash 等可提供重复证据 | 不把相似直接等同于低价值、抄袭或缺少作者立场 |

## 为什么选这七个

公开仓库中还有大量 humanizer、提示词集合和 voice profile 变体。首版没有按 Star 数堆项目，而是选择能覆盖四种不同能力的代表样本：

1. 两个写作形态 Skill；
2. 三种零样本检测路线；
3. 一个跨模型、文体和攻击的检测基准；
4. 一个可提供重复证据的文本去重工具。

这种选法用于回答“每类工具究竟解决什么”，不用于评选唯一最佳项目。

## 自有方法边界

本项目独立编写三层十五维评分、HCE 保护清单、finding 合同、三项中性证据门、Profile 和局部确认式改写流程。第三方作者不为本项目背书；本项目也不声称复现论文结果。

