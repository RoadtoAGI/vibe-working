# lint 接口

`scripts/aigc_style_lint.py` 只做表层定位：按 [中文模式库](zh-patterns.json) 与 [英文模式库](en-patterns.json) 扫描可见文字，报告命中位置和复核提示。它不读上下文，不判断语义严重度，不删改文本，也不判断作者身份或 AI 概率。运行方式见 [技能入口](../SKILL.md#表层定位)。

## 命中的含义

- 每条命中是一个复核候选，`message` 写的是该候选该问的问题。`family` 与 `rule_id` 对应模式库条目，语义归属以 [高级语义模式](semantic-families.md) 为准：同一表层候选可能属于不同语义模式，由阅读决定。
- `severity` 只排复核顺序。中文库沿用 `high / medium / low`；英文库固定 `low`，并附 `semantic_severity: null`、`auto_action: none`、`scope_status: unclassified`。
- `review_only: true` 表示该规则的合法同形用法很常见，命中只提示重读。
- `min_document_hits` 规则只在整篇命中达到下限时报告，用于“单个合法、成片才是信号”的词项（书面腔否定词、文言副词、轻动词、空泛评价词、“这件事”）。下限是定位阈值，不是合格线。
- `requires_anchor` 规则在同句出现引用、年份或来源标记时不报告。
- 英文 `decision_owner: academic-writing/Authority` 的候选（对比表达）涉及本文相对既有工作的定位，由该技能的作者权限决定处理，lint 不预判作用域。
- `derived_signals` 与 `distribution_signals` 是分布统计：模态词与强化词堆叠、重复段首、英文冒号与破折号密度、分词尾句与词汇痕迹计数。它们只排序复读顺序，不设阈值，不升级严重度。

## 覆盖状态

JSON 固定返回 `coverage.surface_lint: completed`、`semantic_review: not_run`、`overall_review: incomplete`。零命中只说明未发现已注册信号；完整审阅结论必须有实际阅读支持。自动化消费者按这些字段判断报告范围，普通交付不复述它们。

## 退出码

`--fail-on` 默认 `none`。设置阈值后，任何达到该表层优先级的候选（包括 `review_only`）使脚本返回退出码 2；分布统计不参与。该选项用于提醒复核，不能用作自动删句、拒稿或语义不合格门槛。

## 自定义词库

`--patterns FILE` 载入同 schema 的词库，`language` 须与 `--lang` 一致。项目专属词表应作为单独文件维护，不修改技能自带库。新增条目遵循 [更新规则](code-document-register.md#更新规则)：写清字面功能、失配成立条件和改写收益，用相邻正常用法检验触发范围；“听起来像 AI”不进词库。

## 开发检查

```bash
python3 scripts/aigc_style_lint.py --self-test
python3 scripts/test_aigc_style_lint.py
python3 -m json.tool references/zh-patterns.json >/dev/null
python3 -m json.tool references/en-patterns.json >/dev/null
```

`scripts/fixtures/zh-compatibility.json` 冻结中文输出，词库改动后按新行为重新生成并在 `kind` 字段说明；`scripts/fixtures/en-source-cases.json` 与 `zh-source-cases.json` 保存有来源的真实句子，检验程序能否定位候选、能否不把合法同形升级为问题。这些用过的来源不充当独立效果证据。
