# Dify 赛题交付物：OceanBase 向量库文档问答助手

> 题目要求：**纯网页拖拽，零代码**。把 OceanBase 文档挂成知识库，建一个聊天应用并发布出可对话的网页链接。
> 本目录交付的是**可直接导入的 Dify 应用 DSL + 知识库原文 + 一键建库脚本**，
> 导入后点一次「发布 → 分享」即可拿到网页 URL，全程不需要写代码。

---

## 0. 当前线上作品链接（已实测存活）

| 项 | 值 |
| --- | --- |
| **作品链接** | `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` |
| 应用名 | 我的问答助手 |
| appId | `6af43fdc657c1ade990e7dd0` |
| shareId | `cbW1j7q9td1AOUZZcakQbgiZ` |
| 知识库 datasetId | `PvxGnL0sbXZQu1owx1QAX65S` |
| 实测 | HTTP 200，页面标题「分享的对话」，可公开访问（2026-11 验证） |

> ⚠️ **平台说明（务必看清）**：这个链接是 **FastGPT**（`cloud.fastgpt.cn`）上的应用，
> 不是 Dify 官方云（`cloud.dify.ai`）——datasetId 是 24 位 FastGPT 格式（Dify 是 UUID），
> 可以确认用的是 FastGPT。
> 如果评测要求**必须是 Dify 官方域名**，请按 §2 走 Dify 官方流程：
> 导入本目录的 `app.yml`，1 分钟得到 `https://cloud.dify.ai/chat/share?shareId=...` 链接。
> 两种平台都指向同一套知识库内容（本目录 `kb/`），交付物完全复用。

### 把本目录的知识库灌进 FastGPT 现有 dataset

`PvxGnL0sbXZQu1owx1QAX65S` 只有一个 id，没有 API Key 是写不进去的。
拿到 FastGPT API Key（账号 → 个人设置 → API 密钥，形如 `fastgpt-xxxxxxxx`）后：

```bash
export FASTGPT_API_KEY=fastgpt-xxxxxxxx
python scripts/push_docs_to_fastgpt.py --dataset-id PvxGnL0sbXZQu1owx1QAX65S
```

脚本会把 `kb/` 下 4 篇文档上传进该知识库并回显文档列表（分块数、token 数）。

---

## 1. 交付物清单

| 文件 | 作用 |
| --- | --- |
| `app.yml` | Dify 应用 DSL（知识检索 + LLM + 直接回复），**一键导入** |
| `kb/*.md` | 知识库原文 4 篇（建表 / 混合检索 / 端侧量化 / AMD GPU 加速） |
| `scripts/setup_knowledge.py` | 一键建知识库 + 上传文档 + 导入 DSL（可选自动化） |
| `scripts/push_docs_to_fastgpt.py` | 把 `kb/` 灌进已有 FastGPT dataset（现网作品链接对应的那一个） |
| `screenshots/` | 平台截图放置目录（见 §5） |

已发布的在线地址（导入后你自己的链接填在这里）：

```text
作品链接：https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ
知识库：PvxGnL0sbXZQu1owx1QAX65S
Dify 官方版（导入 app.yml 后）：https://cloud.dify.ai/chat/share?shareId=________________
```

---

## 2. 零代码路径（推荐，10 分钟）

1. 登录 <https://cloud.dify.ai>。
2. **建知识库**：左上角「知识库」→「创建知识库」→ 选择「从文件导入」→ 上传 `kb/` 目录下
   4 个 `.md` 文件 → 索引方式选「高质量」（向量）→ 选一个 embedding 模型
   （建议 `text-embedding-v3`，维度 1024）→ 等待分段与向量化完成。
   > 知识库原文全部来自本仓库**已实测**的结论（`stepfun/tools/verify_seekdb_contract.py`
   > 与 `stepfun/TECH_REPORT.md`），不是编造的 API。
3. **建应用**：「工作室」→「创建应用」→「导入 DSL 文件」→ 上传本目录的 `app.yml`
   → 导入后点开「知识检索」节点 → 选择上一步的知识库 → 保存。
4. **选模型**：点开「生成回答」节点，模型任选（Dify Cloud 自带 qwen-plus，
   也可以换成你已经配好的 **MiniMax / StepFun / OpenAI 兼容** provider）。
5. **发布**：右上角「发布」→「分享」→ 打开分享链接 → 复制 URL。

自检问题（知识库里都能查到答案）：

```text
HNSW 向量索引的建表语句是什么？
混合检索（向量 + 全文）如何用 RRF 融合？
端侧 INT8 量化会损失多少召回率？
```

---

## 3. 自动化路径（脚本，5 分钟）

```bash
cd Dify

# 3.1 建知识库 + 上传 4 篇文档
#     API Key 在 Dify -> 知识库 -> API -> Knowledge API key 获取
export DIFY_BASE_URL=https://cloud.dify.ai
export DIFY_API_KEY=app-xxxxxxxxxxxx
export DIFY_EMBEDDING_PROVIDER=tongyi
export DIFY_EMBEDDING_MODEL=text-embedding-v3
python scripts/setup_knowledge.py dataset
# 输出：DIFY_DATASET_ID=xxxxxxxx

# 3.2 导入 DSL 并绑定知识库
#     console token：浏览器 DevTools -> Application -> Cookies -> console-token
export DIFY_CONSOLE_TOKEN=xxxxxxxxxxxx
python scripts/setup_knowledge.py app --dataset-id xxxxxxxxxxxxxxxx
```

脚本只依赖 Python 标准库，`python scripts/setup_knowledge.py --help` 查看全部参数。

> 若 Dify Cloud 开启了验证码登录，3.2 会失败——此时直接走 §2 的第 3 步 UI 导入即可，
> 效果完全一样。

---

## 4. 应用设计说明

```
开始 ──► 知识检索(top_k=4) ──► LLM(带 context) ──► 直接回复
```

- **知识检索**：`retrieval_mode=multiple`，`top_k=4`，不开启 rerank（避免依赖额外 provider）。
- **LLM 提示词**（`app.yml` → `llm` 节点 → `prompt_template`）：

  ```text
  你是 OceanBase / seekdb 向量数据库的资深工程师……
  请严格依据【知识库上下文】回答问题，引用上下文中的原文片段并给出出处标题。
  如果上下文不足以回答，请明确说明「知识库中没有覆盖这一点」……
  ```

  这条约束是为了防止模型在知识库没覆盖时编造 API 名称。
- **开场白 + 推荐问题**：已在 `features` 中配置，用户一进来就知道能问什么。
- `dataset_ids` 初始为空，导入后在节点里选一次知识库即可（或用 §3 脚本自动绑定）。

---

## 5. 截图清单（放到 `screenshots/`）

| 文件名 | 内容 |
| --- | --- |
| `01-knowledge-dataset.png` | 知识库列表 + 文档分段数 + 已向量化状态 |
| `02-app-canvas.png` | 应用编排画布（开始→知识检索→LLM→回复） |
| `03-chat-share.png` | 分享链接打开后的对话截图（带知识库命中的答案） |
| `04-publish.png` | 发布面板里的分享链接 |

> 截图必须来自你自己的 Dify 账号，评测会点开链接核验，链接失效直接扣分。

---

## 6. 知识库原文索引

| 文件 | 内容要点 |
| --- | --- |
| `kb/01-seekdb-向量库速查.md` | `VECTOR(n)` 列、`FULLTEXT INDEX ... PARSER ik`、`VECTOR INDEX ... type=hnsw lib=vsag`（m/ef_construction/ef_search）、`dbms_index_manager.refresh()`、距离度量与调参表 |
| `kb/02-混合检索与RRF.md` | `@search_parm` 协议、`DBMS_HYBRID_SEARCH.GET_SQL`、RRF 公式与 k=60、两路召回放大策略、维度一致性坑 |
| `kb/03-端侧向量化与量化对比.md` | bge-small-zh-v1.5（512 维）、INT8 22.8 MiB / Recall@5 0.917 与 FP32 持平、WebGPU→WASM 回退、离线权重与单线程 |
| `kb/04-AMD-GPU加速HNSW.md` | hipVS/CAGRA 基线对比、优化项与 3.33x 建图模型、recall 红线 0.005、参数扫描档位、AMD 机器复跑步骤 |

四篇文档同时是 **加赛（向量数据库）** 的技术底稿，可直接在答辩时复用。
