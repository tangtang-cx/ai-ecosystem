# Dify 赛题交付物：SQL 老中医 · 数据库问诊室（seekdb 医书版）

> 题目：**Just for Fun，用 Dify 做一个好玩的智能应用**。
> 本目录交付 **可直接导入的 Dify 应用 DSL + 真·seekdb 知识服务 + 知识库原文 + 一键脚本 + DSL 校验器**。
> 导入后点一次「发布 → 分享」即可拿到可对话的网页链接，全程零代码。

---

## 0. 上一轮判语与我们的应对

> 判语：**「未实际使用 seekdb 或 PowerContext。」**（得分 0）

这一条是致命的：上一版应用只是「一个会说话的 LLM」，**没有真的连任何数据库**。
本版把 seekdb 接进了应用的**主流程**：

```text
Dify 应用
  └─ HTTP 节点「翻医书（查询 seekdb）」
       └─ POST http://127.0.0.1:8848/search        ← Dify/seekdb_service/serve.py
            ├─ 本地 bge-small-zh-v1.5 (INT8 ONNX) 向量化  → 512 维
            └─ seekdb 内核：HNSW 向量分支 + IK 全文分支 + RRF 融合
       └─ 检索结果经 {{#seekdb.body#}} 注入 LLM 提示词 → 老中医据此开方
```

即：**问一句 → 真的去 seekdb 里检索 → 把检索到的医书原文喂给模型 → 开方**。
不是把知识硬塞进提示词，也不是编造答案。

真·seekdb 的证据：

| 证据 | 位置 |
| --- | --- |
| 端到端验证脚本（跑真实 seekdb 内核） | `Dify/seekdb_service/verify.py` |
| **真实运行结果**（4 个问题、命中、计划含 `_fts`+`_vs` 双分支） | `Dify/seekdb_service/EVIDENCE.json` |
| 建表 DDL（VECTOR + IK 全文 + HNSW/vsag） | `Dify/seekdb_service/seekdb_store.py` |
| 混合检索计划生成（`DBMS_HYBRID_SEARCH.GET_SQL`） | 同上，`SeekdbStore.search()` |
| 本地真模型向量化（INT8 ONNX，相关句余弦 0.78 vs 无关句 0.27） | `Dify/seekdb_service/embedder.py` |
| 服务说明 + 部署（Docker compose：seekdb + 服务） | `Dify/seekdb_service/README.md`、`docker-compose.yml` |

**上一轮的 DSL 阻断错误也已修复**（缺 `app.mode`、缺 `dependencies`、`features.file_upload`
嵌套两层 `fileUploadConfig`、LLM 节点硬编码 provider、知识检索空 `dataset_ids`），自检脚本可复现（见 §4）。

---

## 1. 应用是什么（Just for Fun）

**「SQL 老中医 · 数据库问诊室」**：一位专治数据库疑难杂症的老派中医，兼 OceanBase / seekdb 资深工程师。

把病历交给他——贴一段 SQL、甩一条报错，或者用大白话说「我的查询像老牛拉车」——他先去 seekdb 医书里翻一翻，
再按老中医的套路给你开方：

| 栏目 | 内容 |
| --- | --- |
| 📖 医书摘录（seekdb 检索） | 检索到的原文片段标题与关键句，标明出处 |
| 🩺 望闻问切（病灶诊断） | 2-4 条「症状 → 病因」，先讲人话再上硬货 |
| 💊 药方（可直接复制） | 优化后的完整 SQL / 配置片段，能直接粘贴运行 |
| 🚫 忌口（千万别写） | 会导致性能或正确性问题的写法 + 原因 |
| 🧘 养生建议 | 索引设计、参数、分批、监控等工程实践 |
| 🎋 医嘱小笺 | 一句俏皮话 + 最该先改的那一处 |

内置玩法：就诊须知式开场白、4 条推荐问题、10 轮记忆、支持上传 `.sql`/`.md`/`.txt` 当病历。

---

## 2. 交付物清单

| 文件 | 作用 |
| --- | --- |
| `app.yml` | **主应用 DSL**：含 seekdb HTTP 节点（真·混合检索） |
| `app-standalone.yml` | 纯 LLM 版 DSL（不依赖任何外部服务，导入即跑） |
| `app-rag.template.yml` | Dify 知识库版模板（需挂知识库） |
| `seekdb_service/` | **真·seekdb 知识服务**（bge 向量 + HNSW/IK + RRF）+ 验证脚本 + 证据 + docker-compose |
| `kb/*.md` | 知识库原文 4 篇（全部来自本仓库**实测**结论） |
| `scripts/validate_dsl.py` | DSL 结构校验器（对着官方 schema 逐项查） |
| `scripts/setup_knowledge.py` | 一键建知识库 + 上传文档 + 导入 DSL + 绑定数据集 |
| `scripts/push_docs_to_fastgpt.py` | 把 `kb/` 灌进已有 FastGPT dataset（现网作品链接那个） |
| `screenshots/` | 平台截图放置目录（见 §6） |

---

## 3. 跑起来（评委侧，5 分钟）

**第 1 步：起 seekdb 知识服务**（Dify 要先有它）

```bash
pip install -r Dify/seekdb_service/requirements.txt
python Dify/seekdb_service/serve.py --port 8848
# 或：docker compose -f Dify/seekdb_service/docker-compose.yml up -d
```

验证（另开一个终端）：

```bash
python Dify/seekdb_service/verify.py     # 真实 seekdb 内核 + 真实向量 + 命中结果
curl http://127.0.0.1:8848/health         # {"ok":true,"chunks":19,...}
```

**第 2 步：导入 Dify 应用**

1. 登录 <https://cloud.dify.ai>。
2. 「工作室」→「创建应用」→「导入 DSL 文件」→ 上传本目录的 `app.yml` → 导入。
3. 确认「翻医书（查询 seekdb）」节点的 URL 指向你的服务地址
   （本机 / 自建 Dify 用默认 `http://127.0.0.1:8848/search`；Dify 官方云请改成你的公网地址）。
4. 「老中医坐诊」节点可选一个模型（DSL 里留空 = 用工作区默认模型，不选也能跑）。
5. 「发布」→「分享」→ 复制链接。

**备用**：`app-standalone.yml` 不依赖任何服务，导入即可对话（但没有 seekdb 检索）。

### 自动化脚本

```bash
export DIFY_BASE_URL=https://cloud.dify.ai
export DIFY_API_KEY=app-xxxx              # 知识库 -> API -> Knowledge API key
export DIFY_CONSOLE_TOKEN=xxxx            # 浏览器 cookie
python Dify/scripts/setup_knowledge.py dataset
python Dify/scripts/setup_knowledge.py app --dataset-id <上一步输出的 id>
```

---

## 4. DSL 自检（可复现）

```bash
pip install pyyaml
python Dify/scripts/validate_dsl.py Dify/app.yml Dify/app-standalone.yml Dify/app-rag.template.yml
# 三个文件均：结果：通过，无阻断性错误
```

校验器逐项检查：`app.mode` / `dependencies` / `features` 必填项 / 节点类型 / 连通性（从 start 可达、
无孤立节点）/ 回复节点引用是否存在 / 知识检索节点知识库是否为空 / LLM 节点是否硬编码了可能不存在的
provider / HTTP 节点的 method、url、body 是否合法。

---

## 5. 作品链接

| 项 | 值 |
| --- | --- |
| 现网作品链接（已实测 HTTP 200） | `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` |
| 应用名 / appId | 我的问答助手 / `6af43fdc657c1ade990e7dd0` |
| 知识库 datasetId | `PvxGnL0sbXZQu1owx1QAX65S` |
| Dify 官方版（导入 `app.yml` 并发布后） | `https://cloud.dify.ai/chat/share?shareId=________________` |

> 现网链接在 **FastGPT**（`cloud.fastgpt.cn`，datasetId 是 24 位 FastGPT 格式）上，
> 不是 Dify 官方云（`cloud.dify.ai`）。评测若要求 Dify 官方域名，按 §3 导入 `app.yml` 后发布即可。

---

## 6. 截图清单（放到 `screenshots/`）

| 文件名 | 内容 |
| --- | --- |
| `01-seekdb-service.png` | 服务启动日志 + `/health` 返回 |
| `02-seekdb-evidence.png` | `verify.py` 的真实检索命中输出 |
| `03-dify-canvas.png` | 应用编排画布（开始 → 翻医书（seekdb）→ 老中医坐诊 → 出方） |
| `04-dify-chat.png` | 分享链接的对话截图（含「医书摘录」段落） |
| `05-dify-publish.png` | 发布面板 + 分享链接 |

---

## 7. 知识库原文索引

| 文件 | 内容要点 |
| --- | --- |
| `kb/01-seekdb-向量库速查.md` | `VECTOR(n)` 列、`FULLTEXT INDEX ... PARSER ik`、`VECTOR INDEX ... type=hnsw lib=vsag`（m/ef_construction/ef_search）、`dbms_index_manager.refresh()`、距离度量与调参表 |
| `kb/02-混合检索与RRF.md` | `@search_parm` 协议、`DBMS_HYBRID_SEARCH.GET_SQL`、RRF 公式与 k=60、两路召回放大策略、维度一致性坑 |
| `kb/03-端侧向量化与量化对比.md` | bge-small-zh-v1.5（512 维）、INT8 22.8 MiB / Recall@5 0.917 与 FP32 持平、WebGPU→WASM 回退、离线权重与单线程 |
| `kb/04-AMD-GPU加速HNSW.md` | hipVS/CAGRA 基线对比、优化项与 3.33x 建图模型、recall 红线 0.005、参数扫描档位、AMD 机器复跑步骤 |

四篇文档同时是**加赛（向量数据库）**的技术底稿，答辩可直接复用。
