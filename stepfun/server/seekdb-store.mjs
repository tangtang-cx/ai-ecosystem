import {
  FulltextIndexConfig,
  Schema,
  SeekdbClient,
  VectorIndexConfig,
} from "seekdb";

const COLLECTION_NAME = "browser_knowledge_base";
const EMBEDDING_DIM = 512;

/**
 * Real seekdb adapter.
 *
 * The browser never talks to MySQL directly: this local server owns the seekdb
 * connection, and hybridSearch runs *inside* seekdb (vector recall + full-text
 * recall fused with RRF). The client only ships vectors and documents.
 *
 * Two deployment modes are supported:
 *   - embedded (default): seekdb runs as a local background process managed by
 *     the seekdb-js native binding; data lives under SEEKDB_PATH.
 *   - server: an external seekdb / OceanBase instance is used (docker compose).
 */
export class SeekdbStore {
  constructor() {
    this.client = null;
    this.collection = null;
    this.mode = "seekdb";
  }

  async init() {
    const mode = (process.env.SEEKDB_MODE || "embedded").toLowerCase();
    if (mode === "server") {
      await this.initServer();
    } else {
      await this.initEmbedded();
    }
    await this.collection.refresh_index();
  }

  async initServer() {
    const host = process.env.SEEKDB_HOST || "127.0.0.1";
    const port = Number(process.env.SEEKDB_PORT || 2881);
    const user = process.env.SEEKDB_USER || "root";
    const password = process.env.SEEKDB_PASSWORD || "";
    const database = process.env.SEEKDB_DATABASE || "test";
    const tenant = process.env.SEEKDB_TENANT || undefined;
    this.client = new SeekdbClient({ host, port, user, password, database, tenant });
    this.mode = "seekdb-server";
    this.collection = await this.client.getOrCreateCollection({
      name: COLLECTION_NAME,
      schema: this.schema(),
    });
  }

  async initEmbedded() {
    const path = process.env.SEEKDB_PATH || "./.data/seekdb";
    this.client = new SeekdbClient({ path, database: process.env.SEEKDB_DATABASE || "test" });
    this.mode = "seekdb-embedded";
    this.collection = await this.client.getOrCreateCollection({
      name: COLLECTION_NAME,
      schema: this.schema(),
    });
  }

  schema() {
    return new Schema({
      fulltextIndex: new FulltextIndexConfig("ik", { ik_mode: "smart" }),
      vectorIndex: new VectorIndexConfig({
        hnsw: {
          dimension: EMBEDDING_DIM,
          distance: "cosine",
          type: "hnsw",
          m: 16,
          ef_construction: 200,
          ef_search: 64,
        },
        embeddingFunction: null,
      }),
    });
  }

  async add(documents) {
    if (!this.collection) throw new Error("seekdb collection is not initialized");
    if (!documents.length) return { inserted: 0, count: await this.collection.count() };

    const ids = documents.map((doc) => doc.id);
    const embeddings = documents.map((doc) => doc.embedding);
    const texts = documents.map((doc) => doc.text);
    const metadatas = documents.map((doc) => ({
      title: doc.title,
      source: doc.source,
      chars: doc.text.length,
      imported_at: new Date().toISOString(),
    }));

    for (let offset = 0; offset < documents.length; offset += 64) {
      const end = offset + 64;
      await this.collection.upsert({
        ids: ids.slice(offset, end),
        embeddings: embeddings.slice(offset, end),
        documents: texts.slice(offset, end),
        metadatas: metadatas.slice(offset, end),
      });
    }
    await this.collection.refresh_index();
    return { inserted: documents.length, count: await this.collection.count() };
  }

  async search(query, embedding, limit) {
    if (!this.collection) throw new Error("seekdb collection is not initialized");
    const started = performance.now();
    const candidateCount = Math.max(limit * 3, 12);
    const result = await this.collection.hybridSearch({
      query: {
        whereDocument: { $contains: query },
        nResults: candidateCount,
      },
      knn: {
        queryEmbeddings: [embedding],
        nResults: candidateCount,
      },
      rank: { rrf: {} },
      nResults: limit,
      include: ["documents", "metadatas", "distances"],
    });
    const elapsedMs = performance.now() - started;

    const ids = result.ids?.[0] ?? [];
    const texts = result.documents?.[0] ?? [];
    const metadata = result.metadatas?.[0] ?? [];
    const distances = result.distances?.[0] ?? [];
    const hits = ids.map((id, index) => {
      const meta = metadata[index] ?? {};
      return {
        id,
        text: texts[index] ?? "",
        title: typeof meta.title === "string" ? meta.title : "未命名片段",
        source: typeof meta.source === "string" ? meta.source : "本地粘贴",
        score: null,
        distance: typeof distances[index] === "number" ? distances[index] : null,
      };
    });
    return { hits, elapsedMs };
  }

  async count() {
    if (!this.collection) return 0;
    return this.collection.count();
  }

  async reset() {
    if (!this.collection) return { ok: true, count: 0 };
    const existing = await this.collection.get({ include: [] });
    const ids = existing.ids ?? [];
    if (ids.length) await this.collection.delete({ ids });
    await this.collection.refresh_index();
    return { ok: true, count: await this.collection.count() };
  }

  async close() {
    if (this.client) await this.client.close();
    this.client = null;
    this.collection = null;
  }
}

export { COLLECTION_NAME, EMBEDDING_DIM };
