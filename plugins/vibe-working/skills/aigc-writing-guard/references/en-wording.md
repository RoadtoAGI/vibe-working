# 英文判据与观察

处理英文文本时读取本页。语义机制、动作与强度由 [高级语义模式](semantic-families.md) 定义；本页只补英文专属的词项、判据与观察。表层候选由 [英文模式库](en-patterns.json) 定位；学术稿的定位、主张与结果解释归 `academic-writing` 作者权限，相关真实案例见 [英文复核边界](english-review-cases.md)。

案例分两类：本机真实观察（MUSE 稿件、审稿意见、口癖检测报告），以及社区词表。社区词表只用作定位线索，其示例多为作者自拟，本页不转录。

## 词表定位，语感裁决

英文词级口癖随模型版本更替：社区库 humanizer 3.0 把早先列为口癖的“伪范围”和“同义词轮换”降为人类习惯，因为维基百科的观察口径变了。结构与姿态性的习惯更稳定，所以判断顺序是：先看段落在做什么（铺垫、宣告、否定衬托、强凑三件套），再看词。

一个命中按“细心的作者会不会故意这样写”衡量；一处命中只在最强的几类（否定衬托、戏剧化碎句、伪深度格言、起跑式铺垫、与假想敌辩论）上足以动手，其余要同段有多个线索。引文、标题、专名和讨论该短语的段落不动。

## 空泛修饰与意义拔高

**真实观察。** 一位独立审稿人对 MUSE 摘要的意见：`"lifts Sonnet-4.6 from 8.40 → 8.98, surpassing Opus-4.6 zero-shot (8.76) by a meaningful margin" — "meaningful margin" is vague; just state +0.22 absolute / +2.5% relative on a 10-point scale and let the reader judge.` 这是空词的标准修法：评价词被它所评价的数字替换，判断交给读者。

同一稿件的口癖检测报告记录了基线问题：`balanced enumerations, and abstract-noun openings made the exposition feel over-composed`；`slogan-like metaphors and recurrent contrast templates`；技术附录里 `Repeated labels, colons, em-dash appositives, and First/Second/Third/Fourth summaries made the author commentary feel templated`。改稿动作是 `Removed promotional metaphors from Method and tied motivations to observed failures, schema fields, runtime consumers, and review behavior`。报告同时说明分数是编辑风险估计，不是作者身份概率。

**词项线索**（社区库 humanizer §12，“出现即值得看”的词；其余词按用法判断，“a formal word outside these lists is not a tell by itself”）：`actually, additionally, align with, bolstered, crucial, deep dive, delve, enduring, enhance, garner, gate/gated/gating (figurative), highlight (verb), interplay, intricate, key (adjective), landscape (abstract), meticulous, pivotal, quietly, robust (figurative), showcase, tapestry (abstract), testament, underscore (verb), valuable, vibrant`。意义拔高短语（§13）：`stands as a testament, a pivotal/crucial moment, plays a key role, marking/shaping the, underscores its importance, reflects a broader, enduring/lasting legacy, setting the stage for, evolving landscape, indelible mark, the future looks bright`。

判据同中文：相对什么？`robust` 在统计学里有定义，`gated` 在网络结构里是字面义，`novel`、`significant` 有对照或检验时是作者主张；都不是口癖。没有标准的评价词删去，或换成它所指的属性与数字。删后不得留下更泛的命题。

## 对照句与虚设对手

**保留条件**（humanizer §1）：`Keep a contrast only when the negative half corrects a belief the reader actually holds, or when both halves carry information.` 形态包括 `not X but Y`、`not just / only / merely X, but Y`、`it's not X, it's Y`、倒装的 `X rather than Y`、拆成两句的 `This does not mean X. It means Y.`，以及收尾的否定碎句 `..., no guessing`。

**真实观察**（MUSE 稿件）：

- 提案提纲：`MUSE's difference is not "more planning" but rule-bearing planning with downstream enforcement.` “more planning”是先前工作和读者都会默认的解释，两半都带信息，骨架成立。但检测报告指出相关工作部分 `Several paragraphs followed the same pattern: summarize a family of systems, then close with a compact MUSE contrast`——单句成立，成片即模板；修法是 `stated differences through concrete artifact behavior instead of a repeated contrast formula`。
- 正文：`a patch it judges to require rollback is not applied but re-dispatches the writer at scene scope.` 程序性两分，两半各是一个动作，不触发。

**虚设对手的词项线索**（humanizer §5、§17）：`This isn't (mainly) about, I'm not saying, To be clear, Don't get me wrong, This is not to say, Some might say... but, A tempting approach would be, One might be tempted to, An obvious approach would be, You might think... but, It would be easy to just`；借权威：`experts argue, observers have cited, industry reports, some critics, several publications`。保留条件：`Keep an objection the text attributes or answers in full, and keep an option a reader would actually weigh. Several unrelated rejections in a row are a stronger sign than one.` 缺引用本身不是口癖。

本机英文语料中尚未收集到虚设对手的真实案例；出现后补入，不自拟。

## 绕道动词与僵硬语域

`serves as, stands as, functions as, operates as, marks, represents; boasts, features, offers, maintains; refers to` 绕开 `is / are / has`（humanizer §18）。`-ing` 尾句 `highlighting, underscoring, emphasizing, ensuring, reflecting, showcasing` 把评价嫁接在事实后（§15）；真实判断案例见 [分词尾句](english-review-cases.md#分词尾句归因与反复回指)。不带施事的被动、`utilize`、`facilitate`、`in order to` 和名词化短语属于同一语域偏移，单独出现不是问题，成片时按段落恢复主语与直接动词。

列表式开场 `There are several ways / There are a few options / Here are a few tips / Here are the steps / It is generally a good idea / In general` 来自 HC3 数据集的 ChatGPT 指示短语表；它们是问答助手语域，进入文章正文就成了起跑式铺垫，删去后直接写第一条内容。

## 并列标题

英文标题 `X and Y` 同样问两件事：这个 and 在替读者做事，还是在替作者躲判断；删掉一项，意思会不会变。

**真实观察**：MUSE 稿件相关工作小节 `Narrative Theory and Computational Story Generation`、`Character Agents and Persona Fidelity` 各并列两个有正文的主题，并列项即内容；需要核对的是小节是否说出了本文与它们的关系，还是只做了综述。OranSim 实验协议的 `Estimation and uncertainty`、`Execution and provenance`、`Targets and splits` 是协议文档的固定导航节名，保留。

## 来源

- 审稿意见：`MUSE/paper/exploration/reviews/review-v2-emnlp-independent.md` m1。
- 口癖检测与改写报告：`MUSE/paper/targets/aaai-2027/aigc-detection-report.md`。
- 稿件原句：`MUSE/paper/` 下 `proposal-v4-outline.md`、`main.tex`、`manuscript-v4-gpt.md`；OranSim 协议 `oran-suite/oranai/oransim-dev/docs/` 下 `protocol.md`。
- 社区词表：`MUSE/repos/reference/AIGC-prevent/humanizer/SKILL.md`（v3.1.0，§1、§5、§12、§13、§15、§17、§18）；HC3 `chatgpt-comparison-detection/HC3/indicating_words_en_chatgpt.txt`。
