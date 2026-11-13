# 技术说明 · 端侧 AI 知识库

## 1. 模型与量化

| 项 | 值 |
| --- | --- |
| 模型 | `Xenova/bge-small-zh-v1.5`（BAAI bge-small-zh-v1.5 的 ONNX 转换） |
| 固定版本 | revision `75c43b069aac4d136ba6bc1122f995fedcfd2781` |
| 向量维度 | 512，cosine，L2 归一化 |
| 量化方式 | ONNX 静态 INT8 与 FP16，两种权重均由模型仓库提供 |
| 文件体积 | FP32 90.5 MiB / FP16 45.3 MiB / INT8 22.8 MiB |
| 压缩比 | FP16 2.00x，INT8 3.97x |

量化质量用同一浏览器、同一语料（12 段）和 6 条查询做精确余弦 Top-5：

| 指标 | INT8 | FP32 |
| --- | --- | --- |
| Recall@5 | 0.917 | 0.917 |
| Top-5 重合度 | 96.7% | — |
| 12 次查询向量化 | 124 ms | — |

质量没有下降；重合度损失来自一条边界样本的排名互换。

## 2. 端侧运行

- 运行时：`@huggingface/transformers` 3.8.1（Transformers.js）。
- 后端选择：
  1. 检测 `navigator.gpu.requestAdapter()`；
  2. 可用则加载 FP16 + `device: "webgpu"`；
  3. 初始化或推理失败则捕获异常，加载 INT8 + `device: "wasm"`，界面徽标显示当前后端。
- 离线资源：模型放在 `public/models/`；ONNX Runtime 的 `.wasm` / `.mjs` 在
  `npm run build` 前复制到 `public/ort/`，并设置
  `env.backends.onnx.wasm.wasmPaths`，不请求 jsDelivr。
- 线程：`numThreads = 1`，避免依赖 COOP/COEP 响应头。

实测（Edge headless，WASM，INT8）：模型加载 594 ms（浏览器缓存命中），
12 个片段向量化 748 ms，约 2 447 字符/秒。首次加载需下载 22.8 MiB。

## 3. seekdb 使用

集合 `browser_knowledge_base`：

```sql
CREATE TABLE `browser_knowledge_base` (
  id VARBINARY(512) PRIMARY KEY NOT NULL,
  document STRING,
  embedding VECTOR(512),
  metadata JSON,
  FULLTEXT INDEX idx_fts (document)
    WITH PARSER ik PARSER_PROPERTIES=(ik_mode='smart'),
  VECTOR INDEX idx_vec (embedding)
    WITH(distance=cosine, type=hnsw, lib=vsag,
         m=16, ef_construction=200, ef_search=64)
) ORGANIZATION = HEAP
```

- 写入：`collection.upsert({ids, embeddings, documents, metadatas})`，每 64 条一批；
  片段 ID 为内容 SHA-256 前 20 位，重复导入不会产生重复文档。
- 刷新：写入后调用 `collection.refresh_index()`（内部执行
  `CALL dbms_index_manager.refresh()`），保证新文档立即可检索。
- 检索：`collection.hybridSearch()`，`query.whereDocument.$contains` 走全文分支，
  `knn.queryEmbeddings` 走向量分支，`rank.rrf` 在 seekdb 内融合，**不是**客户端
  分别取两路再拼合。
- 状态：集合是唯一知识库；页面维护当前语料计数与导入/查询状态，`reset()`
  清空集合。切换语料时按内容哈希增量 upsert。

## 4. 验证与限制

- 前端：TypeScript 类型检查通过，Vite 生产构建通过。
- 浏览器：Playwright + Edge 实测 WASM INT8 加载、12 段向量化、质量对比通过。
- seekdb：`tools/verify_seekdb_contract.py` 在真实 seekdb 内核上验证了建表、
  INSERT、`DBMS_HYBRID_SEARCH.GET_SQL` 计划生成、全文分支返回与 COUNT。
- 本机 Windows 的 seekdb-js 嵌入式绑定在 `open()` 阻塞，HNSW 索引刷新返回
  `code=4012` 超时；这是本机 Windows build 的限制。Linux/macOS 使用默认
  嵌入式模式，或任意平台用 `SEEKDB_MODE=server` + Docker 复跑完整近似检索。

## 5. 复现

```bash
cd stepfun
npm install
npm run model:fetch
npm run typecheck
npm run build
npm run serve
```

质量对比：页面「运行质量对比」需要 FP32 基线：

```bash
npm run model:fetch -- --fp32
```

seekdb SQL 契约验证：

```bash
python tools/verify_seekdb_contract.py
```
