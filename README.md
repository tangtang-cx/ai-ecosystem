# AI 生态创新赛题作品

本仓库用于 2026 第六届 OceanBase 数据库大赛 **AI 生态创新**方向的三道合作方赛题：

| 目录 | 赛题 | 提交物 | 状态 |
| --- | --- | --- | --- |
| `gaode/` | 周边去哪儿：基于高德的地点推荐助手 | `gaode/SKILL.md` | 已完成 |
| `stepfun/` | 端侧 AI 推理性能优化与 seekdb 混合检索 | Web 应用、源码、技术说明 | 已完成（本机未复跑完整近似检索，见下） |
| `amd/` | seekdb × AMD hipVS：加速 HNSW 索引构建 | 源码、复现测试、CPU/GPU 对比报告 | 未开始：缺 ROCm/GPU |

## 生态赛题（Dify / Qoder / 魔搭）

| 目录 | 赛题 | 提交物 | 状态 |
| --- | --- | --- | --- |
| `Dify/` | Dify：OceanBase 向量库文档 RAG 助手 | `app.yml`（可导入 DSL）、`kb/` 知识库、一键建库脚本 | 已完成，导入并发布即可拿链接 |
| `Qoder/` | Qoder：数据库代码审查助手 | Streamlit 应用 + 15 条静态规则 + 单测 | 已完成，待 Qoder Sites 发布 |
| `魔搭/` | 魔搭社区：ModelScope 推理 API 问答助手 | Python 代码 + 录屏 `第三题.mp4` | 已完成（真实调用，非占位） |

> 全部赛题的**统一索引**（7 节：AMD / MiniMax / Qoder / StepFun / Dify / 高德 / 魔搭，
> 每节含实现思路、截图链接、核心代码）见 [`AI-Ecosystem-Solutions/README.md`](AI-Ecosystem-Solutions/README.md)。

## 提测信息（仓库 / 分支 / Commit SHA）

仓库地址统一为 `https://github.com/tangtang-cx/ai-ecosystem`（私有库，评测方需有访问权限）。

| 赛题 | 分支 | Commit SHA（40 位） |
| --- | --- | --- |
| 高德 | `gaode` | `55c0faebea36a0900d7c54ee647a9c453e099fa7` |
| StepFun | `stepfun` | `ec22a31e539d4ece0657b68ebdbc35f02c9bff92` |
| AMD | `amd-cagra-solution` | `fced626b49611b8e37be0dd1bac8559220cfabe6` |
| Dify | `Dify` | `50437db84813970208381f931147eb57deca8c6b` |
| Qoder | `qoder` | `a97d78f4bf837fa6bc04a8ef02253a03c4f0aee6` |
| 魔搭社区 | `modelscope` | `c5bfe6e237d77941fb77eb7a5b098d29db8acd94` |
| 全部生态赛题合并版 | `2026-competition-ecosystem` | 见 [`AI-Ecosystem-Solutions/README.md`](AI-Ecosystem-Solutions/README.md) |

> 所有分支都包含官方基线提交 `39e069f4`，可直接用于提测平台的「仓库 + 分支 + 40 位 SHA」校验。

## 重要说明

- 高德题**不需要**提交后端代码或 API Key。评测平台统一提供 Agent、模型与高德 MCP 工具，只加载 `gaode/SKILL.md`。
- StepFun 题**禁止调用云端推理 API**。文档向量化与查询向量化必须在浏览器本地完成，存储和混合检索必须由 seekdb 完成。
- AMD 题以 **GPU CAGRA 路径**为硬门槛，CPU 平替不能作为有效提交，必须有 AMD Radeon / ROCm 环境。

> StepFun 的本机验证范围：浏览器端 INT8/FP16 加载、向量化、量化质量对比已实测；
> seekdb 建表与混合检索 SQL 契约已在真实 seekdb 内核验证。但本机 Windows 的
> seekdb-js 嵌入式绑定在 `open()` 阻塞、HNSW 刷新超时，完整近似检索需在
> Linux/macOS 或 `SEEKDB_MODE=server` + Docker 下复跑。

## 分支与提交

三个赛题均基于官方 `2026-competition-ecosystem` 分支的目录约定：

```text
gaode/    -> 高德 Skill
stepfun/  -> 阶跃星辰 Web 应用
amd/      -> AMD 赛题源码（如有 GPU 环境）
```

生态赛题（Dify / Qoder / 魔搭）在 `main` 与 `2026-competition-ecosystem` 两个分支上都有：

```text
Dify/       -> Dify 应用 DSL + 知识库 + 一键脚本
Qoder/      -> Qoder 生成的数据库代码审查助手
魔搭/        -> ModelScope 问答助手 + 录屏
AI-Ecosystem-Solutions/ -> 7 节总览 README
```

提交到提测平台时填写本仓库地址、`2026-competition-ecosystem` 分支和完整 40 位 commit SHA。

## 本地校验

```powershell
# 校验高德 Skill 的 YAML frontmatter 与必填段落
python tools/check_skill.py gaode/SKILL.md

# Qoder：静态规则 + UI 冒烟（23 个用例）
python Qoder/tests/test_rules.py -v
python Qoder/tests/test_app_smoke.py -v

# 魔搭：客户端单测 + 真实连通性（9 个用例）
python 魔搭/tests/test_client.py -v
python 魔搭/scripts/smoke_test.py
```

StepFun 与 AMD 的启动方式分别见对应目录的 `README.md`。
