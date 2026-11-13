# AMD 赛题（seekdb × AMD hipVS）准备分支

本分支是 AMD 赛题的**执行规划**，不含实现代码（代码要写在 seekdb 的 fork 里）。

| 文档 | 内容 |
| --- | --- |
| [amd/EXECUTION_PLAN.md](amd/EXECUTION_PLAN.md) | **主文档**：角色与机器分工、代码地图、P0~P7 阶段计划、测量口径、硬门槛自检表、时间线、风险预案、红线 |
| [amd/README.md](amd/README.md) | 题面口径与基线信息、环境要求、数据集准备、优化方向的技术背景 |

## 答题仓库说明（重要）

AMD 题的答题仓库**不是**本仓库，而是 seekdb 的 fork：

```text
https://github.com/tangtang-cx/seekdb   （私有）
分支：基于 zihaomu/seekdb 的 amd-oceanbase-official-contest-base-v5
基线冻结 commit：634888d9b037153fa143d2c913ba4b25503e1d62
提测地址格式：https://wzhaihqy:<只读令牌>@github.com/tangtang-cx/seekdb
```

本分支只负责「计划与规范」，代码落地在 seekdb fork 的 `amd-cagra-submit` 分支。
