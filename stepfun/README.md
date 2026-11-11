# 端侧 AI 知识库 · 浏览器本地向量化 + seekdb 混合检索

2026 OceanBase 数据库大赛 **AI 生态创新 / 阶跃星辰** 赛题作品。

用户在浏览器里导入文本，应用使用 **Transformers.js** 在本地完成文档和查询的
embedding（优先 WebGPU + FP16，失败自动降级 WASM + INT8），把向量、原文和
元数据写入 **seekdb**，查询时由 seekdb 在数据库内完成 **向量 + 全文混合检索**，
并用 RRF 融合两路结果。

## 1. 快速启动

要求：Node.js ≥ 20，npm ≥ 10。

```bash
cd stepfun
npm install                 # .npmrc 已设置 legacy-peer-deps
npm run model:fetch         # 下载 INT8 + FP16 模型（约 71 MB）
npm run serve               # 构建前端并启动本地服务
# 打开 http://127.0.0.1:8787
```

默认使用 **seekdb 嵌入式模式**，数据库目录为 `stepfun/.data/seekdb`。

### Windows 说明

seekdb-js 的 Windows 原生绑定在本机初始化时会阻塞在 `open()`（V1.4.0 嵌入式
模式改为独立后台进程，该 Windows build 在本环境无法启动）。Windows 上请改用
**server 模式**：

```bash
docker compose up -d        # 启动 oceanbase/seekdb，端口 2881
# 另开终端
$env:SEEKDB_MODE="server"
npm run serve
```

Linux / macOS 直接使用默认 embedded 模式即可。

### 只用前端调试

```bash
npm run dev                 # Vite，http://127.0.0.1:5173
```

前端会把 `/api` 代理到 `127.0.0.1:8787`，所以仍需启动 `npm run server`。

## 2. 使用流程

1. 点击「载入示例语料」，或粘贴自己的文本（空行分段）。
2. 点击「导入并向量化」：浏览器本地生成向量，写入 seekdb 并刷新索引。
3. 输入问题点击「检索」：查询向量本地生成，seekdb 内完成 hybrid search。
4. 底部「量化与质量对比」可现场跑 INT8 vs FP32 的 Recall@5 对比。

## 3. 关键设计

| 层 | 实现 |
| --- | --- |
| 端侧推理 | `@huggingface/transformers` 3.8.1，`bge-small-zh-v1.5`，512 维 |
| 后端选择 | 有 WebGPU 时 FP16 + WebGPU；不可用/失败时 INT8 + WASM，并在界面标记 |
| 本地资源 | 模型和 ONNX Runtime WASM 全部从本站加载，不依赖 CDN |
| 数据库 | seekdb 嵌入式或 server 模式，`seekdb-js` 官方 SDK |
| 索引 | HNSW（cosine, m=16, ef_construction=200）+ IK 全文索引 |
| 混合检索 | `collection.hybridSearch()`，RRF 融合，检索在 seekdb 内完成 |
| 增量写入 | 片段 ID 为内容 SHA-256 前 20 位，`upsert` + `refresh_index()` |
| 质量评测 | 同一浏览器内加载 FP32 基线，精确余弦 Top-5，对比 Recall@5 与重合度 |

## 4. 本地实测

测试设备：Windows 11，Edge headless，WASM 后端（无 WebGPU）。

| 指标 | 结果 |
| --- | --- |
| INT8 模型加载（浏览器缓存命中） | 594 ms |
| 12 个片段向量化 | 748 ms（约 2 447 字符/秒） |
| INT8 vs FP32 Recall@5 | 0.917 vs 0.917 |
| INT8 vs FP32 Top-5 重合度 | 96.7% |
| 模型体积 | FP32 90.5 MiB → INT8 22.8 MiB（3.97x） |
| 12 次查询向量化 | 124 ms |

seekdb 侧：在真实 seekdb 内核上验证了建表 DDL、全文分支、向量分支的 SQL
计划生成与执行；本机 Windows 嵌入式绑定的 HNSW 索引刷新超时（`code=4012`），
因此**近似向量检索的完整链路需要在 Linux/macOS 或 Docker server 模式复跑**。
验证脚本见 `tools/verify_seekdb_contract.py`。

## 5. 目录

```text
stepfun/
├── src/                 # 浏览器端：embedding、UI、API
├── server/              # 本地 Node 服务 + seekdb 适配器
├── public/models/       # 本地模型（INT8/FP16）
├── scripts/             # 模型下载、ORT 资源复制
├── tools/               # seekdb SQL 契约验证
├── test/                # Playwright UI / 质量 / 指标脚本
├── docker-compose.yml   # server 模式
├── TECH_REPORT.md       # 一页技术说明
└── README.md
```

## 6. 提交

按官方要求把 `stepfun/` 放入 `2026-competition-ecosystem` 分支，提交仓库 URL、
分支和完整 commit SHA。不要提交 `.data/`、`node_modules/`、`.env`。
