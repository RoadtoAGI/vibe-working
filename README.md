# Vibe Working

让 AI 在开发、审查与写作中作出有依据的决定，并交付可使用的结果。

Vibe Working 是 RoadtoAGI 维护的开放技能 marketplace。四项技能覆盖规则开发、工程方案选择、中英文表达治理和交付验收，支持 Claude Code 与 Codex。安装一次即可获得全部技能及其 reference、案例、模板和脚本。

## 四项技能

| 技能 | 适合什么任务 | 帮助模型作出什么决定 |
|---|---|---|
| [rule-skill-engineering](plugins/vibe-working/skills/rule-skill-engineering/SKILL.md) | 将文档、经验与案例整理为技能、开发指南或协议 | 找到规则来源、成立条件、权威位置和实际消费者；归并同源规则、划分职责、确定抽象层级，让指导进入执行者的决定 |
| [engineering-value](plugins/vibe-working/skills/engineering-value/SKILL.md) | 实现功能、修复缺陷、设计系统、审计工程方案 | 以目标效果、问题机制和代码圈复杂度成本选择方案、实现位置、范围与验证深度 |
| [aigc-writing-guard](plugins/vibe-working/skills/aigc-writing-guard/SKILL.md) | 中英文说明文、技术文档、商业与学术文本的生成、审阅和修订 | 根据阅读功能识别空泛评价、表演式宣告、模板结构、虚设对手和语域偏移，保留事实、关系与作者意图 |
| [quality-gate](plugins/vibe-working/skills/quality-gate/SKILL.md) | 用户主动发起的一次交付验收 | 查看需求是否漂移、变异代码是否影响单元测试、代码结构是否高效，给出结论和修复单 |

## 方法来源

作者将 **Uncle Bob（Robert C. Martin）** 的编程习惯、社区 AIGC 防治实践与代码审查方法蒸馏为具体的判断工具。Uncle Bob 关于代码职责、架构边界和长期维护的讨论，为工程判断提供了参考；来源见 [The Clean Coder Blog](https://blog.cleancoder.com/)。技能进一步说明这些方法在什么条件下有用、应改变哪项决定、怎样从实际结果判断效果。

中英文表达参考了 [humanizer](https://github.com/blader/humanizer)、[Humanizer-zh](https://github.com/op7418/Humanizer-zh) 和 [stop-slop](https://github.com/hardikpandya/stop-slop)。代码审查借鉴社区审查实践，包括 [Claude Code code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review)。工程取舍结合价值导向软件工程、软件工程经济学和架构成本收益分析；具体依据见 [工程收益理论](plugins/vibe-working/skills/engineering-value/references/engineering-value-theory.md)。

## 知识工程：把经验转成可迁移的指导

技能开发结合 `grill-me` 式追问与作者在实践中总结的规律：追问目标、成立条件和失败原因，找到会改变选择的信息，再决定哪些经验值得成为共享规则。

相同职责与作用域的规则归并到一个权威位置；共同支持一项决定的规则相邻组织；抽象保留对结果起作用的关系和条件，具体规则承载差异。正文放执行当前任务所需的指导，reference 放按情境加载的材料，脚本处理可确定的重复判断。

这套技能提供操作工具包。执行顺序由任务依赖决定，案例用于辨明成立条件，模板用于承载需要交接的结果。`rule-skill-engineering` 会用同样的方法指导模型开发其他技能：从材料找到可执行的决定，检查来源与边界，并确认指导是否进入了最终产物。

可直接复用的工具包括 [规则工作台模板](plugins/vibe-working/skills/rule-skill-engineering/assets/rule-workbench.template.json)、[归并与抽象依据](plugins/vibe-working/skills/rule-skill-engineering/references/abstraction-foundations.md)和[验证形态选择](plugins/vibe-working/skills/engineering-value/references/verification-selection.md)。

## 理论结合实际

实际开发中的失败被整理成少量示例（few-shot），每个案例保留情境、决定性差异与迁移边界。模型从案例学习何时调整判断，再把原理用于当前任务。

| 观察到的现象 | 案例帮助辨明的决定 |
|---|---|
| 过度校验 | 模型是否增加了多余的校验闸门|
| 表演式推理 | 模型总说“我会XXX”，他真的这么做了吗？ |
| 需求漂移 | 新增模块、字段和流程的动机是什么，是否和原始预期一致（我们不需要在番茄炒蛋里加东坡肉） |
| 过度迎合 | 是否出现豆包式的提出质疑就道歉，把用户提示的每一个字都转化成代码加到项目里 |

案例见 [规则开发观察](plugins/vibe-working/skills/rule-skill-engineering/references/observed-cases.md)、[工程观察](plugins/vibe-working/skills/engineering-value/references/observed-cases.md)和[中英文表达的语义判据](plugins/vibe-working/skills/aigc-writing-guard/references/semantic-families.md)。历史项目记录的来源定位见 [SOURCE_NOTES.md](SOURCE_NOTES.md)。

## 安装与订阅

marketplace 是技能目录。添加目录后安装下面的插件，即可加载本仓库的全部技能。

### Claude Code

在终端执行：

```bash
claude plugin marketplace add RoadtoAGI/vibe-working
claude plugin install vibe-working@vibe-working
```

在 Claude Code 会话中，也可执行 `/plugin marketplace add RoadtoAGI/vibe-working`，再通过 `/plugin` 面板安装 `vibe-working@vibe-working`。

插件技能使用插件名前缀：`/vibe-working:<skill-name>`。例如：

```text
/vibe-working:rule-skill-engineering 将这些案例整理为一个有边界的技能。
/vibe-working:engineering-value 选择这个功能的实现范围与验证方式。
/vibe-working:aigc-writing-guard 修订这段技术说明，保留事实和术语。
/vibe-working:quality-gate
```

`quality-gate` 只在明确调用时运行。其余技能根据当前任务范围使用。学术写作的论文库入口属于另行授权的私有学术包；普通文风任务使用本包即可。

更新 marketplace 与插件：

```bash
claude plugin marketplace update vibe-working
claude plugin update vibe-working@vibe-working
```

### Codex

```bash
codex plugin marketplace add RoadtoAGI/vibe-working --ref main
codex plugin add vibe-working@vibe-working
```

安装后开启新会话，用 `$<skill-name>` 显式选择技能，也可用自然语言描述任务。

```bash
codex plugin marketplace upgrade vibe-working
codex plugin add vibe-working@vibe-working
```

本包提供 `.agents/plugins/marketplace.json` 和 `.codex-plugin/plugin.json`；Claude Code 使用 `.claude-plugin/marketplace.json` 与插件内的 `.claude-plugin/plugin.json`。

### ChatGPT 工作区

有插件管理权限的工作区管理员可在 **Admin → Plugins → Add → Import marketplace** 导入 `https://github.com/RoadtoAGI/vibe-working`，Path 留空，分支填 `main`，随后配置插件的可安装策略。此入口受工作区的插件功能与管理员权限控制。

安装格式与管理流程参见 [Claude Code marketplace](https://code.claude.com/docs/en/plugins/create-marketplace) 和 [OpenAI marketplace 管理文档](https://learn.chatgpt.com/docs/enterprise/plugin-management)。

## 目录与运行环境

```text
.agents/plugins/marketplace.json       # Codex marketplace
.claude-plugin/marketplace.json        # Claude Code marketplace
plugins/vibe-working/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  skills/                             # 可调用的技能及配套材料
```

技能正文通过宿主模型执行。配套检查脚本使用 Python 3；`quality-gate` 中的具体测试、变异和质量测量工具根据被审查项目的语言安装，参考它的 `references/tools.md`。包内已带所需脚本；宿主自带的 `skill-creator`、`skill-audit` 或 `code-review` 可配合使用。

## 许可与来源

作者编写的技能、脚本与文档采用 [MIT 许可](LICENSE)，支持使用、修改与再分发。第三方引文及材料保留各自权利。

来源与第三方材料见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)，发行内容见 [SOURCE.json](SOURCE.json)。
