# PowerContext 赛道交付（ai-ecosystem 镜像分支）

本分支是 **2026 OceanBase 数据库大赛 PowerContext 赛道**的完整产品实现镜像，
与比赛仓库 `tangtang-cx/prowercontext-project` 的 `2026-competition` 分支内容一致。

| 字段 | 值 |
| --- | --- |
| 镜像仓库 | `https://github.com/tangtang-cx/ai-ecosystem` |
| 分支 | `2026-competition-powercontext` |
| 提测仓库（比赛用） | `https://github.com/tangtang-cx/prowercontext-project` |
| 提测分支 | `2026-competition` |
| 提测 commit | `d855bdd6c9516f2eb1a8287247e60e45274ae199` |

> 提测请使用**比赛仓库 + `2026-competition` 分支**：该分支保留了官方冻结基线
> `9db1753434162c0aa7c9f1189a1722e617880a52` 的祖先关系，赛题一的仓库检查才成立。
> 本分支只做成果归档与查阅，根目录的 `src/` 与比赛仓库完全相同。

## 本分支包含什么

- `src/` —— 产品全部源码（判题只加载这一层）
- `docs/`、`tests/`、`e2e/`、`benchmark/`、`openapi/` —— 随仓库交付的文档、测试与资产
- 不含 `competition/`：那是主办方的官方判题资产，不在第三方仓库里再分发

## 本次完成的两道题

### 赛题九 · 来源撤回后的记忆停用与恢复（20 分）

新增 `powercontext.builtin.runtime.source_lifecycle`：

- `SourceLifecycleEvent`（`extra="forbid"`，`revision`/`sequence` 为严格正整数，`node_id`/`reason` 非空）
- `runtime.lifecycle.for_scope(scope_id)` 提供 `register_source` / `register_memory` /
  `register_topic` / `apply` / `resolve`
- 注册即按父节点当前可用性判定状态；父节点缺失、自环、重复父节点一律拒绝
- 事件按 `revision` 精确匹配、按 `sequence` 单调递增，重放幂等
- `all` / `any` 策略沿 DAG 递归传播到所有后代；撤回时原生 Memory 置为非活跃，
  恢复后重新可检索，正文版本不变
- 撤回的 Topic Memory 不再进入原生 Topic 检索与 Context，但原始 `ArtifactRef` 仍可精确读取
- 注册、事件与状态按 scope 持久化；不同 scope 互不影响

### 赛题四 · 财报 PDF 全文解析与证据页检索（50 分）

重写 `powercontext.sources.pdf_pages.search_pdf_pages` 的排序：

- 财报是封闭语料，改为对**全部已捕获页面**打分，而不是在截断的候选池里排序
- 语料级 BM25 + 章节标题加权：一页命中一个生僻词，胜过很多页重复公司名
- 提问指标类问题时预留**主要财务报表页**（利润表 / 资产负债表 / 现金流量表）
- 一个 scope 存放多份年报时，先按问题用词定位到它问的那一份报告再排序
- 财报术语扩展（geographies→geographic、legal→legal proceedings、ebitda→operating income …）

## 本地验收

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/run_selftest.ps1 -Target all
```

| 套件 | 结果 |
| --- | --- |
| test-csv / test-pi / test-pdf / test-rerank / test-incremental | 17 / 15 / 6 / 10 / 14 passed |
| test-count-trigger / test-embedding / test-lifecycle / test-evidence / test-hybrid | 17 / 8 / 4 / 3 / 1 passed |

赛题四的证据页召回（FinanceBench 官方证据页，Recall@20）：

| 数据集 | 改前 | 改后 |
| --- | ---: | ---: |
| 公开样例 PEPSICO_2022_10K（5 题 8 个 gold 页） | 75.0% | **100.0%** |
| 12 份年报 52 题 | 48.1% | **90.4%** |
| 同一 scope 放 4 份年报 27 题 | 48.1% | **85.2%** |
