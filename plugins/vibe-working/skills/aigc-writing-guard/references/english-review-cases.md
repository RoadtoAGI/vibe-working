# 英文候选的阅读功能与权限边界

英文词句由[模式库](en-patterns.json)定位，语义判断沿用[信息冗余、语义指向和文体组织](semantic-families.md)。这些真实来源用于看清判别条件；词频和句式命中均不能单独决定修法。学术惯例由 `academic-writing` 负责；定位、主张和结果冲突由其 Authority 负责。

## C15 Colons and entry rewriting

MUSE 的 YXC 批注稿 p.1 以如下工程类比进入引言：

> Agentic code generation crossed from demonstration to daily tool when harnesses made long-running model behavior stateful, inspectable, and correctable (Yang et al. 2024): explicit contracts state what each step must satisfy, persistent state records what the run has committed to, and verification decides when to retry.

YXC-10 指出“尽量少用冒号”；YXC-14 要求全文检查可替换的冒号。当前 `main-en.md` L11 从任务进入：

> Story generation brings together problems of computational creativity and practical support for human writers. A writing request can specify a genre, character relationships, required events, and a desired prose style; the resulting work must fulfill these requirements in a coherent reading experience

两段同时改变了主线、内容和句法。它们保留了明确的阅读反馈与实际重写，但不能作为“仅替换冒号即可改善文字”的修复对。旧统计17.5→7.6次/千词同样只提供分布线索；这里不将该比率设为阈值。

相邻合法用法来自同一现稿 L63：

> The scene plans in this trace use a *beat contract* to specify the intended value transition and the pressure that drives it:

下一项即为公式。冒号负责引出定义；替换标点必须保持这项功能。lint 把这类冒号计入描述性统计，但不会据此产生问题命中。

来源：B1 的真实对照及边界（历史来源：`oran-suite/oranai/oransim-dev/docs/level-3-implementation/research/academic-writing/B1/accepted-repairs.md:274`），原批注与完整坐标在同目录 `muse-annotations.json`。原PDF合并换行与行末断词，当前片段保留源稿措辞。贡献起句 `Our contributions:` 的具体层级修复由 [academic-story 的 MUSE 贡献案例](https://github.com/RoadtoAGI/academic-writing-skills/blob/main/plugins/academic-writing-suite/skills/academic-story/references/reader-navigation-cases.md#c10-muse-consolidate-contribution-levels)承接，不能推广成冒号禁令。

## 具体挑战与空宣告的区别

AnnaAgent 摘要明确写出：

> two key challenges: dynamic evolution and multi-session memory.

随后说明咨询中的心理状态变化和多会谈需求，分别介绍情绪调节/主诉诱导组件与三层记忆。挑战有具体对象，解法沿同一关系展开。此处数量、强调词和冒号都有职责；保留它们。英文表层规则只定位句末未展开的裸宣告，仍需连读随后语境，不能假定下一句没有解释。

来源：[AnnaAgent source.txt L25–43](https://github.com/RoadtoAGI/academic-writing-skills/blob/main/plugins/academic-writing-suite/skills/academic-exemplar-analysis/library/papers/acl-2025-annaagent/source.txt)，已核原PDF p.1左栏。更完整的挑战—功能组—消融组织归 `academic-story` 的 AnnaAgent 案例。

## 对比命中先确定比较对象

ACPO 在呈现两项已有经验的矛盾时写 `In contrast, Yang et al. [2025b] argue…`；在定义CISPO基线时写 `clips only IS ratios rather than gating token updates`。两者分别承担背景问题与技术区分职责。GENOME 相关工作中的 `By contrast, GENOME optimizes…` 则属于原作者对本文相对其他方法的定位。

lint 为上述片段都提供 `en_contrast_scope` 候选，并保持 `scope_status: unclassified`、`auto_action: none`。语义审阅区分它们：背景发现和必要方法区分可以保留；目标稿的定位沿 `academic-writing` Authority 使用已有作者决定，必要时提交作者选择。不能为了清空命中删除比较对象或技术差异。

完整来源和作者权限判定见 [writing 的定位与背景对照案例](https://github.com/RoadtoAGI/academic-writing-skills/blob/main/plugins/academic-writing-suite/skills/academic-writing/references/explanation-cases.md#c17c20-author-positioning-and-a-background-comparison)。方法定义另见 [ACPO L490–493](https://github.com/RoadtoAGI/academic-writing-skills/blob/main/plugins/academic-writing-suite/skills/academic-exemplar-analysis/library/papers/arxiv-2026-acpo-rl-updates/source.txt)。

## 分词尾句、归因与反复回指

Avengers 的跨分布结果段列出三个比较数字后写 `showcasing its strong generalization capability`。这是一个值得复读的分词尾句；是否删减取决于它在本段是否解释结果的意义，或只重复前句评价。原文出现某个高频词不证明该句有错。来源：[Avengers L163–165](https://github.com/RoadtoAGI/academic-writing-skills/blob/main/plugins/academic-writing-suite/skills/academic-exemplar-analysis/library/papers/aaai-2026-avengers/source.txt)。

同一判据适用于 `This design enables…` 和章节收束：辨明新增能力、推论或承接后再处理。观点可以在摘要、组件解释和结果中承担不同职责；GENOME 用进化启发解释不同算子，不能按“比喻只出现一次”截断。归因模板也不能换成 `This likely stems from…` 后继续补造原因；解释使用作者材料，缺口按 `academic-writing` 的结果解释规则交接。

## 零表层命中仍可能有阅读问题

MUSE 的 `story theory becomes the API of generation` 以及 Gaussian 的 `These population mechanisms correspond to operations on a Gaussian mixture.` 都可能表层零命中。前者需要读者恢复具体操作，后者需要分辨建模动作与既有性质；单看词表无法判断。

MUSE 的真实修复由[具体对象与操作案例](https://github.com/RoadtoAGI/academic-writing-skills/blob/main/plugins/academic-writing-suite/skills/academic-writing/references/explanation-cases.md#c11-muse-make-the-object-and-operation-recoverable)承接；已有检索观察怎样接回设计选择见[解释链案例](https://github.com/RoadtoAGI/academic-writing-skills/blob/main/plugins/academic-writing-suite/skills/academic-writing/references/explanation-cases.md#c26-muse-connect-an-existing-observation-to-the-design)。Gaussian A1/A5/A6 的原句与批注见 B1 反馈归并（历史来源：`oran-suite/oranai/oransim-dev/docs/level-3-implementation/research/academic-writing/B1/oransim-gaussian-feedback.md`）。导师阅读问题需实际修复，不能由机械添加 `may`、`possibly` 或 `we hypothesize` 代替。

## 使用与回归

`scripts/fixtures/en-source-cases.json` 保存原句、来源、定位和语义判断范围，供 lint 的开发回归使用。它检验程序能否定位表层候选，以及能否避免把分布统计、具体挑战和公式标点自动升级为问题；其中的语义说明由来源与上下文阅读支持，不是脚本推理结果。这些已参与开发的来源不充当独立泛化或效果增益证据。
