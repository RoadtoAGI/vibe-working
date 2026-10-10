# 代码文档语域

本页提供代码设计文档、软件验证报告和 agent 执行规范的源语域样本、候选词项和修订映射。跨域判定、强度和局部边界统一见 [代码文档文风跨域污染](semantic-families.md#代码文档文风跨域污染-code_document_register_leakage)，内容保护遵循 [技能入口](../SKILL.md#共同约束)。

## 源语域

代码与 agent 文档用以下结构描述真实机器和工程流程：

- **状态与转换**：state machine、terminal state、状态转换、停止条件；
- **准入与阻断**：gate、hard gate、fail-closed、blocking finding；
- **验证与追踪**：verify、audit trail、evidence chain、traceability matrix；
- **失败处理**：fallback、rollback、degrade、failure path；
- **权威与契约**：single source of truth、SSOT、contract、acceptance criteria；
- **执行生命周期**：plan、execute、verify、review、ship、stop；
- **文档结构**：字段标签、枚举状态、版本名、通过/阻断结论。

这些词在代码文档中指向可执行对象。例如，hard gate 可以对应退出码和下一阶段，stop condition 可以对应循环终止表达式，fallback 可以对应实际备用实现。

公开社区项目中的字面样本：

- [Agent Brain](https://github.com/rohitg00/agentbrain) 使用 state machine、required artifacts、stop conditions 和 proof gates 描述 agent 生命周期。
- [FuguNano workflow](https://github.com/BicaMindLabs/FuguNano/blob/main/docs/WORKFLOW.md) 将 hard gate 对应为可执行 barrier；未满足时禁止进入下一阶段。
- [GSA Agentic Coding Playbook](https://github.com/GSA-TTS/agentic-coding-playbook) 使用 single source of truth、fallback cache 和 fail-closed check 描述真实文件与检查行为。
- [loopkit-b](https://github.com/hhamja/loopkit-b) 使用 PLAN、EXECUTE、VERIFY、STOP 状态机及机器强制限制。
- [agent-execution-harness](https://github.com/lordaeternus/agent-execution-harness) 定义 init、preflight、gate、evidence、completed、halt 等运行状态。

## 跨域污染的表层信号

### 复合治理名目

`准确性硬刹车`、`盲区审计`、`风险扫描`、`证据盘点`、`质量闸门`、`路线版`。

这些名称模拟工具、检查器或交付版本。正文没有对应工具、输入、输出和执行者时，名称只增加程序感。

### 字段化人物与事实

`已验证能力：`、`未验证判断：`、`实际任务：` 等标签把连续叙述改造成 schema 字段。判断重点是整段功能；单独使用“已验证”不自动构成问题。

`已知状态与使用边界`、`当前状态与应用范围` 等标题可将普通事实表包装成系统状态与接口范围。确定存在语域错位后，从所辖内容提炼领域标题，例如客户事实表可用“客户概况”，身体活动说明可用“步行条件”；完整命名判断见 [章节标题套式](semantic-families.md#章节标题套式-formulaic_heading)。

### 封闭程序分支

`只保留两个选择`、`没有第三条方案`、`除非出现真正的新证据`。这类句式把现实建议写成穷举分支和状态转换。领域事实只能支持当前判断时，应写“目前可行的安排”和重新评估条件。

### 失败处理借词

`兜底`、`fallback`、`降级路径`、`回退路径`。在生活或医学建议中，应直接写备用的人、车辆、设备、药物、机构或取消安排。

### 执行过程与版本泄漏

`我调用了你要求的审计`、`按上一版执行`、`不再出路线版`。这些语句暴露模型如何处理提示词和管理产物；删除后直接陈述事实与建议。

## 修订映射

仅在上下文已确认语域失配后参考下表。先理解原句所承载的对象、条件和后果，再组织自然的目标表达；字面术语和有用标题保持。表中写法不能作为逐词替换表，改写后按入口的阅读保真复读句段。

| 代码文档文风 | 目标领域写法 |
|---|---|
| 准确性硬刹车 / 盲区审计 | 删除名目，直接写现有信息不足及遗漏事实 |
| 已验证能力 / 未验证判断 | 连续陈述已经发生的事和未经验证的判断 |
| 当前状态与应用范围 | 按所辖内容提炼领域标题，保留必要对象和条件 |
| 硬闸门 | 准入条件、否决条件、审批条件；按领域选择 |
| 停止条件 | 研究中止标准、治疗停止标准、项目终止条件 |
| 状态机 | 只有真实有限状态与转换时保留；否则写阶段变化 |
| SSOT | 写明以哪份数据库、记录、政策或文件为准 |
| 兜底 / fallback | 写明具体备用人员、资源、设备或取消安排 |
| 只保留两个选择 | 目前可行的安排有；分别写成立条件 |
| 真正的新证据 | 写明哪些新信息会改变当前判断 |
| 路线版 / 执行版 | 删除版本包装，直接给方案 |

## 更新规则

社区代码文档用于发现源语域词项。用户反例提供跨域失配的候选证据，判定仍依据上下文中的对象和用途。新增词项需写清其字面功能、失配成立条件及改写收益，并用相邻正常用法检验触发范围；同形的正常表达不进入问题域。单纯“听起来像 AI”不进入词库。
