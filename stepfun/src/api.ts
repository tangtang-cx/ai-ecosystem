export interface DocumentInput {
  id: string;
  text: string;
  title: string;
  source: string;
  embedding: number[];
}

export interface SearchHit {
  id: string;
  text: string;
  title: string;
  source: string;
  score: number | null;
  distance: number | null;
}

export interface SearchResponse {
  hits: SearchHit[];
  elapsedMs: number;
  mode: "hybrid";
}

export interface HealthResponse {
  ok: boolean;
  mode: string;
  collection: string;
  count: number;
  dimension: number;
  backend: string;
  error?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(body.error || `${response.status} ${response.statusText}`);
  return body;
}

export function health(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function addDocuments(documents: DocumentInput[]): Promise<{ inserted: number; count: number; elapsedMs: number }> {
  return request("/api/documents", { method: "POST", body: JSON.stringify({ documents }) });
}

export function search(query: string, embedding: number[], limit = 5): Promise<SearchResponse> {
  return request("/api/search", {
    method: "POST",
    body: JSON.stringify({ query, embedding, limit }),
  });
}

export function reset(): Promise<{ ok: boolean; count: number }> {
  return request("/api/documents", { method: "DELETE" });
}
