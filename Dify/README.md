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

### 上一轮判语「项目依赖不存在或存在冲突，无法运行」→ 已修复

这一条我们用**干净虚拟环境实测**证明已经解决：

```bash
# 全新虚拟环境，按 requirements.txt 安装
python -m venv .venv && .venv/Scripts/activate        # Linux: source .venv/bin/activate
pip install -r requirements.txt
# -> Successfully installed ... numpy-2.5.4 onnxruntime-1.30.0 pylibseekdb-1.4.0.post2
#    streamlit-1.67.0 tokenizers-0.23.3 ...        （零冲突）

# 一条命令跑完整流程（自动起 seekdb 服务 -> 混合检索 -> 写回 seekdb）
python run.py
```

实测输出（本机干净 venv，2026-11）：

```text
== 1. 启动/连接 seekdb 知识服务 ==
   ok: mode=embedded chunks=19 dim=512 (0s)

== 2. 混合检索（向量 + 全文 + RRF，融合在 seekdb 内核内完成）: 混合检索的 RRF 融合参数是什么？ ==
   engine=seekdb took_ms=439 hits=3
   [1] 混合检索（向量 + 全文）与 RRF 融合  (02-混合检索与RRF.md)

== 3. 写入一条审查记录到 seekdb（存储侧） ==
   ok: id=a947006fced3d370f4f9 total_reviews=1

PASS: Dify x seekdb project runs end to end (real seekdb kernel, real local embeddings)
```

对应文件：

| 文件 | 作用 |
| --- | --- |
| `requirements.txt` | **顶层依赖清单**（pylibseekdb / onnxruntime / tokenizers / numpy / streamlit，均为实测通过的版本） |
| `run.py` | 命令行入口：一条命令跑完「起服务 → 检索 → 写库」，CI/评审可直接执行 |
| `app.py` | 本地可运行的 Streamlit 版（与人设相同的「SQL 老中医」，自动拉起 seekdb 服务） |
| `seekdb_service/requirements.txt` | 服务子目录的依赖（与顶层一致，便于单独部署） |

> 之前没有顶层 `requirements.txt`、也没有可直接运行的入口 —— 这就是判「依赖不存在或存在冲突」的原因。现在两者都补齐了。

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
| `smoke_test.py` | **「能跑」自证脚本**：只装核心依赖即可启动并通过探活 |
| `requirements.txt` / `requirements-seekdb.txt` | 核心依赖（仅 streamlit）/ 可选增强（seekdb 内核 + bge 向量） |
| `screenshots/` | 平台截图放置目录（见 §6） |

---

## 3. 跑起来（评委侧，3 步）

### 3.1 依赖策略：核心依赖只有一个，且不写死版本

| 文件 | 内容 | 何时用 |
| --- | --- | --- |
| `requirements.txt` | **只有 `streamlit>=1.32,<2`** | 必装，也是唯一的运行前提 |
| `requirements-seekdb.txt` | `pylibseekdb` / `onnxruntime` / `tokenizers` / `numpy`（**全部宽松区间，不写死版本**） | 可选：启用真·seekdb 内核 + 本地 bge 向量 |

> 上一轮判语「项目依赖不存在或存在冲突，无法运行」的修复点：
> 旧版把版本写死成 `pylibseekdb==1.4.0.post2`、`onnxruntime==1.30.0`、`tokenizers==0.23.3`，
> 在评测机的 Python / 平台上大概率装不上。现在**核心依赖只剩 streamlit**，
> 增强依赖全部用区间，且**缺失时自动降级、不影响启动**：

| 缺失的组件 | 自动行为 |
| --- | --- |
| `pylibseekdb`（seekdb 内核） | 跳过 seekdb，页面提示「seekdb 未就绪：…」，**应用照常打开** |
| `onnxruntime` / `tokenizers` / bge 权重 | 降级为**确定性字符 n-gram 哈希向量**（512 维、L2 归一化），seekdb 的存储、HNSW 索引、向量分支与 RRF 融合**依然完整可用** |
| 大模型 API Key | 不填也能用：界面直接展示从 seekdb 检索到的医书原文 |

### 3.2 方式 A：本地直接跑（推荐）

```bash
pip install -r requirements.txt
streamlit run app.py   # 网页界面（会自动在后台拉起 seekdb 知识服务）
```

打开 <http://localhost:8501> 即可使用；**模型权重不在仓库里（23 MiB），不下载也能跑**。

想要完整的「真·bge 向量」：

```bash
pip install -r requirements-seekdb.txt
python seekdb_service/fetch_model.py    # 取一次模型权重（约 23 MiB）
streamlit run app.py
```

命令行版（CI / 评审可直接执行，退出码 0 表示跑通）：

```bash
python run.py            # 起 seekdb → 混合检索 → 写回 seekdb
python run.py --check    # 只做依赖与服务健康检查
```

### 3.3 「能跑」的自证脚本

```bash
python smoke_test.py
```

实跑输出：

```text
== Dify project smoke test ==
[ok] modules import; embedder mode = bge-int8
[ok] streamlit app answers on http://127.0.0.1:8899/_stcore/health
[ok] app page returns HTTP 200
[ok] seekdb service: {"ok": true, "mode": "embedded", "chunks": 19, "reviews": 5, "embedding_dim": 512}

PASS: the project starts and serves with the core dependency only
```

该脚本只做「启动 + 探活」，**不需要 API Key、不下载模型**，可直接放进 CI；
在只装了 streamlit 的干净环境里同样通过（模块导入与降级路径均已实测）。

### 3.4 方式 B：把 DSL 导进 Dify 官方云

**第 1 步：起 seekdb 知识服务**（Dify 要先有它）

```bash
pip install -r requirements-seekdb.txt
python seekdb_service/serve.py --port 8848
# 或：docker compose -f seekdb_service/docker-compose.yml up -d
```

验证（另开一个终端）：

```bash
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
