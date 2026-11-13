import { createServer } from "node:http";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { SeekdbStore } from "./seekdb-store.mjs";

try {
  process.loadEnvFile?.(".env");
} catch {
  // .env is optional.
}

const ROOT = resolve(fileURLToPath(new URL("../", import.meta.url)));
const DIST = join(ROOT, "dist");
const PORT = Number(process.env.PORT || 8787);
const MAX_BODY = 32 * 1024 * 1024;
const store = new SeekdbStore();

let ready = false;
let initError = null;
const initPromise = store
  .init()
  .then(() => {
    ready = true;
    console.log("seekdb ready");
  })
  .catch((error) => {
    initError = error;
    console.error("seekdb init failed:", error.message);
  });

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".wasm": "application/wasm",
  ".onnx": "application/octet-stream",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

function json(response, status, body) {
  const payload = JSON.stringify(body);
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(payload),
    "cache-control": "no-store",
  });
  response.end(payload);
}

async function readJson(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_BODY) throw new HttpError(413, "请求体过大");
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new HttpError(400, "请求体不是合法 JSON");
  }
}

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function assertReady() {
  if (initError) throw new HttpError(503, `seekdb 未连接：${initError.message}`);
  if (!ready) throw new HttpError(503, "seekdb 正在初始化");
}

function validateDocuments(value) {
  if (!Array.isArray(value) || value.length === 0) throw new HttpError(400, "documents 不能为空");
  if (value.length > 256) throw new HttpError(400, "一次最多写入 256 个片段");
  return value.map((item, index) => {
    if (!item || typeof item !== "object") throw new HttpError(400, `documents[${index}] 非法`);
    const { id, text, title, source, embedding } = item;
    if (typeof id !== "string" || !id.trim()) throw new HttpError(400, `documents[${index}].id 非法`);
    if (typeof text !== "string" || text.trim().length < 2) throw new HttpError(400, `documents[${index}].text 非法`);
    if (typeof title !== "string") throw new HttpError(400, `documents[${index}].title 非法`);
    if (typeof source !== "string") throw new HttpError(400, `documents[${index}].source 非法`);
    if (!Array.isArray(embedding) || embedding.length !== 512) {
      throw new HttpError(400, `documents[${index}].embedding 必须是 512 维数组`);
    }
    if (!embedding.every((value) => typeof value === "number" && Number.isFinite(value))) {
      throw new HttpError(400, `documents[${index}].embedding 含非法数值`);
    }
    return { id, text, title, source, embedding };
  });
}

async function api(request, response, pathname) {
  if (pathname === "/api/health" && request.method === "GET") {
    if (initError) {
      json(response, 503, { ok: false, error: initError.message, mode: store.mode });
      return true;
    }
    if (!ready) {
      json(response, 503, { ok: false, error: "seekdb 正在初始化", mode: store.mode });
      return true;
    }
    try {
      json(response, 200, {
        ok: true,
        mode: store.mode,
        collection: "browser_knowledge_base",
        count: await store.count(),
        dimension: 512,
        backend: "seekdb",
      });
    } catch (error) {
      json(response, 503, { ok: false, error: error.message, mode: store.mode });
    }
    return true;
  }

  if (pathname === "/api/documents" && request.method === "POST") {
    await initPromise;
    assertReady();
    const body = await readJson(request);
    const documents = validateDocuments(body.documents);
    const started = performance.now();
    const result = await store.add(documents);
    json(response, 200, { ...result, elapsedMs: performance.now() - started });
    return true;
  }

  if (pathname === "/api/documents" && request.method === "DELETE") {
    await initPromise;
    assertReady();
    json(response, 200, await store.reset());
    return true;
  }

  if (pathname === "/api/search" && request.method === "POST") {
    await initPromise;
    assertReady();
    const body = await readJson(request);
    const query = typeof body.query === "string" ? body.query.trim() : "";
    if (!query) throw new HttpError(400, "query 不能为空");
    if (query.length > 500) throw new HttpError(400, "query 过长");
    const limit = Math.max(1, Math.min(20, Number(body.limit) || 5));
    if (!Array.isArray(body.embedding) || body.embedding.length !== 512) {
      throw new HttpError(400, "embedding 必须是 512 维数组");
    }
    if (!body.embedding.every((value) => typeof value === "number" && Number.isFinite(value))) {
      throw new HttpError(400, "embedding 含非法数值");
    }
    const result = await store.search(query, body.embedding, limit);
    json(response, 200, { ...result, mode: "hybrid" });
    return true;
  }

  return false;
}

async function staticFile(request, response, pathname) {
  let relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const filePath = normalize(join(DIST, relative));
  if (!filePath.startsWith(DIST)) {
    response.writeHead(403);
    response.end("forbidden");
    return;
  }
  try {
    const info = await stat(filePath);
    if (!info.isFile()) throw new Error("not a file");
    response.writeHead(200, {
      "content-type": MIME[extname(filePath)] || "application/octet-stream",
      "content-length": info.size,
      "cache-control": extname(filePath) === ".html" ? "no-cache" : "public, max-age=31536000, immutable",
    });
    createReadStream(filePath).pipe(response);
  } catch {
    const fallback = join(DIST, "index.html");
    try {
      const info = await stat(fallback);
      response.writeHead(200, {
        "content-type": "text/html; charset=utf-8",
        "content-length": info.size,
        "cache-control": "no-cache",
      });
      createReadStream(fallback).pipe(response);
    } catch {
      response.writeHead(503, { "content-type": "text/plain; charset=utf-8" });
      response.end("前端尚未构建：请先运行 npm run build，或使用 npm run dev。");
    }
  }
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url || "/", `http://${request.headers.host || "localhost"}`);
  try {
    if (url.pathname.startsWith("/api/")) {
      const handled = await api(request, response, url.pathname);
      if (!handled) json(response, 404, { error: "not found" });
      return;
    }
    await staticFile(request, response, decodeURIComponent(url.pathname));
  } catch (error) {
    const status = error instanceof HttpError ? error.status : 500;
    if (!response.headersSent) json(response, status, { error: error.message });
    else response.destroy();
  }
});

server.listen(PORT, () => {
  console.log(`StepFun knowledge base: http://127.0.0.1:${PORT}`);
  console.log(`seekdb mode: ${(process.env.SEEKDB_MODE || "embedded").toLowerCase()}`);
  if ((process.env.SEEKDB_MODE || "embedded").toLowerCase() === "server") {
    console.log(`seekdb server: ${process.env.SEEKDB_HOST || "127.0.0.1"}:${process.env.SEEKDB_PORT || 2881}`);
  } else {
    console.log(`seekdb path: ${process.env.SEEKDB_PATH || "./.data/seekdb"}`);
  }
});

async function shutdown() {
  await store.close().catch(() => {});
  server.close(() => process.exit(0));
}
process.on("SIGINT", () => void shutdown());
process.on("SIGTERM", () => void shutdown());
