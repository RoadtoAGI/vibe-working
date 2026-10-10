#!/usr/bin/env python3
"""Structure and coverage metrics for the functions a diff touches.

For every function whose line range intersects the diff, reports cyclomatic
complexity (CCN), non-comment lines (NLOC), line coverage and CRAP:

  CRAP = CCN^2 * (1 - coverage)^3 + CCN

Also reports coverage of the changed lines themselves. Complexity comes from
lizard (Python, JS/TS, Go, Java, Rust, C/C++ and more); coverage is read from
any of: LCOV, coverage.py JSON, Cobertura XML, Go coverprofile. Without a
coverage file, coverage and CRAP are left blank.

Usage:
  diff_metrics.py --base <ref> [--coverage FILE ...] [--ccn N] [--nloc N]
                  [--crap N] [--min-changed-coverage PCT] [--include-tests]
                  [--repo PATH] [--json]

Exit codes: 0 within thresholds, 1 threshold exceeded, 2 setup or input error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|specs?|testing|e2e|acceptance)/"
    r"|(^|/)test_[^/]*\.py$|_test\.(py|go)$"
    r"|\.(test|spec)\.[cm]?[jt]sx?$"
    r"|(Test|Tests|IT)\.(java|kt|cs)$"
)
GENERATED = re.compile(
    r"(^|/)(migrations|vendor|node_modules|dist|build|gen|generated|mutants|mutants\.out|\.stryker-tmp|htmlcov)/"
    r"|(^|/)coverage/lcov-report/|(^|/)reports/mutation/|\.pb\.go$|_pb2\.py$|\.min\.js$"
)


def git(repo: str, *args: str) -> str:
    proc = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def changed_lines(repo: str, base: str, committed_only: bool) -> dict[str, set[int]]:
    rng = [base, "HEAD"] if committed_only else [base]
    text = git(repo, "diff", "-U0", "--no-color", "-M", "--diff-filter=AMR", *rng)
    result: dict[str, set[int]] = defaultdict(set)
    path = None
    for line in text.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            path = target[2:] if target.startswith("b/") else None
        elif line.startswith("@@") and path:
            m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if m:
                start, count = int(m.group(1)), int(m.group(2) or "1")
                result[path].update(range(start, start + count))
    if not committed_only:
        out = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
        for p in filter(None, out.split("\0")):
            full = os.path.join(repo, p)
            if os.path.isfile(full):
                with open(full, encoding="utf-8", errors="replace") as fh:
                    n = len(fh.read().splitlines())
                result[p].update(range(1, n + 1))
    return {p: ls for p, ls in result.items() if ls}


# ---- coverage readers: each returns {path_as_written: {line: hits}} ----

def read_lcov(text: str) -> dict[str, dict[int, int]]:
    data: dict[str, dict[int, int]] = {}
    cur = None
    for line in text.splitlines():
        if line.startswith("SF:"):
            cur = data.setdefault(line[3:].strip(), {})
        elif line.startswith("DA:") and cur is not None:
            parts = line[3:].split(",")
            ln, hits = int(parts[0]), int(float(parts[1]))
            cur[ln] = max(cur.get(ln, 0), hits)
        elif line.startswith("end_of_record"):
            cur = None
    return data


def read_coverage_py_json(obj: dict) -> dict[str, dict[int, int]]:
    data = {}
    for path, info in obj.get("files", {}).items():
        lines = {ln: 1 for ln in info.get("executed_lines", [])}
        lines.update({ln: 0 for ln in info.get("missing_lines", [])})
        data[path] = lines
    return data


def read_cobertura(text: str) -> dict[str, dict[int, int]]:
    root = ET.fromstring(text)
    sources = [s.text.strip() for s in root.iter("source") if s.text]
    data: dict[str, dict[int, int]] = {}
    for cls in root.iter("class"):
        fname = cls.get("filename", "")
        path = fname
        for src in sources:
            cand = os.path.join(src, fname)
            if os.path.exists(cand):
                path = cand
                break
        lines = data.setdefault(path, {})
        for ln in cls.iter("line"):
            n, hits = int(ln.get("number")), int(float(ln.get("hits", "0")))
            lines[n] = max(lines.get(n, 0), hits)
    return data


def read_go_profile(text: str) -> dict[str, dict[int, int]]:
    data: dict[str, dict[int, int]] = {}
    pat = re.compile(r"^(.+):(\d+)\.\d+,(\d+)\.\d+ \d+ (\d+)$")
    for line in text.splitlines()[1:]:
        m = pat.match(line.strip())
        if not m:
            continue
        path, start, end, count = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        lines = data.setdefault(path, {})
        for ln in range(start, end + 1):
            lines[ln] = max(lines.get(ln, 0), count)
    return data


def read_coverage(path: str) -> dict[str, dict[int, int]]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    head = text.lstrip()[:200]
    if head.startswith("mode:"):
        return read_go_profile(text)
    if head.startswith("{"):
        return read_coverage_py_json(json.loads(text))
    if head.startswith("<"):
        return read_cobertura(text)
    if "SF:" in text:
        return read_lcov(text)
    raise ValueError(f"无法识别覆盖率格式：{path}（支持 LCOV、coverage.py JSON、Cobertura XML、Go coverprofile）")


def map_coverage(raw: dict[str, dict[int, int]], repo: str, targets: list[str]) -> dict[str, dict[int, int]]:
    """Map coverage paths (absolute, relative, or Go import paths) onto repo-relative targets."""
    mapped: dict[str, dict[int, int]] = {}
    for cpath, lines in raw.items():
        norm = cpath.replace("\\", "/")
        rel = None
        if os.path.isabs(norm):
            r = os.path.relpath(norm, repo)
            if not r.startswith(".."):
                rel = r
        if rel is None and norm in targets:
            rel = norm
        if rel is None:  # Go import paths and other prefixed forms: most specific target wins
            longer = [t for t in targets if norm.endswith("/" + t)]
            rel = max(longer, key=len) if longer else None
        if rel is None:  # paths relative to a package directory: accept only an unambiguous match
            shorter = [t for t in targets if t.endswith("/" + norm)]
            rel = shorter[0] if len(shorter) == 1 else None
        if rel is None:
            continue
        dest = mapped.setdefault(rel, {})
        for ln, hits in lines.items():
            dest[ln] = max(dest.get(ln, 0), hits)
    return mapped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="diff 起点：分支、提交或 merge-base")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--committed-only", action="store_true", help="只比较 base..HEAD")
    ap.add_argument("--coverage", action="append", default=[], help="覆盖率文件，可重复")
    ap.add_argument("--ccn", type=float, help="单函数圈复杂度上限")
    ap.add_argument("--nloc", type=float, help="单函数非注释行数上限")
    ap.add_argument("--crap", type=float, help="单函数 CRAP 上限")
    ap.add_argument("--min-changed-coverage", type=float, help="改动行覆盖率下限（百分比）")
    ap.add_argument("--include-tests", action="store_true", help="把测试文件也纳入统计")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        import lizard
        from lizard_languages import get_reader_for
    except ImportError:
        print("需要 lizard：pip install lizard（或 uv pip install lizard）", file=sys.stderr)
        return 2

    try:
        repo = git(args.repo, "rev-parse", "--show-toplevel").strip()
        changes = changed_lines(repo, args.base, args.committed_only)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    targets = sorted(
        p for p in changes
        if get_reader_for(p) and not GENERATED.search(p) and (args.include_tests or not TEST_PATH.search(p))
    )

    cov: dict[str, dict[int, int]] = {}
    try:
        for cfile in args.coverage:
            for p, lines in map_coverage(read_coverage(cfile), repo, targets).items():
                dest = cov.setdefault(p, {})
                for ln, hits in lines.items():
                    dest[ln] = max(dest.get(ln, 0), hits)
    except (OSError, ValueError, ET.ParseError) as exc:
        print(exc, file=sys.stderr)
        return 2
    has_cov = bool(args.coverage)

    functions, file_rows = [], []
    for path in targets:
        full = os.path.join(repo, path)
        with open(full, encoding="utf-8", errors="replace") as fh:
            info = lizard.analyze_file.analyze_source_code(path, fh.read())
        touched = changes[path]
        fcov = cov.get(path, {})
        instrumented = [ln for ln in touched if ln in fcov]
        covered = [ln for ln in instrumented if fcov[ln] > 0]
        file_rows.append({
            "file": path,
            "changed_lines": len(touched),
            "instrumented_changed": len(instrumented),
            "covered_changed": len(covered),
            "coverage_data": path in cov,
        })
        for fn in info.function_list:
            span = range(fn.start_line, fn.end_line + 1)
            if not touched.intersection(span):
                continue
            inst = [ln for ln in span if ln in fcov]
            coverage = (sum(1 for ln in inst if fcov[ln] > 0) / len(inst)) if inst else None
            ccn = fn.cyclomatic_complexity
            crap = ccn ** 2 * (1 - coverage) ** 3 + ccn if coverage is not None else None
            flags = []
            if args.ccn is not None and ccn > args.ccn:
                flags.append("CCN")
            if args.nloc is not None and fn.nloc > args.nloc:
                flags.append("NLOC")
            if args.crap is not None and crap is not None and crap > args.crap:
                flags.append("CRAP")
            functions.append({
                "file": path, "function": fn.name, "start": fn.start_line, "end": fn.end_line,
                "ccn": ccn, "nloc": fn.nloc,
                "coverage": None if coverage is None else round(coverage * 100, 1),
                "crap": None if crap is None else round(crap, 1), "flags": flags,
            })

    total_inst = sum(r["instrumented_changed"] for r in file_rows)
    total_cov = sum(r["covered_changed"] for r in file_rows)
    changed_cov = round(total_cov / total_inst * 100, 1) if total_inst else None
    missing_cov = [r["file"] for r in file_rows if has_cov and not r["coverage_data"]]
    cov_fail = (args.min_changed_coverage is not None and changed_cov is not None
                and changed_cov < args.min_changed_coverage)
    flagged = [f for f in functions if f["flags"]]
    functions.sort(key=lambda f: (-(f["crap"] or 0), -f["ccn"]))

    if args.json:
        print(json.dumps({
            "base": args.base, "files": file_rows, "functions": functions,
            "changed_line_coverage": changed_cov, "files_without_coverage": missing_cov,
            "thresholds": {"ccn": args.ccn, "nloc": args.nloc, "crap": args.crap,
                           "min_changed_coverage": args.min_changed_coverage},
            "exceeded": {"functions": len(flagged), "changed_coverage": cov_fail},
        }, ensure_ascii=False, indent=2))
    else:
        print(f"改动文件 {len(targets)} 个，涉及函数 {len(functions)} 个（base={args.base}）")
        if has_cov:
            shown = "无可插桩改动行" if changed_cov is None else f"{changed_cov}%（{total_cov}/{total_inst}）"
            mark = "  ← 低于下限" if cov_fail else ""
            print(f"改动行覆盖率：{shown}{mark}")
            if missing_cov:
                print("覆盖率文件里找不到：" + "、".join(missing_cov))
        print("\n| 函数 | 位置 | CCN | NLOC | 覆盖率% | CRAP | 超限 |\n|---|---|---|---|---|---|---|")
        for f in functions:
            cov_s = "-" if f["coverage"] is None else f["coverage"]
            crap_s = "-" if f["crap"] is None else f["crap"]
            print(f"| {f['function']} | {f['file']}:{f['start']}-{f['end']} | {f['ccn']} | {f['nloc']} "
                  f"| {cov_s} | {crap_s} | {','.join(f['flags'])} |")
    return 1 if flagged or cov_fail else 0


if __name__ == "__main__":
    sys.exit(main())
