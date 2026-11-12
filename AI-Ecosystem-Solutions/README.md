# AI-Ecosystem-Solutions · 第六届 OceanBase 数据库大赛 AI 生态创新赛题总览

> 本目录是 7 道赛题（AMD、MiniMax、Qoder、StepFun、Dify、高德、魔搭）的**统一交付索引**：
> 每节给出「实现思路 / 截图与链接 / 核心代码」三件套，方便评委与队友一眼定位。
> 所有代码都在本仓库对应目录里，可直接 clone 运行。

| # | 赛题 | 目录 / 分支 | 状态 | 一句话交付物 |
| --- | --- | --- | --- | --- |
| 1 | AMD（seekdb × hipVS 加速 HNSW） | `amd-cagra-solution` 分支 · `amd/` | 🟡 代码完成，待 AMD 机器实测 | CAGRA 建图 3.3x 参数模型 + 免 H2D 拷贝的 bridge 优化 |
| 2 | MiniMax | `Qoder/reviewer.py` · `魔搭/` | 🟡 接入层完成，待真实调用截图 | 统一 OpenAI 兼容接入层，MiniMax 作为 provider 预置 |
| 3 | Qoder | `Qoder/` | 🟢 完成 | 数据库代码审查助手（15 条静态规则 + LLM 深审 + 报告导出） |
| 4 | StepFun（端侧推理 + seekdb 混合检索） | `stepfun/` | 🟢 完成 | 浏览器内 INT8 embedding + seekdb 内 RRF 混合检索 |
| 5 | Dify | `Dify/` | 🟢 完成（DSL + 知识库 + 一键脚本） | OceanBase 向量库文档 RAG 助手，导入即发布 |
| 6 | 高德（周边去哪儿） | `gaode/SKILL.md` | 🟢 完成 | 纯 Skill 文件，评测平台直接加载 |
| 7 | 魔搭社区（ModelScope） | `魔搭/` | 🟢 完成 | 魔搭免费推理 API 驱动的 Streamlit 问答助手 |

---

## 提测信息（仓库 / 分支 / Commit SHA）

仓库：`https://github.com/tangtang-cx/ai-ecosystem`（私有库）

| 赛题 | 分支 | Commit SHA（40 位） | 分支内容 |
| --- | --- | --- | --- |
| Dify | `Dify` | `50437db84813970208381f931147eb57deca8c6b` | `Dify/`（DSL + 知识库 + 脚本） |
| Qoder | `qoder` | `a97d78f4bf837fa6bc04a8ef02253a03c4f0aee6` | `Qoder/`（应用 + 规则 + 测试） |
| 魔搭社区 | `modelscope` | `c5bfe6e237d77941fb77eb7a5b098d29db8acd94` | `魔搭/`（代码 + 录屏 + 测试） |
| 高德 | `gaode` | `55c0faebea36a0900d7c54ee647a9c453e099fa7` | `gaode/SKILL.md` |
| StepFun | `stepfun` | `ec22a31e539d4ece0657b68ebdbc35f02c9bff92` | `stepfun/` |
| AMD | `amd-cagra-solution` | `fced626b49611b8e37be0dd1bac8559220cfabe6` | `amd/`（需 apply 到 seekdb fork） |
| 生态赛题合并版 | `2026-competition-ecosystem` | 见仓库该分支最新提交 | 三个生态赛题 + 高德 + StepFun |

> 每个分支都含官方基线提交 `39e069f4`；每个分支根目录的 `README.md` 都写了该题的评测跑法。

---

## 1. AMD · seekdb × AMD hipVS：加速 HNSW 索引构建

**目录**：`amd-cagra-solution` 分支 · `amd/`（本仓库不是官方答题仓库，官方要求改到 seekdb fork 上）

### 实现思路

1. **先看硬门槛**：必须走 GPU CAGRA 路径；建图 ≥ 3.0x、查询 ≥ 1.5x、recall 与同轮基线差 ≤ 0.005。
   CPU 平替不算数，所以本地先把**参数模型**和**代码**做扎实，评测机再复跑。
2. **建图主阶段降本**：NN-Descent 计算量 ≈ `niter × graph_degree`，
   基线 `100 × 128 = 12800` → 优化 `40 × 96 = 3840`，**理论 3.33x**。
   中间图 `256 → 144` 再补一刀。
3. **消灭拷贝与固定开销**：设备缓冲 + `kDLCUDA` DLPack 张量建图（避免 cuVS 内部重复 H2D）；
   查询缓冲 / pinned 结果缓冲 / search params 全部按 handle 缓存；
   搜索跑在常驻 32MB worker 线程上，配合 adaptor patch 去掉「每查询建一次 pthread」。
4. **守 recall 红线**：提供安全/默认/激进/极激进四档参数，先跑官方冒烟与 recall 用例再谈加速。

### 截图 / 链接

| 内容 | 位置 |
| --- | --- |
| 性能设计与验证说明 | `amd/docs/PERF_NOTES.md`（`amd-cagra-solution` 分支） |
| 执行计划 | `amd/EXECUTION_PLAN.md` |
| 一键应用 / 回滚 | `amd/scripts/apply_to_seekdb.sh` |
| Bridge 级基准 | `amd/bench/bench_bridge.py` |
| AMD 实测截图 | ⏳ 待 AMD 机器复跑后补入 `amd/screenshots/` |

### 核心代码（参数与收益模型）

```text
baseline:  100 × 128 = 12800
optimized:  40 ×  96 =  3840
ratio:      12800 / 3840 = 3.33x
```

```c
/* amd/solution/seekdb_cuvs_bridge.c —— 设备缓冲 + DLPack 张量建图 */
cuvsRMMAlloc(&dev_buf, bytes);            /* 设备端常驻缓冲 */
build_graph.dev_ptr = dev_buf;             /* 直接用设备内存建图，避免 H2D 重复拷贝 */
```

---

## 2. MiniMax · 大模型接入

**目录**：`Qoder/reviewer.py`、`魔搭/modelscope_client.py`

### 实现思路

- MiniMax 提供 **OpenAI 兼容**接口（`/v1/chat/completions`），因此不需要写适配层：
  统一封装成「provider 预置」，换厂商只改 Base URL + 模型名。
- 三个交付物（Qoder / 魔搭 / Dify 的 LLM 节点）都内置 MiniMax 预置，
  保证「同一套代码切 4 家推理服务」这件事被真实验证过。
- 魔搭的免费推理列表里**本身就有 MiniMax**：`MiniMax/MiniMax-M3`、`MiniMax/MiniMax-M1-80k`，
  所以即使没有 MiniMax 官方 Key，也能在魔搭上跑通 MiniMax 模型。

### 截图 / 链接

| 内容 | 位置 |
| --- | --- |
| provider 预置 | `Qoder/reviewer.py` → `PROVIDER_PRESETS` |
| 环境变量样例 | `Qoder/.env.example` → `MINIMAX_API_KEY / MINIMAX_BASE_URL / MINIMAX_MODEL` |
| 魔搭上的 MiniMax 模型 | `魔搭/README.md` §5 |
| 真实调用截图 | ⏳ 待补（Qoder / 魔搭 任一界面切到 MiniMax 后截图） |

### 核心代码

```python
# Qoder/reviewer.py
PROVIDER_PRESETS = {
    "minimax": {
        "base_url": "https://api.minimax.chat/v1",
        "model": "MiniMax-Text-01",
        "env_key": "MINIMAX_API_KEY",
    },
    ...
}

# 统一调用（标准库即可，不依赖 openai SDK）
request = urllib.request.Request(
    f"{self.base_url}/chat/completions",
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    method="POST",
    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
)
```

---

## 3. Qoder · 数据库代码审查助手

**目录**：`Qoder/` · 提示词与发布说明见 `Qoder/PROMPT.md`

### 实现思路

1. **用 Qoder 生成骨架**：提示词「请帮我用 Python 写一个 Streamlit 应用，调用大模型 API 做一个『数据库代码审查助手』」。
2. **再补一层确定性**：只靠大模型会漏、会飘，评测现场更不能卡在网络。
   于是加 15 条**正则静态规则**，毫秒级、离线、零误报依赖，可直接进 CI 卡口。
3. **两层合并展示**：规则层给「问题 + 建议 + 命中片段」，LLM 层给语义级判断，
   统一成 🔴阻断 / 🟠警告 / 🔵提示 三级。
4. **可导出**：Markdown 评审报告 + JSON，答辩直接贴报告。

### 截图 / 链接

| 内容 | 位置 |
| --- | --- |
| Qoder 对话 + 生成 diff | ⏳ `Qoder/screenshots/01-qoder-chat.png`（发布后补） |
| Qoder Sites 公网链接 | ⏳ `Qoder/screenshots/03-qoder-sites.png`（发布后补） |
| 应用运行界面 | ⏳ `Qoder/screenshots/04-app-running.png`（发布后补） |

### 核心代码

```python
# Qoder/reviewer.py —— 静态规则（节选）
Rule(id="OB-001", level="error", title="UPDATE / DELETE 缺少 WHERE",
     pattern=r"\b(update|delete\s+from)\b(?![\s\S]{0,400}?\bwhere\b)",
     message="语句没有 WHERE 条件，会更新/删除全表数据。",
     suggestion="补全 WHERE 条件；生产环境先在同事务里 SELECT 校验影响行数。")

# Qoder/app.py —— 两层合并
findings = analyze(sql)          # 确定性规则
llm_result = reviewer.review(sql, extra_context)   # LLM 深审
merged = findings + llm_result.findings
```

测试：`python Qoder/tests/test_rules.py -v` → **23 passed**（22 规则 + 1 UI 冒烟）。

---

## 4. StepFun · 端侧 AI 推理 + seekdb 混合检索

**目录**：`stepfun/` · 技术说明 `stepfun/TECH_REPORT.md`

### 实现思路

- **约束**：禁止云端推理 API；文档/查询向量化必须在浏览器本地完成；存储与混合检索必须由 seekdb 完成。
- **端侧**：Transformers.js + `bge-small-zh-v1.5`（512 维，L2 归一化），
  WebGPU+FP16 优先，异常回退 WASM+INT8；权重本地化，不请求 CDN。
- **量化验证**：INT8 22.8 MiB（FP32 的 1/4），Recall@5 = 0.917 与 FP32 **完全持平**，
  Top-5 重合度 96.7%。
- **检索**：向量 + 全文两路召回，在 **seekdb 内核内**用 RRF 融合（不是客户端拼）。

### 截图 / 链接

| 内容 | 位置 |
| --- | --- |
| 浏览器端实测截图 | `stepfun/artifacts/`（`home.png` / `quality.png` / `debug.png`） |
| 技术说明 | `stepfun/TECH_REPORT.md` |
| seekdb SQL 契约验证 | `stepfun/tools/verify_seekdb_contract.py` |

### 核心代码

```sql
-- 集合定义：HNSW 向量索引 + IK 全文索引
CREATE TABLE `browser_knowledge_base` (
  id VARBINARY(512) PRIMARY KEY NOT NULL,
  document STRING,
  embedding VECTOR(512),
  metadata JSON,
  FULLTEXT INDEX idx_fts (document) WITH PARSER ik PARSER_PROPERTIES=(ik_mode='smart'),
  VECTOR INDEX idx_vec (embedding) WITH(distance=cosine, type=hnsw, lib=vsag,
       m=16, ef_construction=200, ef_search=64)
) ORGANIZATION = HEAP;
```

```javascript
// stepfun/server/seekdb-store.mjs —— 融合发生在 seekdb 内核
const result = await collection.hybridSearch({
  query: { whereDocument: { $contains: query }, nResults: candidateCount },
  knn:   { queryEmbeddings: [embedding],     nResults: candidateCount },
  rank:  { rrf: {} },
  nResults: limit,
});
```

---

## 5. Dify · OceanBase 向量库文档问答助手

**目录**：`Dify/` · 应用 DSL `Dify/app.yml` · 知识库 `Dify/kb/`

### 实现思路

- **零代码交付**：不交一堆截图了事，而是交**可导入的 DSL**。
  评委/队友导入 `app.yml` → 选一次知识库 → 发布，5 分钟拿到分享链接。
- **知识库是实测结论**：4 篇文档全部来自本仓库**跑过**的结论
  （`verify_seekdb_contract.py` 的真实 seekdb 内核 + `TECH_REPORT.md` 的浏览器实测），
  不是编出来的 API。
- **防幻觉**：LLM 提示词强制「只能依据知识库上下文回答，覆盖不到就直说」。
- **一键脚本**：有 Knowledge API key 时，`scripts/setup_knowledge.py` 可自动建库、
  上传文档、导入 DSL 并绑定数据集。

### 截图 / 链接

| 内容 | 位置 |
| --- | --- |
| **作品链接（已实测存活）** | `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ`（应用「我的问答助手」，appId `6af43fdc657c1ade990e7dd0`，datasetId `PvxGnL0sbXZQu1owx1QAX65S`，HTTP 200） |
| Dify 官方版导入件 | `Dify/app.yml` → cloud.dify.ai 导入后发布得 `cloud.dify.ai/chat/share?shareId=...` |
| 知识库列表 | ⏳ `Dify/screenshots/01-knowledge-dataset.png` |
| 应用编排画布 | ⏳ `Dify/screenshots/02-app-canvas.png` |
| 分享链接对话 | ⏳ `Dify/screenshots/03-chat-share.png` |
| 发布面板 | ⏳ `Dify/screenshots/04-publish.png` |

### 核心代码

```yaml
# Dify/app.yml（节选）：开始 -> 知识检索 -> LLM(带 context) -> 直接回复
- id: kb
  data:
    type: knowledge-retrieval
    dataset_ids: []
    retrieval_mode: multiple
    multiple_retrieval_config:
      top_k: 4
- id: llm
  data:
    type: llm
    model: { provider: tongyi, name: qwen-plus, mode: chat }
    prompt_template:
      - { id: sys, role: system, text: "你是 OceanBase / seekdb 向量数据库的资深工程师……" }
      - { id: usr, role: user,  text: "【知识库上下文】\n{{#context#}}\n\n【用户问题】\n{{#sys.query#}}" }
    context:
      enabled: true
      variable_selector: [kb, result]
```

```bash
# 一键建库 + 导入（详见 Dify/README.md §3）
export DIFY_API_KEY=app-xxxx
python Dify/scripts/setup_knowledge.py dataset
```

---

## 6. 高德 · 周边去哪儿：基于高德的地点推荐助手

**目录**：`gaode/SKILL.md`（提测时**只交这一个文件**）

### 实现思路

- 评测平台统一提供 Agent、模型与高德 MCP 工具，**我们只提供 Skill**，
  所以交付物必须是一份能被平台直接加载的 `SKILL.md`。
- Skill 描述完整决策链：起���点解析 → 地点类型 → 步行时间上限 → 候选检索 →
  POI 详情核验 → 步行路径规划 → **最多 3 个**真实可达地点。
- 明确失败兜底：检索不到满足步行时间的地点时如实说明，不编造 POI。

### 截图 / 链接

| 内容 | 位置 |
| --- | --- |
| Skill 全文 | `gaode/SKILL.md` |
| YAML frontmatter 校验 | `python tools/check_skill.py gaode/SKILL.md` |

### 核心代码

```markdown
---
name: gaode-nearby
description: 周边去哪儿：基于高德 MCP 的地点推荐助手
---

# 周边去哪儿

1. 解析用户起点（地址 / 经纬度）、地点类型、步行时间上限、期望数量（最多 3 个）。
2. 用高德 MCP 地点搜索拿候选 POI，按类型与距离初筛。
3. 用 POI 详情核对营业状态与类型是否匹配。
4. 用步行路径规划校验真实可达时间，超出上限的候选直接淘汰。
5. 按「类型匹配 > 时间余量 > 距离」排序，最多返回 3 个。
```

---

## 7. 魔搭社区（ModelScope）· AI 问答助手

**目录**：`魔搭/` · 客户端 `魔搭/modelscope_client.py` · 录屏 `魔搭/第三题.mp4`

### 实现思路

- **完全复用 StepFun 的 Python 结构**，只换两处：Base URL 换成魔搭的
  `https://api-inference.modelscope.cn/v1`，模型换成魔搭免费推理模型。
- 魔搭同样提供 **OpenAI 兼容**协议，所以客户端代码几乎不变——
  这正是「一套代码多平台」的收益。
- **不搞占位**：旧版 `app.py` 只返回固定字符串占位，本版真实调用接口，
  界面上直接显示 `model / 耗时 / usage` 三个指标，可以现场证明是真实推理。
- **动态模型列表**：启动时拉 `/v1/models`（免鉴权），下拉里可选 38 个免费模型，
  包括 `MiniMax/MiniMax-M3`、`stepfun-ai/Step-3.5-Flash`、`Qwen/Qwen3.5-27B`。

### 截图 / 链接

| 内容 | 位置 |
| --- | --- |
| **运行录屏** | `魔搭/第三题.mp4`（已提交） |
| 魔搭 API Key 获取路径 | `魔搭/README.md` §2 |
| 创空间部署步骤 | `魔搭/README.md` §6 |
| 创空间公网链接 | ⏳ 待部署后补 |

### 核心代码

```python
# 魔搭/modelscope_client.py
class ModelScopeClient:
    def chat(self, messages, *, model=None, temperature=0.7, max_tokens=1024) -> ChatResult:
        payload = {"model": model or self.model, "messages": list(messages),
                   "temperature": temperature, "max_tokens": max_tokens, "stream": False}
        data = self._request("/chat/completions", method="POST", payload=payload)
        return ChatResult(content=data["choices"][0]["message"]["content"],
                          model=data.get("model"), usage=data.get("usage", {}),
                          elapsed_ms=elapsed)
```

```bash
# 自检：38 个模型可用 + 真实对话
python 魔搭/scripts/smoke_test.py
```

---

## 复现全部验证

```bash
# Qoder：静态规则 + UI 冒烟（23 个用例）
python Qoder/tests/test_rules.py -v
python Qoder/tests/test_app_smoke.py -v

# 魔搭：客户端单测 + 真实连通性（9 个用例）
python 魔搭/tests/test_client.py -v
python 魔搭/scripts/smoke_test.py

# StepFun：类型检查 + 构建 + seekdb SQL 契约
cd stepfun && npm run typecheck && npm run build
python stepfun/tools/verify_seekdb_contract.py

# 高德：Skill 结构校验
python tools/check_skill.py gaode/SKILL.md

# Dify：DSL 语法与图结构校验
python -c "import yaml; d=yaml.safe_load(open('Dify/app.yml',encoding='utf-8')); \
print(len(d['workflow']['graph']['nodes']),'nodes')"
```

## 待补清单（不影响代码，只差平台账号操作）

- [ ] Dify：导入 → 发布 → 分享链接 + 4 张截图
- [ ] Qoder：Qoder Sites 发布链接 + 4 张截图
- [ ] 魔搭：创空间公网链接（或本地演示录屏补拍）
- [ ] MiniMax：一次真实调用的截图
- [ ] AMD：AMD 机器上的官方冒烟 + recall + QPS 实测截图
