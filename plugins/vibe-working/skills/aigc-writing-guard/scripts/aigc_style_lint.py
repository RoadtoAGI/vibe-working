#!/usr/bin/env python3
"""Deterministic Chinese/English surface-style lint for non-creative writing.

The script reports observable phrase and distribution signals. It does not
estimate whether a text was written by AI.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATTERN_PATH = SKILL_ROOT / "references" / "zh-patterns.json"
EN_PATTERN_PATH = SKILL_ROOT / "references" / "en-patterns.json"
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?])")
CITATION_RE = re.compile(
    r"\[[0-9,，;；\-–—\s]+\]"
    r"|[（(][^）)]*(?:19|20)\d{2}[a-z]?[^）)]*[）)]"
    r"|(?:doi|DOI)\s*[:：]"
    r"|(?:来源|数据源|资料来源)\s*[:：]"
)


def load_policy(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        policy = json.load(handle)
    if policy.get("schema_version") != 1:
        raise ValueError("unsupported pattern-library schema_version")
    return policy


def visible_lines(text: str) -> list[str]:
    """Blank fenced-code lines while preserving source line numbers."""
    output: list[str] = []
    in_fence = False
    fence_char = ""
    fence_size = 0
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_size = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_size:
                in_fence = False
            output.append("")
            continue
        output.append("" if in_fence else line)
    return output


def sentence_for_offset(line: str, offset: int) -> str:
    left = max(line.rfind(mark, 0, offset) for mark in "。！？!?")
    right_candidates = [line.find(mark, offset) for mark in "。！？!?" if line.find(mark, offset) >= 0]
    right = min(right_candidates) + 1 if right_candidates else len(line)
    return line[left + 1 : right]


def excerpt(line: str, limit: int = 160) -> str:
    value = line.strip()
    return value if len(value) <= limit else value[: limit - 1] + "…"


def make_hit(
    *,
    family: str,
    rule_id: str,
    severity: str,
    line: int | None,
    column: int | None,
    matched: str,
    source: str,
    message: str,
) -> dict[str, Any]:
    return {
        "family": family,
        "review_only": True,
        "rule_id": rule_id,
        "severity": severity,
        "line": line,
        "column": column,
        "matched": matched,
        "source": source,
        "message": message,
    }


def pattern_hits(lines: list[str], policy: dict[str, Any]) -> list[dict[str, Any]]:
    raw: list[tuple[dict[str, Any], int]] = []
    rule_counts: Counter[str] = Counter()
    for family, family_spec in policy["families"].items():
        for rule in family_spec["rules"]:
            regex = re.compile(rule["pattern"])
            for line_number, line in enumerate(lines, start=1):
                for match in regex.finditer(line):
                    if rule.get("requires_anchor"):
                        sentence = sentence_for_offset(line, match.start())
                        if CITATION_RE.search(sentence):
                            continue
                    hit = make_hit(
                        family=family,
                        rule_id=rule["id"],
                        severity=rule["severity"],
                        line=line_number,
                        column=match.start() + 1,
                        matched=match.group(0),
                        source=excerpt(line),
                        message=rule["message"],
                    )
                    raw.append((hit, int(rule.get("min_document_hits", 1))))
                    rule_counts[rule["id"]] += 1
    return [hit for hit, minimum in raw if rule_counts[hit["rule_id"]] >= minimum]


def derived_stack_hits(lines: list[str], policy: dict[str, Any]) -> list[dict[str, Any]]:
    config = policy["derived_signals"]
    hits: list[dict[str, Any]] = []
    stack_specs = (
        ("modal_stack", config["modal_tokens"], int(config["modal_stack_min"]), "检查模态词是否表达不同条件或语气；压缩冗余时保留已有必要限定和作者结论力度。"),
        ("intensifier_stack", config["intensifier_tokens"], int(config["intensifier_stack_min"]), "检查强化词是否重复表达强度；确认冗余后按已有材料修订，保留作者判断。"),
    )
    for line_number, line in enumerate(lines, start=1):
        for sentence in filter(None, (part.strip() for part in SENTENCE_SPLIT_RE.split(line))):
            for rule_id, tokens, minimum, message in stack_specs:
                present = [token for token in tokens if token in sentence]
                if len(present) >= minimum:
                    hits.append(
                        make_hit(
                            family=rule_id,
                            rule_id=rule_id,
                            severity="low",
                            line=line_number,
                            column=max(1, line.find(sentence) + 1),
                            matched=" / ".join(present),
                            source=excerpt(sentence),
                            message=message,
                        )
                    )
    return hits


def markdown_paragraphs(lines: list[str]) -> list[tuple[int, str]]:
    paragraphs: list[tuple[int, str]] = []
    buffer: list[str] = []
    start = 0
    for line_number, line in enumerate(lines + [""], start=1):
        if line.strip():
            if not buffer:
                start = line_number
            buffer.append(line.strip())
        elif buffer:
            value = " ".join(buffer)
            if not re.fullmatch(r"#{1,6}\s+.*", value):
                paragraphs.append((start, value))
            buffer = []
    return paragraphs


def distribution_hits(lines: list[str], policy: dict[str, Any]) -> list[dict[str, Any]]:
    config = policy["derived_signals"]
    paragraphs = markdown_paragraphs(lines)
    hits: list[dict[str, Any]] = []

    prefix_chars = int(config["repeated_paragraph_prefix_chars"])
    prefix_min = int(config["repeated_paragraph_prefix_min"])
    prefix_rows: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
    for line_number, paragraph in paragraphs:
        cleaned = re.sub(r"^[#>*+\-\d.、（）()\s]+", "", paragraph)
        compact = re.sub(r"\s+", "", cleaned)
        if len(compact) >= max(12, prefix_chars):
            prefix_rows[compact[:prefix_chars]].append((line_number, paragraph))
    for prefix, rows in prefix_rows.items():
        if len(rows) >= prefix_min:
            hits.append(
                make_hit(
                    family="repeated_paragraph_opening",
                    rule_id="repeated_paragraph_opening",
                    severity="low",
                    line=rows[0][0],
                    column=1,
                    matched=prefix,
                    source=f"段首出现在行 {', '.join(str(row[0]) for row in rows)}",
                    message="检查重复段首的承接、回指和章节功能；仅合并无用复读，保留必要重复。",
                )
            )

    return hits


def analyze(text: str, policy: dict[str, Any]) -> dict[str, Any]:
    if policy.get("language", "zh").startswith("en"):
        return analyze_english(text, policy)
    lines = visible_lines(text)
    hits = pattern_hits(lines, policy)
    hits.extend(derived_stack_hits(lines, policy))
    hits.extend(distribution_hits(lines, policy))
    hits.sort(key=lambda item: ((item["line"] or 10**9), (item["column"] or 0), item["rule_id"]))

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for hit in hits:
        grouped[hit["family"]].append(hit)
    clusters = []
    for family, family_hits in sorted(grouped.items()):
        severity = max(family_hits, key=lambda item: SEVERITY_RANK[item["severity"]])["severity"]
        clusters.append(
            {
                "family": family,
                "count": len(family_hits),
                "severity": severity,
                "lines": sorted({hit["line"] for hit in family_hits if hit["line"] is not None}),
            }
        )

    return {
        "schema_version": 1,
        "claim": "observable_style_risk_signals_only",
        "review_guidance": "结合上下文判断候选的阅读功能；保留必要回指、衔接、比较和自然搭配。命中数与严重度不构成自动改写或质量结论。",
        "coverage": {
            "surface_lint": "completed",
            "semantic_review": "not_run",
            "overall_review": "incomplete",
        },
        "document": {
            "characters": len(text),
            "lines": len(text.splitlines()),
            "paragraphs": len(markdown_paragraphs(lines)),
        },
        "hits": hits,
        "clusters": clusters,
    }


def english_visible_lines(text: str) -> list[str]:
    """Mask code, URLs and math without moving source coordinates.

    This is a text scanner, not a LaTeX or PDF layout parser. Prose in
    citations, quotations and methods remains a review candidate, not an edit.
    """
    surface = "\n".join(visible_lines(text))
    protected = re.compile(
        r"\\begin\{(?P<env>equation\*?|align\*?|gather\*?|verbatim|lstlisting)\}"
        r".*?\\end\{(?P=env)\}"
        r"|\$\$.*?\$\$|\\\[.*?\\\]|\\\(.*?\\\)"
        r"|(?<!\\)\$(?!\$)[^$\n]*(?<!\\)\$"
        r"|`+[^`\n]+`+|https?://[^\s<>]+|<[^>\n]*>"
        r"|(?<=\])\((?:[^()\n]|\([^()\n]*\))*\)"
        r"|\\(?:label|ref|eqref|autoref|[cC]ref|cite[pt]?)\*?(?:\[[^\]\n]*\]){0,2}\{[^{}\n]*\}",
        re.DOTALL,
    )
    surface = protected.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), surface)
    return [re.sub(r"[^\n]", " ", line) if "---" in line and re.fullmatch(r"[\s|:\-]+", line)
            else line for line in surface.split("\n")]


def clusters_for(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for hit in hits:
        grouped[hit["family"]].append(hit)
    return [
        {"family": family, "count": len(items),
         "severity": max(items, key=lambda item: SEVERITY_RANK[item["severity"]])["severity"],
         "lines": sorted({item["line"] for item in items if item["line"] is not None})}
        for family, items in sorted(grouped.items())
    ]


def analyze_english(text: str, policy: dict[str, Any]) -> dict[str, Any]:
    lines = english_visible_lines(text)
    surface = "\n".join(lines)
    starts = [0]
    for match in re.finditer("\n", surface):
        starts.append(match.end())
    hits = []
    for family, spec in policy["families"].items():
        for rule in spec["rules"]:
            matches = list(re.finditer(rule["pattern"], surface))
            if len(matches) < int(rule.get("min_document_hits", 1)):
                continue
            for match in matches:
                line_index = bisect_right(starts, match.start()) - 1
                hit = make_hit(
                    family=family, rule_id=rule["id"], severity="low",
                    line=line_index + 1, column=match.start() - starts[line_index] + 1,
                    matched=match.group(), source=excerpt(lines[line_index]),
                    message=rule["message"],
                )
                hit.update({"language": "en", "semantic_severity": None,
                            "auto_action": "none", "scope_status": "unclassified",
                            "decision_owner": rule.get("decision_owner", "aigc-writing-guard/contextual-review")})
                hits.append(hit)
    hits.sort(key=lambda item: (item["line"], item["column"], item["rule_id"]))

    # Descriptive counts have no threshold, severity, or fail-on effect.
    words = len(re.findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", surface))
    # Figure/Table labels, clock times and ratios are not prose colons.
    colon_text = re.sub(r"(?im)^\s*(?:figure|fig\.?|table)\s+\d+[a-z]?\s*:", "", surface)
    counts = {
        "prose_colons": len(re.findall(r"(?<!\d):(?!\d)", colon_text)),
        "em_dashes": surface.count("—") + len(re.findall(r"(?<!-)---(?!-)", surface)),
        "participial_tails": sum(h["rule_id"] == "en_participial_tail" for h in hits),
        "lexical_trace_tokens": sum(h["rule_id"] == "en_lexical_trace" for h in hits),
    }
    return {
        "schema_version": 1,
        "language": "en",
        "claim": "observable_style_risk_signals_only",
        "review_guidance": "英文命中仅定位复核候选；固定low表示表层优先级，semantic_severity未判定。词密度不判语义严重度。定位对比遵循academic-writing的作者权限；不得自动删句或弱化主张。",
        "coverage": {"surface_lint": "completed", "semantic_review": "not_run", "overall_review": "incomplete"},
        "document": {"characters": len(text), "lines": len(text.splitlines()),
                     "paragraphs": len(markdown_paragraphs(lines)), "english_words": words},
        "hits": hits,
        "clusters": clusters_for(hits),
        "distribution_signals": {
            "scope": "source prose after code, math, URLs, link targets, HTML tags, LaTeX labels/refs/cites and table separators are masked; Figure/Table label colons and numeric colons excluded; not PDF-layout-normalized",
            "interpretation": "descriptive_review_order_only",
            "semantic_severity": None,
            "metrics": {name: {"count": count, "per_1000_english_words": round(count * 1000 / words, 3) if words else None}
                        for name, count in counts.items()},
        },
    }


def select_languages(text: str, requested: str) -> list[str]:
    if requested != "auto":
        return [requested]
    surface = "\n".join(english_visible_lines(text))
    found = []
    if re.search(r"[\u3400-\u9fff]", surface):
        found.append("zh")
    if re.search(r"[A-Za-z]", surface):
        found.append("en")
    return found or ["zh"]


def analyze_languages(text: str, requested: str, policy_path: Path | None = None) -> dict[str, Any]:
    if policy_path is not None:
        policy = load_policy(policy_path)
        language = "en" if policy.get("language", "zh").startswith("en") else "zh"
        if requested not in ("auto", language):
            raise ValueError("--lang conflicts with the custom pattern library language")
        return analyze(text, policy)
    languages = select_languages(text, requested)
    reports = [analyze(text, load_policy(EN_PATTERN_PATH if lang == "en" else DEFAULT_PATTERN_PATH)) for lang in languages]
    if len(reports) == 1:
        return reports[0]
    report = reports[0]
    report["language"] = "mixed"
    report["languages"] = languages
    report["hits"] += reports[1]["hits"]
    report["hits"].sort(key=lambda item: (item["line"] or 10**9, item["column"] or 0, item["rule_id"]))
    report["clusters"] = clusters_for(report["hits"])
    report["distribution_signals"] = reports[1]["distribution_signals"]
    report["review_guidance"] += " 英文词密度仅安排复核，定位对比交academic-writing作者规则判断。"
    return report


def render_text(report: dict[str, Any]) -> str:
    doc = report["document"]
    output = [
        "AIGC writing style lint",
        f"characters={doc['characters']} paragraphs={doc['paragraphs']} hits={len(report['hits'])}",
        "coverage: surface_lint=completed semantic_review=not_run overall_review=incomplete",
        report["review_guidance"],
    ]
    if "distribution_signals" in report:
        output.append("English distributions (review order only): " + json.dumps(report["distribution_signals"]["metrics"]))
    if not report["hits"]:
        output.append("No registered deterministic signals found.")
        output.append("Semantic review has not run; do not report overall AIGC clearance.")
        return "\n".join(output)
    for hit in report["hits"]:
        location = f"L{hit['line']}:{hit['column']}" if hit["line"] is not None else "document"
        output.append(
            f"[{hit['severity'].upper()}] {location} {hit['family']}/{hit['rule_id']}: "
            f"{hit['matched']} — {hit['message']}"
        )
    output.append("Clusters: " + ", ".join(f"{item['family']}={item['count']}" for item in report["clusters"]))
    output.append("Semantic review has not run; deterministic hits are candidates, not final findings.")
    return "\n".join(output)


def self_test(policy: dict[str, Any]) -> None:
    positive = """诚实说：数据不足。

短答：不建议上线。

## 先给结论

讲人话：先修复输入口径。

值得注意的是，这不是简单的效率问题，而是组织责任问题。

首先，平台提供入口。其次，平台整合数据。最后，平台形成闭环。

这项技术将成为增长引擎，为行业注入新动能。

我调用了你要求的“准确性硬刹车/盲区审计”。

这里只保留两个选择。除非出现真正的新证据，否则没有第三条方案；中途没有兜底。

当前状态与应用范围
"""
    positive_families = {item["family"] for item in analyze(positive, policy)["hits"]}
    expected = {
        "performative_preface",
        "meta_performance",
        "contrastive_negation",
        "formulaic_enumeration",
        "stock_metaphor",
        "code_document_register_leakage",
    }
    missing = expected - positive_families
    if missing:
        raise AssertionError(f"positive fixture missing families: {sorted(missing)}")

    heading_report = analyze("当前状态与应用范围", policy)
    heading_rule_ids = {item["rule_id"] for item in heading_report["hits"]}
    if "status_usage_scope_heading" not in heading_rule_ids:
        raise AssertionError("code-document status/scope heading was not surfaced for semantic review")
    if heading_report["coverage"]["semantic_review"] != "not_run":
        raise AssertionError("deterministic lint must not claim semantic review completion")

    anchored = "李等（2024）研究表明，该方法在表3所列条件下将准确率从71.2%提高到75.8%。"
    anchored_families = {item["family"] for item in analyze(anchored, policy)["hits"]}
    if "vague_authority" in anchored_families:
        raise AssertionError("anchored attribution was incorrectly flagged")

    adjacent = "表3给出两组结果。准确率从71.2%提高到75.8%，误差范围保持不变。"
    if analyze(adjacent, policy)["hits"]:
        raise AssertionError("adjacent factual fixture should be clean")

    literalized_advice = "他近期只走过约100米；过关需要连续步行数百米。途中如果无法继续，受限区内没有可用车辆接驳。轮椅未送到时取消行程。"
    advice_families = {item["family"] for item in analyze(literalized_advice, policy)["hits"]}
    if "code_document_register_leakage" in advice_families:
        raise AssertionError("natural domain prose was incorrectly flagged as code-document register")

    quoted = "本文将“先给结论”和“讲人话”列为待分析的表演式前缀。"
    quoted_families = {item["family"] for item in analyze(quoted, policy)["hits"]}
    if "performative_preface" in quoted_families:
        raise AssertionError("quoted language-analysis object was incorrectly flagged")

    functional = analyze("具体而言，第一组只读取记录。具体而言，第二组还可以更新记录。", policy)
    if not functional["hits"] or not all(hit["review_only"] for hit in functional["hits"]):
        raise AssertionError("functional connective matches must remain review-only candidates")
    if functional["coverage"]["overall_review"] != "incomplete":
        raise AssertionError("surface matches cannot decide readability")

    print("self-test passed: positive, status-scope-heading, coverage-state, anchored-attribution, adjacent-negative, literalized-advice, quoted-object")


def zh_source_self_test(policy: dict[str, Any]) -> None:
    fixtures = json.loads((SKILL_ROOT / "scripts" / "fixtures" / "zh-source-cases.json").read_text(encoding="utf-8"))
    for case in fixtures["cases"]:
        found = {hit["rule_id"] for hit in analyze(case["text"], policy)["hits"]}
        if not set(case["expected_surface_rules"]).issubset(found):
            raise AssertionError(f"{case['id']}: missing surface rules; got {sorted(found)}")
        if set(case.get("forbidden_surface_rules", [])) & found:
            raise AssertionError(f"{case['id']}: unexpected surface rule {sorted(set(case['forbidden_surface_rules']) & found)}")
        if case.get("expect_no_surface_hits") and found:
            raise AssertionError(f"{case['id']}: expected no surface matches; got {sorted(found)}")
    print(f"Chinese source self-test passed: {len(fixtures['cases'])} sourced cases; semantic expectations remain contextual judgments")


def english_self_test() -> None:
    fixtures = json.loads((SKILL_ROOT / "scripts" / "fixtures" / "en-source-cases.json").read_text(encoding="utf-8"))
    policy = load_policy(EN_PATTERN_PATH)
    for case in fixtures["cases"]:
        report = analyze(case["text"], policy)
        found = {hit["rule_id"] for hit in report["hits"]}
        if not set(case["expected_surface_rules"]).issubset(found):
            raise AssertionError(f"{case['id']}: missing surface rules; got {sorted(found)}")
        if set(case.get("forbidden_surface_rules", [])) & found:
            raise AssertionError(f"{case['id']}: unexpected surface rule")
        if case.get("expect_no_surface_hits") and found:
            raise AssertionError(f"{case['id']}: expected no surface matches; got {sorted(found)}")
        if any(hit["auto_action"] != "none" or hit["semantic_severity"] is not None for hit in report["hits"]):
            raise AssertionError("surface scanner must not decide edits or semantic severity")
        if report["coverage"]["semantic_review"] != "not_run":
            raise AssertionError("source regressions do not run semantic review")
    print(f"English self-test passed: {len(fixtures['cases'])} sourced development cases; semantic expectations remain contextual judgments")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="UTF-8 text/Markdown file; stdin when omitted")
    parser.add_argument("--patterns", type=Path, help="optional custom pattern library JSON (language must agree with --lang)")
    parser.add_argument("--lang", choices=("en", "zh", "auto"), default="auto", help="surface library selection; auto scans both languages when present (default: auto)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--fail-on",
        choices=("none", "low", "medium", "high"),
        default="none",
        help="exit 2 on surface candidates at or above this severity, including review-only signals; not a semantic verdict (default: none)",
    )
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        if args.patterns:
            policy = load_policy(args.patterns)
            if policy.get("language", "zh").startswith("en"):
                raise SystemExit("--self-test uses bundled fixtures; run with --lang en and no custom --patterns")
            self_test(policy)
            zh_source_self_test(policy)
        else:
            if args.lang in ("zh", "auto"):
                self_test(load_policy(DEFAULT_PATTERN_PATH))
                zh_source_self_test(load_policy(DEFAULT_PATTERN_PATH))
            if args.lang in ("en", "auto"):
                english_self_test()
        return 0
    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    report = analyze_languages(text, args.lang, args.patterns)
    if args.format == "json":
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(render_text(report))
    if args.fail_on != "none":
        threshold = SEVERITY_RANK[args.fail_on]
        if any(SEVERITY_RANK[hit["severity"]] >= threshold for hit in report["hits"]):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
