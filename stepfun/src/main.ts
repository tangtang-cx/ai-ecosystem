import { Embedder, type LoadProgress } from "./embedder";
import { addDocuments, health, reset, search, type SearchHit } from "./api";
import { COLLECTION_NAME, formatBytes, MODEL_SIZES, type Precision } from "./config";
import { SAMPLE_DOCUMENTS, SAMPLE_QUERIES } from "./samples";

interface Chunk {
  id: string;
  title: string;
  text: string;
  source: string;
}

const embedder = new Embedder();
let docs: Chunk[] = [];
let corpusCount = 0;

const $ = <T extends HTMLElement>(id: string): T => {
  const element = document.getElementById(id);
  if (!element) throw new Error(`missing element #${id}`);
  return element as T;
};

const dom = {
  backendBadge: $("backendBadge"),
  dbBadge: $("dbBadge"),
  docInput: $<HTMLTextAreaElement>("docInput"),
  queryInput: $<HTMLInputElement>("queryInput"),
  importBtn: $<HTMLButtonElement>("importBtn"),
  searchBtn: $<HTMLButtonElement>("searchBtn"),
  loadSamples: $<HTMLButtonElement>("loadSamples"),
  qualityBtn: $<HTMLButtonElement>("qualityBtn"),
  importStatus: $("importStatus"),
  importStatusText: $("importStatusText"),
  importProgress: $("importProgress"),
  importProgressBar: $("importProgressBar"),
  searchStatus: $("searchStatus"),
  searchStatusText: $("searchStatusText"),
  results: $("results"),
  corpusCount: $("corpusCount"),
  chunkCount: $("chunkCount"),
  importMs: $("importMs"),
  writeMs: $("writeMs"),
  metricLoad: $("metricLoad"),
  metricModel: $("metricModel"),
  metricEmbed: $("metricEmbed"),
  metricEmbedRate: $("metricEmbedRate"),
  metricWrite: $("metricWrite"),
  metricQueryEmbed: $("metricQueryEmbed"),
  metricSearch: $("metricSearch"),
  metricE2E: $("metricE2E"),
  qualityHint: $("qualityHint"),
  qualityOutput: $<HTMLPreElement>("qualityOutput"),
};

function setStatus(target: "import" | "search", state: "idle" | "busy" | "ok" | "error", text: string): void {
  const element = target === "import" ? dom.importStatus : dom.searchStatus;
  const label = target === "import" ? dom.importStatusText : dom.searchStatusText;
  element.classList.remove("is-busy", "is-ok", "is-error");
  if (state !== "idle") element.classList.add(`is-${state}`);
  label.textContent = text;
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function chunkText(raw: string): Promise<Chunk[]> {
  const blocks = raw
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean);
  const chunks: Chunk[] = [];
  const maxChars = 460;
  const overlap = 80;

  for (const block of blocks) {
    const title = block.split("\n")[0].slice(0, 42) || "未命名片段";
    if (block.length <= maxChars) {
      chunks.push({
        id: `doc-${(await sha256(block)).slice(0, 20)}`,
        title,
        text: block,
        source: "本地粘贴",
      });
      continue;
    }
    for (let start = 0; start < block.length; start += maxChars - overlap) {
      const text = block.slice(start, start + maxChars).trim();
      if (text.length < 20) continue;
      chunks.push({
        id: `doc-${(await sha256(text)).slice(0, 20)}`,
        title: `${title} · ${Math.floor(start / (maxChars - overlap)) + 1}`,
        text,
        source: "本地粘贴（长文切分）",
      });
    }
  }
  return chunks;
}

async function ensureModel(): Promise<void> {
  if (embedder.ready) return;
  dom.backendBadge.textContent = "加载模型…";
  dom.backendBadge.className = "badge is-warn";
  await embedder.init(updateModelProgress);
  updateModelBadge();
}

function updateModelProgress(progress: LoadProgress): void {
  if (progress.phase === "download") {
    const percent = progress.progress ? Math.round(progress.progress) : null;
    dom.backendBadge.textContent = percent === null ? "下载模型…" : `下载模型 ${percent}%`;
    dom.backendBadge.className = "badge is-warn";
  } else if (progress.phase === "fallback") {
    dom.backendBadge.textContent = "回退到 WASM";
    dom.backendBadge.className = "badge is-warn";
  }
  setStatus("import", "busy", progress.message);
}

function updateModelBadge(): void {
  const precision = embedder.precision.toUpperCase() as Precision | string;
  const bytes = MODEL_SIZES[embedder.precision as Precision] ?? MODEL_SIZES.int8;
  dom.backendBadge.textContent = `${embedder.backend.toUpperCase()} · ${precision}`;
  dom.backendBadge.className = "badge is-ready";
  dom.metricLoad.textContent = formatMs(embedder.loadMs);
  dom.metricModel.textContent = `${precision} · ${formatBytes(bytes)}`;
  dom.metricModel.title = `模型 ${MODEL_SIZES[embedder.precision as Precision] ?? MODEL_SIZES.int8} bytes`;
}

async function refreshHealth(): Promise<void> {
  try {
    const result = await health();
    if (!result.ok) throw new Error(result.error || "seekdb unavailable");
    dom.dbBadge.textContent = `seekdb · ${result.count} 条`;
    dom.dbBadge.className = "badge is-ready";
    corpusCount = result.count;
    dom.corpusCount.textContent = `${result.count} 个片段`;
  } catch (error) {
    dom.dbBadge.textContent = "seekdb 未连接";
    dom.dbBadge.className = "badge is-error";
    dom.dbBadge.title = error instanceof Error ? error.message : String(error);
  }
}

async function importDocuments(): Promise<void> {
  const raw = dom.docInput.value.trim();
  if (!raw) {
    setStatus("import", "error", "请先粘贴要导入的文本");
    return;
  }

  dom.importBtn.disabled = true;
  dom.loadSamples.disabled = true;
  dom.importProgress.hidden = false;
  dom.importProgressBar.style.width = "4%";
  setStatus("import", "busy", "正在切分文本…");

  try {
    docs = await chunkText(raw);
    dom.chunkCount.textContent = String(docs.length);
    if (!docs.length) throw new Error("没有生成有效片段");

    await ensureModel();
    setStatus("import", "busy", `正在向量化 ${docs.length} 个片段…`);

    const embedStart = performance.now();
    const total = docs.length;
    const vectors: number[][] = [];
    let done = 0;
    for (let offset = 0; offset < total; offset += 8) {
      const batch = docs.slice(offset, offset + 8);
      const batchVectors = await embedder.embed(batch.map((chunk) => chunk.text), 8);
      vectors.push(...batchVectors);
      done += batch.length;
      dom.importProgressBar.style.width = `${Math.round((done / total) * 88) + 4}%`;
      setStatus("import", "busy", `向量化 ${done}/${total} 个片段…`);
    }
    const embedMs = performance.now() - embedStart;
    dom.importMs.textContent = formatMs(embedMs);
    dom.metricEmbed.textContent = formatMs(embedMs);
    dom.metricEmbedRate.textContent = `${Math.round(raw.length / (embedMs / 1000))} 字符/秒`;

    setStatus("import", "busy", "写入 seekdb 并刷新索引…");
    const writeStart = performance.now();
    const result = await addDocuments(
      docs.map((chunk, index) => ({
        id: chunk.id,
        title: chunk.title,
        text: chunk.text,
        source: chunk.source,
        embedding: vectors[index],
      })),
    );
    const writeMs = performance.now() - writeStart;
    dom.writeMs.textContent = formatMs(writeMs);
    dom.metricWrite.textContent = formatMs(writeMs);
    dom.importProgressBar.style.width = "100%";
    setStatus("import", "ok", `已写入 ${result.inserted} 个片段，索引已刷新`);
    await refreshHealth();
  } catch (error) {
    setStatus("import", "error", shortError(error));
  } finally {
    dom.importBtn.disabled = false;
    dom.loadSamples.disabled = false;
    setTimeout(() => {
      dom.importProgress.hidden = true;
      dom.importProgressBar.style.width = "0%";
    }, 1200);
  }
}

async function runSearch(): Promise<void> {
  const query = dom.queryInput.value.trim();
  if (!query) {
    setStatus("search", "error", "请输入查询");
    return;
  }

  dom.searchBtn.disabled = true;
  const started = performance.now();
  setStatus("search", "busy", "正在生成本地查询向量…");

  try {
    await ensureModel();
    const embedStart = performance.now();
    const [vector] = await embedder.embed([query]);
    const queryEmbedMs = performance.now() - embedStart;
    dom.metricQueryEmbed.textContent = formatMs(queryEmbedMs);

    setStatus("search", "busy", "seekdb 正在执行向量 + 全文混合检索…");
    const result = await search(query, vector, 5);
    const elapsed = performance.now() - started;
    dom.metricSearch.textContent = formatMs(result.elapsedMs);
    dom.metricE2E.textContent = formatMs(elapsed);
    renderResults(result.hits);
    setStatus("search", "ok", `返回 ${result.hits.length} 条结果`);
  } catch (error) {
    setStatus("search", "error", shortError(error));
    dom.results.innerHTML = `<div class="empty-state"><p>检索失败</p><small>${escapeHtml(shortError(error))}</small></div>`;
  } finally {
    dom.searchBtn.disabled = false;
  }
}

function renderResults(hits: SearchHit[]): void {
  if (!hits.length) {
    dom.results.innerHTML = `<div class="empty-state"><p>没有命中</p><small>换一个问法，或再导入一些相关文档。</small></div>`;
    return;
  }
  dom.results.innerHTML = hits
    .map((hit, index) => {
      const score = hit.score === null ? `#${index + 1}` : `RRF ${hit.score.toFixed(4)}`;
      return `
        <article class="result-card">
          <div class="result-top">
            <h3 class="result-title">${escapeHtml(hit.title || "未命名片段")}</h3>
            <span class="result-score">${escapeHtml(score)}</span>
          </div>
          <p class="result-text">${escapeHtml(hit.text)}</p>
          <div class="result-meta">
            <span>${escapeHtml(hit.id)}</span>
            <span>${escapeHtml(hit.source || "本地粘贴")}</span>
            ${hit.distance === null ? "" : `<span>distance ${hit.distance.toFixed(4)}</span>`}
          </div>
        </article>`;
    })
    .join("");
}

async function loadSampleCorpus(): Promise<void> {
  dom.docInput.value = SAMPLE_DOCUMENTS.map((doc) => `# ${doc.title}\n${doc.text}`).join("\n\n");
  const chunks = await chunkText(dom.docInput.value);
  dom.chunkCount.textContent = String(chunks.length);
  setStatus("import", "idle", `已载入 ${SAMPLE_DOCUMENTS.length} 段示例语料，点击“导入并向量化”写入 seekdb`);
}

async function runQualityBenchmark(): Promise<void> {
  dom.qualityBtn.disabled = true;
  dom.qualityOutput.hidden = false;
  dom.qualityOutput.textContent = "准备基准语料…";
  try {
    await ensureModel();
    const current = embedder;
    const baseline = new Embedder();
    dom.qualityOutput.textContent = "加载 FP32 基线模型（约 90 MB，首次较慢）…";
    await baseline.initFixed("fp32", "wasm", (progress) => {
      dom.qualityOutput.textContent = progress.message;
    });

    const texts = SAMPLE_DOCUMENTS.map((doc) => doc.text);
    const queries = SAMPLE_QUERIES.map((item) => item.query);
    dom.qualityOutput.textContent = "计算量化模型与 FP32 基线的文档向量…";
    const currentDocs = await current.embed(texts);
    const baselineDocs = await baseline.embed(texts);

    let currentRecall = 0;
    let baselineRecall = 0;
    let overlap = 0;
    const started = performance.now();
    for (const item of SAMPLE_QUERIES) {
      const [currentQuery] = await current.embed([item.query]);
      const [baselineQuery] = await baseline.embed([item.query]);
      const currentTop = topK(currentQuery, currentDocs, 5).map((index) => SAMPLE_DOCUMENTS[index].id);
      const baselineTop = topK(baselineQuery, baselineDocs, 5).map((index) => SAMPLE_DOCUMENTS[index].id);
      currentRecall += overlapCount(currentTop, item.expected) / item.expected.length;
      baselineRecall += overlapCount(baselineTop, item.expected) / item.expected.length;
      overlap += overlapCount(currentTop, baselineTop) / 5;
    }
    const queryMs = performance.now() - started;
    const count = SAMPLE_QUERIES.length;
    const currentLabel = current.precision.toUpperCase();
    const compression = (MODEL_SIZES.fp32 / MODEL_SIZES[current.precision as Precision]).toFixed(2);
    dom.qualityOutput.textContent = [
      `模型       ${currentLabel} vs FP32`,
      `模型体积   ${formatBytes(MODEL_SIZES[current.precision as Precision])} vs ${formatBytes(MODEL_SIZES.fp32)}（压缩 ${compression}x）`,
      `语料       ${SAMPLE_DOCUMENTS.length} 段 / 查询 ${count} 条 / Top-5`,
      `Recall@5   ${currentLabel} ${(currentRecall / count).toFixed(3)}  |  FP32 ${(baselineRecall / count).toFixed(3)}`,
      `Top-5 重合 ${(overlap / count * 100).toFixed(1)}%`,
      `查询耗时   ${formatMs(queryMs)}（${count * 2} 次本地 embedding，仅基准测试）`,
      "",
      "说明：质量对比在本地内存中做精确余弦排序，仅用于量化前后对比；正式检索仍由 seekdb 完成。",
    ].join("\n");
    await baseline.dispose();
  } catch (error) {
    dom.qualityOutput.textContent = `质量对比失败：${shortError(error)}\n\n如果缺少 FP32 模型，请运行：\n  npm run model:fetch -- --fp32`;
  } finally {
    dom.qualityBtn.disabled = false;
  }
}

function topK(query: number[], docs: number[][], k: number): number[] {
  return docs
    .map((vector, index) => ({ index, score: cosine(query, vector) }))
    .sort((left, right) => right.score - left.score)
    .slice(0, k)
    .map((item) => item.index);
}

function cosine(left: number[], right: number[]): number {
  let dot = 0;
  let leftNorm = 0;
  let rightNorm = 0;
  for (let index = 0; index < left.length; index += 1) {
    dot += left[index] * right[index];
    leftNorm += left[index] * left[index];
    rightNorm += right[index] * right[index];
  }
  return dot / (Math.sqrt(leftNorm) * Math.sqrt(rightNorm) || 1);
}

function overlapCount(left: string[], right: string[]): number {
  const rightSet = new Set(right);
  return left.filter((item) => rightSet.has(item)).length;
}

function shortError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

async function resetCorpus(): Promise<void> {
  if (!confirm("清空 seekdb 中的知识库？")) return;
  try {
    await reset();
    corpusCount = 0;
    dom.corpusCount.textContent = "0 个片段";
    dom.results.innerHTML = `<div class="empty-state"><p>知识库已清空</p><small>重新导入语料后即可检索。</small></div>`;
    setStatus("search", "idle", "等待查询");
    await refreshHealth();
  } catch (error) {
    setStatus("import", "error", shortError(error));
  }
}

dom.importBtn.addEventListener("click", () => void importDocuments());
dom.searchBtn.addEventListener("click", () => void runSearch());
dom.loadSamples.addEventListener("click", () => void loadSampleCorpus());
dom.qualityBtn.addEventListener("click", () => void runQualityBenchmark());
dom.queryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") void runSearch();
});
$("footerModel").addEventListener("dblclick", () => void resetCorpus());

// Show the database state immediately; model loading starts on first import/search.
void refreshHealth();
setStatus("import", "idle", "等待导入");
setStatus("search", "idle", "等待查询");
console.info("collection", COLLECTION_NAME);
