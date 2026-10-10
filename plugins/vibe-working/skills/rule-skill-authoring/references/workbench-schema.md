# 规则工程工作台 Schema

工作台记录知识到规则再到 skill 的可追溯编译过程。它是开发期证据，不是目标 skill 的运行时依赖。

## 顶层结构

```json
{
  "schema_version": "1.0",
  "phase": "draft",
  "target": {},
  "sources": [],
  "rules": [],
  "clusters": [],
  "placements": [],
  "checks": []
}
```

| 字段 | 约束 | 含义 |
|---|---|---|
| `schema_version` | 固定为 `1.0` | 校验器契约版本 |
| `phase` | `draft` 或 `final` | 是否已完成全部验收 |
| `target` | 对象 | 目标 skill 的事务边界 |
| `sources` | 非空数组 | 来源与权威台账 |
| `rules` | 非空数组 | 原子规则和抽象规则 |
| `clusters` | 数组 | 归并、聚类和抽象裁决 |
| `placements` | 数组 | 每条规则的唯一权威位置 |
| `checks` | 数组 | 验收状态与证据 |

## `target`

| 字段 | 类型 | 含义 |
|---|---|---|
| `name` | 非空字符串 | 目标 skill 名称 |
| `purpose` | 非空字符串 | 一句话决策目标 |
| `deliverable` | 非空字符串 | 该事务产生的主要产物 |
| `owner` | 非空字符串 | 对规则和产物负责的唯一模块 |
| `consumers` | 非空字符串数组 | 直接消费产物的角色或模块 |

若 `purpose` 必须列出多个独立决策目标，先做模块边界诊断。

## `sources[]`

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | 唯一非空字符串 | 来源标识，如 `S-001` |
| `kind` | 枚举 | `primary_authority`、`project_rule`、`user_requirement`、`existing_artifact`、`design_choice` |
| `locator` | 非空字符串 | 文件、章节、URL、消息或其他可复查定位 |
| `authority` | 非空字符串 | 该来源在当前任务中能决定什么 |
| `claims` | 非空字符串数组 | 该来源实际支持的命题 |

`existing_artifact` 证明当前状态；`design_choice` 记录工程选择。两者不能冒充外部原始权威。

## `rules[]`

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | 唯一非空字符串 | 规则标识，如 `R-001` |
| `decision` | 非空字符串 | 这项规则控制的单一决策 |
| `trigger` | 非空字符串 | 适用条件 |
| `action` | 非空字符串 | 执行动作 |
| `acceptance` | 非空字符串 | 可观察验收信号 |
| `rationale` | 非空字符串 | 最小必要依据 |
| `authority` | 非空字符串 | 谁能定义或推翻它 |
| `scope` | 非空字符串 | 适用对象、阶段和边界 |
| `owner` | 非空字符串 | 唯一责任模块 |
| `strength` | 枚举 | `hard_constraint`、`execution_strategy`、`heuristic` |
| `source_ids` | 非空唯一字符串数组 | 指向 `sources[].id` |
| `status` | 枚举 | `active`、`absorbed`、`supporting`、`discarded` |
| `replaced_by` | 字符串或 `null` | `absorbed` 时指向生效规则 |
| `depends_on` | 唯一字符串数组 | 指向前置 `rules[].id` |
| `exceptions` | 字符串数组 | 独立授权或明确状态覆盖产生、会改变动作或判据的真实例外；通常为空，非触发边界写入 `trigger` / `scope` |

状态语义：

- `active`：作为独立规则发布；
- `absorbed`：与另一规则等价，被 `replaced_by` 吸收；
- `supporting`：保留为上层不变量的条件、实现、非触发边界或真实例外；
- `discarded`：无依据、无行为价值或纯机械复述，不进入运行时。

`absorbed` 必须填写 `replaced_by`；其他状态的 `replaced_by` 应为 `null`。

## `clusters[]`

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | 唯一非空字符串 | 聚类标识 |
| `member_rule_ids` | 至少两个唯一规则 ID | 被比较的规则 |
| `relation` | 枚举 | `equivalent`、`shared_invariant`、`adjacent` |
| `decision` | 枚举 | `merge`、`abstract`、`keep_separate` |
| `result_rule_id` | 字符串或 `null` | 归并后的规则或抽象出的父规则 |
| `invariant` | 字符串或 `null` | `shared_invariant` 时写稳定不变量 |
| `rationale` | 非空字符串 | 裁决依据，包含保留的差异 |

合法组合：

| `relation` | `decision` | 额外要求 |
|---|---|---|
| `equivalent` | `merge` | `result_rule_id` 指向有效规则 |
| `shared_invariant` | `abstract` | `result_rule_id` 有效；`invariant` 非空 |
| `adjacent` | `keep_separate` | `result_rule_id` 与 `invariant` 为 `null` |

## `placements[]`

每条规则恰好有一个 placement，避免出现多个完整权威源。

| 字段 | 类型 | 含义 |
|---|---|---|
| `rule_id` | 唯一规则 ID | 被归位的规则 |
| `surface` | 枚举 | `frontmatter`、`skill_body`、`reference`、`script`、`project_rule`、`project_doc`、`discarded` |
| `locator` | 非空字符串 | 目标文件与章节、脚本或文档位置 |
| `reason` | 非空字符串 | 频率、执行面和 owner 如何支持该位置 |

`discarded` 规则只能放在 `discarded`；其他规则不得放在 `discarded`。`absorbed` 规则的 locator 应说明其被哪条规则吸收，不在运行时保留第二份正文。

## `checks[]`

固定检查名：

| `name` | 验证对象 |
|---|---|
| `authority_traceability` | 有效规则都能追溯到支持其命题的来源 |
| `rule_closure` | 规则具备触发、动作、验收和依据 |
| `merge_safety` | 合并项语义等价，差异没有被误删 |
| `abstraction_preservation` | 上层不变量保留子规则条件、非触发边界和真实例外 |
| `ssot_uniqueness` | 每条规则只有一个完整定义位置 |
| `runtime_reachability` | 直接消费者能在需要时加载规则 |
| `structural_validation` | frontmatter、目录、链接和脚本结构有效 |
| `behavior_positive` | 目标任务产生预期决策和产物 |
| `behavior_boundary` | 相邻任务不会误触发或越权 |
| `behavior_conflict` | 冲突、真实授权或状态覆盖、降级路径按权限和边界裁决 |

每项结构：

```json
{
  "name": "rule_closure",
  "status": "pass",
  "evidence": ["R-001 包含 trigger/action/acceptance/rationale"]
}
```

`status` 可取 `open`、`pass`、`fail`、`not_applicable`。`final` 阶段不得保留 `open` 或 `fail`；每项都要有可复查 evidence。`not_applicable` 的 evidence 必须说明为何不适用。

## 校验阶段

开发中运行：

```bash
python3 scripts/validate_rule_workbench.py path/to/rule-workbench.json
```

它检查字段、枚举、ID 引用、cluster 裁决组合、placement 唯一性和检查项完整性。

全部验证完成后把 `phase` 改为 `final`，运行：

```bash
python3 scripts/validate_rule_workbench.py --final path/to/rule-workbench.json
```

`--final` 还会要求所有固定检查均为 `pass` 或有证据的 `not_applicable`。校验器证明工作台结构和声明闭合；实际命令输出、文件内容和行为产物仍需人工或测试复核。
