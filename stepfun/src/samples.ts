export interface SampleDocument {
  id: string;
  title: string;
  text: string;
  source: string;
}

export interface SampleQuery {
  query: string;
  expected: string[];
}

export const SAMPLE_DOCUMENTS: SampleDocument[] = [
  {
    id: "seekdb-overview",
    title: "seekdb 是什么",
    source: "sample/seekdb-overview.md",
    text: "seekdb 是 OceanBase 推出的 AI 原生数据库，面向向量、全文与结构化数据混合检索。它提供嵌入式与 server 两种运行模式，既可以作为本地文件数据库使用，也可以作为独立服务部署。seekdb-js 是其 JavaScript/TypeScript SDK，支持集合、向量索引、全文索引和混合检索。",
  },
  {
    id: "hybrid-search",
    title: "混合检索与 RRF",
    source: "sample/hybrid-search.md",
    text: "混合检索同时执行向量相似度检索与全文关键词检索，再把两路结果融合。seekdb-js 的 hybridSearch 使用 RRF（Reciprocal Rank Fusion）合并候选：同一文档如果在向量和全文两路都排名靠前，融合后的排名会更高。混合检索适合既包含语义意图、又包含明确关键词的查询。",
  },
  {
    id: "hnsw",
    title: "HNSW 向量索引",
    source: "sample/hnsw.md",
    text: "HNSW 是一种分层可导航小世界图索引。它把向量组织成多层近邻图，查询时从稀疏的上层快速接近目标区域，再在底层做精细搜索。HNSW 的构建参数通常包括 M、ef_construction，查询参数包括 ef_search。更大的 ef_search 通常带来更高召回率，但会增加查询延迟。",
  },
  {
    id: "embeddings",
    title: "文本向量化",
    source: "sample/embeddings.md",
    text: "文本向量化把一段文字映射为固定维度的浮点向量，使语义相近的文本在向量空间中距离更近。bge-small-zh-v1.5 是面向中文的轻量 embedding 模型，输出 512 维向量。文档与查询必须使用同一个模型和相同的归一化方式，否则向量空间不一致，检索结果不可比。",
  },
  {
    id: "quantization",
    title: "INT8 与 FP16 量化",
    source: "sample/quantization.md",
    text: "INT8 量化把 FP32 权重映射到 8 位整数，模型体积约为原来的四分之一；FP16 使用 16 位浮点，体积约为原来的一半。量化可以降低下载体积、内存占用和部分推理延迟，但可能带来少量精度损失。量化后应在同一评测集上比较 Recall@K 或 nDCG@K，不能只看体积。",
  },
  {
    id: "webgpu",
    title: "浏览器 WebGPU 推理",
    source: "sample/webgpu.md",
    text: "WebGPU 为浏览器提供接近原生 GPU 的计算能力。Transformers.js 可以把 ONNX 模型放到 WebGPU 执行，从而加速 embedding 推理。WebGPU 在不同浏览器和显卡上的算子支持并不完全一致；生产应用应检测 navigator.gpu 与适配器，失败时自动降级到 WASM，并在界面中明确提示当前后端。",
  },
  {
    id: "wasm",
    title: "WASM 回退路径",
    source: "sample/wasm.md",
    text: "WebAssembly 是浏览器的可移植执行格式。ONNX Runtime Web 的 WASM 后端不依赖 GPU，兼容性最好，适合作为 WebGPU 不可用时的回退方案。WASM 可以使用 SIMD 和多线程，但多线程需要跨源隔离响应头；没有这些响应头时，单线程 WASM 更稳定。",
  },
  {
    id: "chunking",
    title: "文档切分策略",
    source: "sample/chunking.md",
    text: "长文档需要切分成较小的片段再向量化。常见做法是按段落或固定字符数切分，并保留少量重叠，避免一个完整语义被切断。片段过大会稀释主题，片段过小会丢失上下文。每个片段应保留文档 ID、标题、序号和来源，便于检索后回溯原文。",
  },
  {
    id: "index-refresh",
    title: "增量写入与索引刷新",
    source: "sample/index-refresh.md",
    text: "新文档写入后，向量索引和全文索引需要刷新才能被立即检索到。seekdb-js 提供 refresh_index 方法，用于让最新写入对查询可见。应用应把写入和刷新放在同一个用户操作流程中，并在界面上显示刷新状态；连续导入时还要避免重复 ID 覆盖已有文档。",
  },
  {
    id: "rrf",
    title: "RRF 融合公式",
    source: "sample/rrf.md",
    text: "RRF 为每个候选计算 1/(k+rank) 的分数并累加，k 是平滑常数。它只依赖排名，不依赖不同检索通道的原始分数，因此很适合融合向量距离和 BM25 分数。RRF 的缺点是丢弃了原始分数的幅度信息；如果两路分数尺度稳定，也可以使用加权融合。",
  },
  {
    id: "privacy",
    title: "端侧推理与隐私",
    source: "sample/privacy.md",
    text: "端侧推理意味着模型在用户设备上执行，原始文本和查询不需要发送到云端推理服务。它降低了数据外泄风险，也减少了网络往返延迟。但模型文件仍需下载，首次加载会占用时间和带宽；应用应把模型缓存到浏览器 Cache Storage，并区分首次加载与预热后的性能。",
  },
  {
    id: "benchmark",
    title: "检索质量评测",
    source: "sample/benchmark.md",
    text: "检索质量常用 Recall@K 与 nDCG@K 衡量。Recall@K 表示前 K 个结果中覆盖了多少相关文档；nDCG@K 进一步考虑相关文档的排名位置。评测时应固定语料、查询集、切分方式和 embedding 模型，分别记录量化前后与不同后端下的结果，并报告中位数而不是只挑最快一次。",
  },
];

export const SAMPLE_QUERIES: SampleQuery[] = [
  { query: "向量和关键词怎么一起检索", expected: ["hybrid-search", "rrf"] },
  { query: "浏览器没有 GPU 时怎么运行模型", expected: ["wasm", "webgpu"] },
  { query: "INT8 量化后模型小多少", expected: ["quantization"] },
  { query: "新导入的文档为什么搜不到", expected: ["index-refresh"] },
  { query: "长文章应该怎么切分", expected: ["chunking"] },
  { query: "HNSW 的 ef_search 有什么影响", expected: ["hnsw"] },
];
