# AI 生态创新赛题 · 参赛作品

本仓库基于官方基线 **[oceanbase/powercontext@2026-competition-ecosystem](https://github.com/oceanbase/powercontext/tree/2026-competition-ecosystem)**
（基线提交 `d647275c308e09b7b623f322a26f5c4e85734fb0`），按官方脚手架把各赛题资产放进对应目录：

| 目录 | 赛题 | 交付物 |
| --- | --- | --- |
| `dify/` | Dify：Just for Fun，做一个好玩的智能应用 | 应用 DSL（`app.yml`）+ **真·seekdb 知识服务** + 知识库原文 + DSL 校验器 |
| `qoder/` | Qoder：Build with Qoder | 数据库代码审查助手（**接 seekdb 检索与存储**）+ 运行说明 + 验证样例 |
| **Qoder 项目网站** | `https://sql-review-assistant-8ptbxy0nhc9.qoder.zone/` | ✅ 已发布到 Qoder Sites，未登录 HTTP 200（浏览器端 15 条规则可交互） |
| `gaode/` | 高德：周边去哪儿 | `SKILL.md`（评测平台直接加载） |
| `stepfun/` | StepFun：端侧 AI 推理 + seekdb 混合检索 | 浏览器端 INT8 embedding + seekdb 内 RRF 检索 + 技术说明 |
| `minimax/` | MiniMax | MiniMax × seekdb 的 SQL 处方助手 |
| `modelscope/` | 魔搭社区 | ModelScope 问答助手 + **可上传的 Skill**（提交物是 Skill 网址/编号） |
| `amd/` | AMD：seekdb × hipVS | CAGRA bridge 优化方案（官方答题在 seekdb fork 上，本目录为实现与说明） |
| `AI-Ecosystem-Solutions/` | — | 七题总览（实现思路 / 截图链接 / 核心代码） |

## 作品链接（每题交哪一条）

| 赛题 | 作品链接 | 状态 |
| --- | --- | --- |
| **Dify（600076）** | `https://cloud.dify.ai/chat/share?shareId=...`（导入 `dify/app.yml` 后发布） | ⏳ 待发布 —— 操作见 `Dify/LINK_GUIDE.md` |
| **Qoder（600077）** | `https://sql-review-assistant-8ptbxy0nhc9.qoder.zone/` | ✅ 已发布，未登录 HTTP 200，浏览器端 15 条规则可交互 |
| **魔搭社区** | `https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer` | ✅ 已提交成功（公开可访问） |
| 高德 / StepFun | 按对应赛题要求提供（Skill 文件 / Web 应用） | ✅ |

> ⚠️ `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` **不是 Dify 题的作品链接**：
> 它是另一个通用问答助手，跑不出我们声明的玩法，提交它会被判「主要功能运行失败」。

## 提测怎么填

```text
代码仓库地址：https://<用户名>:<令牌>@github.com/tangtang-cx/seekdb.git
分支：2026-competition-ecosystem
Commit：<该分支最新 commit 的完整 40 位 SHA>
```

> ⚠️ 仓库地址**必须**写成 `用户名:令牌@` 的形式（平台只接受这一种），
> 缺用户名或缺令牌会被判为 `failMsg=4`，页面直接显示「执行失败 0.000」。
> 仓库必须保持**私有**（官方不允许 Public 仓库参赛）。

各赛题单独提测时，用对应目录的分支（`Dify` / `qoder` / `gaode` / `stepfun` / `modelscope`）。

## 本地校验

```bash
# Dify：DSL 结构（对照官方 0.6.0 schema）+ 真·seekdb 端到端
python dify/scripts/validate_dsl.py dify/app.yml dify/app-standalone.yml dify/app-rag.template.yml
python dify/seekdb_service/verify.py

# Qoder：15 条静态规则 + Streamlit UI 冒烟
python qoder/tests/test_rules.py -v
python qoder/tests/test_app_smoke.py -v

# 魔搭：客户端单测 + 真实连通性
python modelscope/tests/test_client.py -v
python modelscope/scripts/smoke_test.py

# 高德：Skill 结构校验
python tools/check_skill.py gaode/SKILL.md
```

## 两个"真·seekdb"的实现

1. `dify/seekdb_service/` —— Dify 应用的 HTTP 节点调它：
   本地 `bge-small-zh-v1.5` INT8 ONNX 向量化 → **真实 seekdb 内核**
   （`VECTOR(512)` + `FULLTEXT INDEX ... PARSER ik` + `VECTOR INDEX ... type=hnsw lib=vsag`）
   → `DBMS_HYBRID_SEARCH.GET_SQL` 生成计划、**RRF 融合在 seekdb 内核内完成**。
   真实运行证据见 `dify/seekdb_service/EVIDENCE.json`。
2. `qoder/` —— 审查助手同样接 seekdb：先用混合检索取回相关「医书」条目作为审查依据，
   再把审查历史写回 seekdb（存储 + 查询都有），见 `qoder/README.md`。
