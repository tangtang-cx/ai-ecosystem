# AMD 赛题（seekdb × AMD hipVS）

本分支（`amd-cagra-solution`）包含 AMD 赛题的完整作战计划、可应用的优化实现
与基准脚本：

- 计划与说明：[`amd/README.md`](amd/README.md)、[`amd/EXECUTION_PLAN.md`](amd/EXECUTION_PLAN.md)
- 优化 bridge：[`amd/solution/`](amd/solution/)
- 一键应用与回滚：[`amd/scripts/apply_to_seekdb.sh`](amd/scripts/apply_to_seekdb.sh)
- Bridge 级基准：[`amd/bench/bench_bridge.py`](amd/bench/bench_bridge.py)
- 性能设计与验证：[`amd/docs/PERF_NOTES.md`](amd/docs/PERF_NOTES.md)

提交方式与另外两题不同：AMD 题的官方答题仓库是 **seekdb 的 fork**
（`https://github.com/tangtang-cx/seekdb`），分支基于官方
`amd-oceanbase-official-contest-base-v5`，commit 必须是冻结基线
`634888d9b037153fa143d2c913ba4b25503e1d62` 的后代。

本仓库的 `amd-cagra-solution` 分支用于评审/复用实现；正式提交时把
`amd/solution/` 与 `amd/patches/` 应用到 seekdb fork 即可。
