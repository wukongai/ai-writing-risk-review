# 贡献指南

欢迎提交问题、场景样本、Profile 改进和测试。请遵守以下边界：

1. 不提交包含个人隐私、凭证或未授权原文的样本；
2. 新增 finding 规则时同时提供反例和保护性回归；
3. 不把检测器分数改写为 AI 来源概率；
4. 不加入检测规避、代写、洗稿、伪造引用或经历的能力；
5. 修改后运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/ai-writing-risk-review/scripts/self_test.py
```

Pull Request 请说明：问题、证据、预期行为、负迁移风险和验证结果。

