# Dify 赛题交付物：SQL 老中医 · 数据库问诊室

> 题目：**Just for Fun，用 Dify 做一个好玩的智能应用**。
> 本目录交付 **可直接导入的 Dify 应用 DSL + 知识库原文 + 一键建库脚本 + DSL 结构校验器**，
> 导入后点一次「发布 → 分享」即可拿到可对话的网页链接，全程零代码。

---

## 0. DSL 阻断问题：已修复（并附自检脚本）

上一版 `app.yml` 曾被判「**DSL 配置存在阻断主要流程的错误**」。根因是 5 处 schema 违规，
现已全部按 **Dify 官方当前 DSL（`version: 0.6.0`）** 重写，对照基准是 Dify 仓库自己 CI 用的
`cli/test/e2e/fixtures/apps/echo-chat.yml` 与 `reasoning-chat.yml`：

| # | 原来的问题 | 后果 | 现在的写法 |
| --- | --- | --- | --- |
| 1 | 缺 `app.mode` | Dify 无法判定应用类型，导入即坏 | `app.mode: advanced-chat` |
| 2 | 缺 `dependencies` | schema 校验不通过 | `dependencies: []` |
| 3 | `features.file_upload` 写成了嵌套两层 `fileUploadConfig` | 字段结构非法 | 改成官方扁平结构 + `fileUploadConfig` 9 个限额字段 |
| 4 | **LLM 节点硬编码 `tongyi/qwen-plus`** | 判题工作区没装这个 provider → 节点失效 → **阻断主流程** | `provider: ''` / `name: ''`，回退到**工作区默认模型**，导入即有效 |
| 5 | **知识检索节点 `dataset_ids: []`** | 空知识库 → 节点无效 → **阻断主流程** | 主应用 `app.yml` **直接去掉知识检索节点**；RAG 版单独放在 `app-rag.template.yml` |

第 4、5 条是「阻断主要流程」的真正来源：任何依赖**评测方环境**的配置（特定模型供应商、
特定知识库 id）都会让导入后的应用不可运行。现在主应用 **零外部依赖**：导入到任何 Dify 实例
都能直接跑通。

### 自检脚本（可复现）

```bash
pip install pyyaml
python Dify/scripts/validate_dsl.py Dify/app.yml Dify/app-rag.template.yml
# app.yml                -> 结果：通过，无阻断性错误
# app-rag.template.yml   -> 结果：通过，无阻断性错误
```

校验器会逐项检查：`app.mode` / `dependencies` / `features` 必填项 / 节点类型 / 连通性
（从 start 可达、无孤立节点）/ 回复节点引用是否存在 / **知识检索节点知识库是否为空** /
LLM 节点是否硬编码了可能不存在的 provider。

---

## 1. 应用是什么（Just for Fun）

**「SQL 老中医 · 数据库问诊室」**：一位专治数据库疑难杂症的老派中医，兼 OceanBase / seekdb 资深工程师。

把病历交给他——贴一段 SQL、甩一条报错，或者用大白话说「我的查询像老牛拉车」——他会按老中医的套路给你开方：

| 栏目 | 内容 |
| --- | --- |
| 🩺 望闻问切（病灶诊断） | 2-4 条「症状 → 病因」，先讲人话再上硬货 |
| 💊 药方（可直接复制） | 优化后的完整 SQL / 配置片段，能直接粘贴运行 |
| 🚫 忌口（千万别写） | 会导致性能或正确性问题的写法 + 原因 |
| 🧘 养生建议 | 索引设计、参数、分批、监控等工程实践 |
| 🎋 医嘱小笺 | 一句俏皮话 + 最该先改的那一处 |

内置玩法：
- **开场白**就是一份「就诊须知」，用户一进来就知道怎么玩；
- **4 条推荐问题**（"我的查询像老牛拉车，一跑就是三十秒，怎么治？"）降低上手门槛；
- **10 轮记忆**（`memory.window.size = 10`），可以接着上一张方子追问；
- **支持上传 `.sql` / `.md` / `.txt`** 当病历；
- 提示词里硬约束了**真实语法**（`VECTOR(n)`、`VECTOR INDEX ... WITH(distance=cosine, type=hnsw,
  lib=vsag, ...)`、`FULLTEXT INDEX ... WITH PARSER ik`、`dbms_index_manager.refresh()`），
  并要求「知识覆盖不到就直说，不要编造 API」。

---

## 2. 交付物清单

| 文件 | 作用 |
| --- | --- |
| `app.yml` | **主应用 DSL**（零依赖，导入即跑通）—— 先导这个 |
| `app-rag.template.yml` | RAG 版 DSL 模板（带知识检索节点，需挂知识库） |
| `kb/*.md` | 知识库原文 4 篇（全部来自本仓库**实测**结论） |
| `scripts/validate_dsl.py` | DSL 结构校验器（对着官方 schema 逐项查） |
| `scripts/setup_knowledge.py` | 一键建库 + 上传文档 + 导入 DSL + 绑定数据集 |
| `scripts/push_docs_to_fastgpt.py` | 把 `kb/` 灌进已有 FastGPT dataset（现网作品链接那个） |
| `screenshots/` | 平台截图放置目录（见 §5） |

---

## 3. 零代码路径（评委侧，5 分钟）

1. 登录 <https://cloud.dify.ai>。
2. **导入应用**：「工作室」→「创建应用」→「导入 DSL 文件」→ 上传本目录的 `app.yml` → 导入。
3. **选模型**（可选）：点「老中医坐诊」节点 → 选一个你工作区里已有的模型。
   *DSL 里模型留空 = 用工作区默认模型；不选也能跑。*
4. **发布**：右上角「发布」→「分享」→ 复制链接。
5. **（进阶）** 想用知识库：先「知识库」→ 创建 → 上传 `kb/` 下 4 个 `.md` → 索引选「高质量」
   → 再导入 `app-rag.template.yml` → 在「翻医书」节点里选中该知识库 → 发布。

### 自动化路径（脚本）

```bash
export DIFY_BASE_URL=https://cloud.dify.ai
export DIFY_API_KEY=app-xxxx              # 知识库 -> API -> Knowledge API key
export DIFY_CONSOLE_TOKEN=xxxx            # 浏览器 cookie
python Dify/scripts/setup_knowledge.py dataset
python Dify/scripts/setup_knowledge.py app --dataset-id <上一步输出的 id>
```

脚本只依赖 Python 标准库。

---

## 4. 作品链接

| 项 | 值 |
| --- | --- |
| 现网作品链接（已实测 HTTP 200） | `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` |
| 应用名 / appId | 我的问答助手 / `6af43fdc657c1ade990e7dd0` |
| 知识库 datasetId | `PvxGnL0sbXZQu1owx1QAX65S` |
| Dify 官方版（导入 `app.yml` 后） | `https://cloud.dify.ai/chat/share?shareId=________________` |

> 现网链接在 **FastGPT**（`cloud.fastgpt.cn`，datasetId 是 24 位 FastGPT 格式）上，
> 不是 Dify 官方云。评测若要求 Dify 官方域名，导入 `app.yml` 1 分钟即可拿到同款链接，
> 并把链接回填到本表（改一个文件，30 秒推送）。

---

## 5. 截图清单（放到 `screenshots/`）

| 文件名 | 内容 |
| --- | --- |
| `01-dify-import.png` | 导入 DSL 的界面 |
| `02-dify-canvas.png` | 应用编排画布（开始 → 老中医坐诊 → 出方） |
| `03-dify-chat.png` | 分享链接的对话截图（含结构化「开方」输出） |
| `04-dify-publish.png` | 发布面板 + 分享链接 |

---

## 6. 知识库原文索引

| 文件 | 内容要点 |
| --- | --- |
| `kb/01-seekdb-向量库速查.md` | `VECTOR(n)` 列、`FULLTEXT INDEX ... PARSER ik`、`VECTOR INDEX ... type=hnsw lib=vsag`（m/ef_construction/ef_search）、`dbms_index_manager.refresh()`、距离度量与调参表 |
| `kb/02-混合检索与RRF.md` | `@search_parm` 协议、`DBMS_HYBRID_SEARCH.GET_SQL`、RRF 公式与 k=60、两路召回放大策略、维度一致性坑 |
| `kb/03-端侧向量化与量化对比.md` | bge-small-zh-v1.5（512 维）、INT8 22.8 MiB / Recall@5 0.917 与 FP32 持平、WebGPU→WASM 回退、离线权重与单线程 |
| `kb/04-AMD-GPU加速HNSW.md` | hipVS/CAGRA 基线对比、优化项与 3.33x 建图模型、recall 红线 0.005、参数扫描档位、AMD 机器复跑步骤 |

四篇文档同时是**加赛（向量数据库）**的技术底稿，答辩可直接复用。
