#!/usr/bin/env python3
"""Scan a git diff for moves that weaken verification evidence.

Every hit is a lead for the reviewer to judge, not a verdict: a test removed
together with the feature it covered is legitimate; an assertion loosened to
make a failing test pass is not.

Usage:
  floor_guard.py --base <ref> [--repo PATH] [--committed-only] [--json]

By default the diff runs from <base> to the working tree, including untracked
files, so uncommitted delivery is scanned too. --committed-only compares
<base> with HEAD.

Exit codes: 0 no hits, 1 hits found, 2 git or usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|specs?|testing|e2e|acceptance)/"
    r"|(^|/)test_[^/]*\.py$|_test\.(py|go)$"
    r"|\.(test|spec)\.[cm]?[jt]sx?$"
    r"|(Test|Tests|IT)\.(java|kt|cs)$"
)

TOOL_OUTPUT = re.compile(
    r"(^|/)(node_modules|mutants|mutants\.out|\.stryker-tmp|htmlcov|\.pytest_cache|__pycache__)/"
    r"|(^|/)coverage/lcov-report/|(^|/)reports/mutation/"
)
THRESHOLD_FILES = re.compile(
    r"(^|/)(CONSTRAINTS\.md|\.coveragerc|setup\.cfg|pyproject\.toml|tox\.ini|pytest\.ini"
    r"|jest\.config\.[cm]?[jt]s|vitest\.config\.[cm]?[jt]s|stryker\.conf(ig)?\.[a-z]+"
    r"|\.golangci\.ya?ml|\.eslintrc(\.[a-z]+)?|eslint\.config\.[cm]?[jt]s|\.nycrc(\.[a-z]+)?"
    r"|codecov\.ya?ml|package\.json|\.mutmut[^/]*|mutmut[^/]*\.toml)$"
)
THRESHOLD_WORDS = re.compile(
    r"fail[_-]?under|threshold|coverageThreshold|minimum|\bmin\b|\bbreak\b|\bhigh\b|\blow\b"
    r"|complexity|max[-_]|omit|exclude|ignore|skip|paths_to_mutate|do_not_mutate|mutate",
    re.IGNORECASE,
)

SUPPRESSION = re.compile(
    r"#\s*noqa|#\s*type:\s*ignore|#\s*pragma:\s*no\s*(cover|mutate)|#\s*pylint:\s*disable"
    r"|#\s*nosec|nosemgrep|gitleaks:allow|//\s*nolint|@ts-(ignore|expect-error|nocheck)"
    r"|eslint-disable|istanbul\s+ignore|c8\s+ignore|v8\s+ignore|Stryker\s+disable"
    r"|@SuppressWarnings|#\[allow\(|//\s*coverage:ignore",
    re.IGNORECASE,
)
SKIP = re.compile(
    r"@pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail)\(|@unittest\.(skip|expectedFailure)"
    r"|\b(it|test|describe)\.(skip|todo)\(|\bx(it|test|describe)\(|\bt\.Skip(f|Now)?\("
    r"|@(Disabled|Ignore)\b|#\[ignore\]"
)
ASSERTION = re.compile(
    r"\bassert\w*\b|\bexpect\(|\.should\b|\bself\.assert|\brequire\.\w+\(|\bassert\.\w+\("
    r"|\bt\.(Error|Errorf|Fatal|Fatalf|Fail|FailNow)\(|\.to(Be|Equal|StrictEqual|Throw|Match|Contain|HaveBeenCalled)\w*\("
)
STUB = re.compile(
    r"raise\s+NotImplementedError|panic\(\s*\"(?i:not implemented|todo|unimplemented)"
    r"|throw\s+new\s+Error\(\s*['\"`](?i:not implemented|todo)|\b(todo|unimplemented)!\("
    r"|(#|//|/\*|\*)\s*(TODO|FIXME|XXX|HACK)\b"
)
SOURCE_EXT = re.compile(
    r"\.(py|pyi|[cm]?[jt]sx?|go|java|kts?|rs|rb|cs|c|cc|cpp|cxx|h|hpp|swift|php|scala|vue|svelte|lua|dart)$"
)
EMPTY_HANDLER_ONE_LINE = re.compile(
    r"^\s*except(\s+[\w.,() ]+(\s+as\s+\w+)?)?\s*:\s*(pass|\.\.\.)\s*(#.*)?$"
    r"|catch\s*(\([^)]*\))?\s*\{\s*\}|\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(\{\s*\}|undefined|null)\s*\)"
    r"|if\s+err\s*!=\s*nil\s*\{\s*\}"
)
EXCEPT_HEAD = re.compile(r"^\s*except(\s+[\w.,() ]+(\s+as\s+\w+)?)?\s*:\s*(#.*)?$")
PASS_BODY = re.compile(r"^\s*(pass|\.\.\.|continue)\s*(#.*)?$")


@dataclass
class FileDiff:
    path: str
    status: str = "modified"  # added | deleted | modified | renamed
    added: list[tuple[int, str]] = field(default_factory=list)
    removed: list[tuple[int, str]] = field(default_factory=list)


def git(repo: str, *args: str) -> str:
    proc = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_diff(text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    cur: FileDiff | None = None
    old_ln = new_ln = 0
    hunk = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)$", line)
            cur = FileDiff(path=m.group(2) if m else line.split()[-1])
            files.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("new file mode"):
            cur.status = "added"
        elif line.startswith("deleted file mode"):
            cur.status = "deleted"
        elif line.startswith("rename to "):
            cur.status = "renamed"
            cur.path = line[len("rename to "):]
        elif line.startswith("--- ") and cur.status == "deleted":
            src = line[4:]
            cur.path = src[2:] if src.startswith("a/") else cur.path
        elif line.startswith("@@"):
            m = hunk.match(line)
            if m:
                old_ln, new_ln = int(m.group(1)), int(m.group(2))
        elif line.startswith("+") and not line.startswith("+++"):
            cur.added.append((new_ln, line[1:]))
            new_ln += 1
        elif line.startswith("-") and not line.startswith("---"):
            cur.removed.append((old_ln, line[1:]))
            old_ln += 1
    return files


def untracked(repo: str) -> list[FileDiff]:
    out = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    result = []
    for path in filter(None, out.split("\0")):
        full = os.path.join(repo, path)
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except (IsADirectoryError, FileNotFoundError):
            continue
        result.append(FileDiff(path=path, status="added", added=list(enumerate(lines, start=1))))
    return result


def scan(files: list[FileDiff]) -> list[dict]:
    hits: list[dict] = []

    def hit(kind: str, f: FileDiff, ln: int | None, text: str) -> None:
        hits.append({"kind": kind, "file": f.path, "line": ln, "text": text.strip()[:200]})

    for f in files:
        if TOOL_OUTPUT.search(f.path):
            continue
        is_test = bool(TEST_PATH.search(f.path))
        if f.status == "deleted" and is_test:
            hit("test_file_deleted", f, None, f"{len(f.removed)} lines removed")
            continue
        if THRESHOLD_FILES.search(f.path):
            if f.path.endswith("CONSTRAINTS.md"):
                if f.status == "added":  # a brand-new file weakens nothing; list it once for the record
                    hit("constraints_changed", f, None, f"新增文件，{len(f.added)} 行")
                    continue
                for ln, text in f.removed:
                    hit("constraints_changed", f, ln, "- " + text)
                for ln, text in f.added:
                    hit("constraints_changed", f, ln, "+ " + text)
            else:
                for ln, text in f.removed:
                    if THRESHOLD_WORDS.search(text):
                        hit("threshold_config_changed", f, ln, "- " + text)
                for ln, text in f.added:
                    if THRESHOLD_WORDS.search(text):
                        hit("threshold_config_changed", f, ln, "+ " + text)
        if not SOURCE_EXT.search(f.path):
            continue
        prev: tuple[int, str] | None = None
        for ln, text in f.added:
            if SUPPRESSION.search(text):
                hit("suppression_added", f, ln, text)
            if SKIP.search(text):
                hit("test_skip_added", f, ln, text)
            if EMPTY_HANDLER_ONE_LINE.search(text):
                hit("empty_handler_added", f, ln, text)
            elif prev and prev[0] == ln - 1 and EXCEPT_HEAD.match(prev[1]) and PASS_BODY.match(text):
                hit("empty_handler_added", f, prev[0], prev[1].strip() + " / " + text.strip())
            if not is_test and STUB.search(text):
                hit("stub_or_todo_added", f, ln, text)
            prev = (ln, text)
        if is_test and f.status != "deleted":
            removed = [(ln, t) for ln, t in f.removed if ASSERTION.search(t)]
            added = sum(1 for _, t in f.added if ASSERTION.search(t))
            for ln, text in removed:
                hit("assertion_removed", f, ln, f"{text}  [file: -{len(removed)} +{added} assertions]")
    return hits


LABELS = {
    "test_file_deleted": "测试文件被删除",
    "assertion_removed": "断言被删除或改写（看同文件增删数与改写后的断言是否同样严格）",
    "test_skip_added": "新增 skip / xfail",
    "suppression_added": "新增屏蔽注释",
    "threshold_config_changed": "阈值或排除范围配置有改动",
    "constraints_changed": "CONSTRAINTS.md 有改动",
    "empty_handler_added": "新增空异常处理",
    "stub_or_todo_added": "新增未实现桩或 TODO",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="diff 起点：分支、提交或 merge-base")
    ap.add_argument("--repo", default=".", help="仓库路径，默认当前目录")
    ap.add_argument("--committed-only", action="store_true", help="只比较 base..HEAD，不含未提交改动")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()
    try:
        repo = git(args.repo, "rev-parse", "--show-toplevel").strip()
        if args.committed_only:
            files = parse_diff(git(repo, "diff", "-U0", "--no-color", "-M", args.base, "HEAD"))
        else:
            files = parse_diff(git(repo, "diff", "-U0", "--no-color", "-M", args.base)) + untracked(repo)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    hits = scan(files)
    if args.json:
        print(json.dumps({"base": args.base, "files_scanned": len(files), "hits": hits}, ensure_ascii=False, indent=2))
    else:
        print(f"扫描 {len(files)} 个文件，线索 {len(hits)} 条（base={args.base}）")
        for kind, label in LABELS.items():
            group = [h for h in hits if h["kind"] == kind]
            if not group:
                continue
            print(f"\n## {label}（{len(group)}）")
            for h in group:
                loc = f"{h['file']}:{h['line']}" if h["line"] else h["file"]
                print(f"- {loc}  {h['text']}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
