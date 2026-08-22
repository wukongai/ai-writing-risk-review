# AI Writing Risk Review

一个面向普通文章、公开内容、新闻、报告和论文草稿的 Agent Skill。它分别检查：

1. AI 文本形态：模板句式、机械对称、节奏过齐、过度顺滑和空泛抽象；
2. 创作贡献：原创增量、重复填充、材料拼装、判断归属和过程方法；
3. 证据归属：来源追溯、引用归属、事实与观点、人类贡献和复用相似。

三层分别评分、分别结论，不计算综合总分。它不判断文本一定由谁生成，不承诺通过 AI 检测、查重或平台审核。

## 安装

```bash
npx skills add wukongai/ai-writing-risk-review
```

安装后可直接告诉 Agent：

```text
用 ai-writing-risk-review 完整评审这篇文章，先只诊断，不要改原文。
```

也可以只运行一层：

```text
只检查 AI 文本形态。
只检查创作贡献和资料拼接风险。
按新闻模式检查来源、引语和事实/观点边界。
按学术模式检查引用与作者贡献，不代写。
```

## 安全边界

- 默认只诊断；用户逐条选择 finding 后才展示局部修改提案。
- 不编造事实、引用、采访、经历、研究或作者贡献。
- 不提供检测规避、洗稿、代写或绕过平台规则的方法。
- 公开内容默认只评读者可见正文，操作性 frontmatter 不进入 finding。
- 金句、认知反转、排比和短句只有同时通过三项中性证据门才可形成 finding。

## Profile

- `general`：普通文章、博客和报告；
- `public-content`：公众号、自媒体和其他公开内容；
- `news`：新闻与资讯；
- `academic`：论文草稿与研究综述；
- `custom`：用户可自行调整关注层和保护表达。

## 当前验证状态

- 合同、Schema、脚本和边界回归已通过自动测试；
- `public-content` 已完成真实文章回归；
- `news` 与 `academic` 已完成结构测试，尚不宣称跨场景真实效用已经充分验证。

方法来源见 [METHOD_SOURCES.md](METHOD_SOURCES.md)，第三方许可边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

