# 闸门工具参考

各工具的选项随版本变化，参数以已安装版本的 `--help` 为准。工具产生的工作目录（`mutants/`、`.stryker-tmp/`、`reports/mutation/` 等）不提交，仓库 `.gitignore` 没有覆盖时补上。

## 本 skill 的脚本

脚本依赖 git；`diff_metrics.py` 还依赖 lizard。不往项目环境里装 lizard 时用 uv 临时提供：

```bash
G=<本 skill 目录>
python3 $G/scripts/floor_guard.py --base <起点> [--committed-only] [--json]
uv run --no-project --with lizard python3 $G/scripts/diff_metrics.py \
  --base <起点> --coverage <覆盖率文件> [--coverage <另一个>] \
  [--ccn 10] [--crap 30] [--nloc 60] [--min-changed-coverage 80] [--json]
```

退出码：0 无线索或未超限，1 有线索或超限，2 git、输入或依赖错误。`diff_metrics.py` 默认排除测试文件和生成代码，`--include-tests` 可纳入测试。

## 覆盖率文件

`diff_metrics.py` 识别 LCOV、coverage.py JSON、Cobertura XML 和 Go coverprofile，多语言仓库可以传多个文件。

| 语言 | 生成命令 | 文件 |
|---|---|---|
| Python | `pytest --cov=<包> --cov-report=json:tmp/quality-gate/coverage.json` | coverage.py JSON |
| TS / JS（Jest） | `npx jest --coverage --coverageReporters=lcov` | `coverage/lcov.info` |
| TS / JS（Vitest） | `npx vitest run --coverage --coverage.reporter=lcov`（需 `@vitest/coverage-v8`） | `coverage/lcov.info` |
| Go | `go test ./... -coverprofile=tmp/quality-gate/cover.out` | coverprofile |
| Rust | `cargo llvm-cov --lcov --output-path tmp/quality-gate/lcov.info` | LCOV |

## 变异测试

| 语言 | 工具与安装 | 限定到改动文件 | 结果 |
|---|---|---|---|
| Python | mutmut 3：`uv pip install mutmut` 或装进项目开发依赖 | `pyproject.toml` 的 `[tool.mutmut]`（或 `setup.cfg` 的 `[mutmut]`）：`source_paths = ["<包目录>"]`，`only_mutate = ["<改动文件>.py", ...]`；测试目录写进 `pytest_add_cli_args_test_selection` | `mutmut run`；`mutmut export-cicd-stats` 写出 `mutants/mutmut-cicd-stats.json`（killed / survived / no_tests / timeout 计数）；`mutmut results` 列出未杀死的变异体；`mutmut show <名称>` 给出该变异的 diff |
| TS / JS | StrykerJS：`npm i -D @stryker-mutator/core` 加对应测试运行器插件（`jest-runner`、`vitest-runner` 或 `mocha-runner`），TS 项目加 `typescript-checker` | `npx stryker run --mutate "src/a.ts,src/b.ts:10-60"`；重复运行加 `--incremental` | `reports/mutation/mutation.json`；状态 Killed / Survived / NoCoverage / Timeout |
| Go | gremlins：`go install github.com/go-gremlins/gremlins/cmd/gremlins@latest` | `gremlins unleash <包路径>`，按改动所在的包限定 | 状态 KILLED / LIVED / NOT COVERED / TIMED OUT / NOT VIABLE |
| Rust | cargo-mutants：`cargo install cargo-mutants` | `git diff <起点> > tmp/quality-gate/changes.diff`，再 `cargo mutants --in-diff tmp/quality-gate/changes.diff` | `mutants.out/` 下 caught / missed / timeout / unviable 列表 |

计数口径统一为：杀死率 = 被杀死 ÷（总数 − 等价 − 无法编译或运行的变异体）。mutmut 的 `no tests`、Stryker 的 `NoCoverage`、gremlins 的 `NOT COVERED` 表示没有测试执行到这段代码，按存活处理并进入分诊。超时一般说明变异造成了死循环，计为杀死。

工具配置必须写进项目文件时（如 mutmut 的 `[tool.mutmut]`），写入后在报告里列出，由实现方在修复轮决定保留还是移除。

## 其他结构检查

项目在 `CONSTRAINTS.md` 中定义了对应规则时才运行。

| 检查 | 工具 |
|---|---|
| 重复代码 | `npx jscpd --min-lines 6 --reporters json --output tmp/quality-gate/jscpd <路径>`，多语言通用 |
| Python 依赖方向 | import-linter：在配置里写层级契约后运行 `lint-imports` |
| TS / JS 依赖方向 | dependency-cruiser：`npx depcruise --validate <配置> src` |
| Go 依赖方向 | 编译器已禁止循环导入；层级规则用 `go list -deps` 结合脚本检查 |
