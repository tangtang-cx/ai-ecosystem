// Build the amd-cagra-submit branch on top of the frozen baseline using the REST API,
// because git's smart-HTTP endpoint to github.com is unreliable from this network.
import { readFileSync } from "node:fs";
import { join } from "node:path";

const TOKEN = process.env.GH_T;
if (!TOKEN) throw new Error("GH_T missing");
const REPO = process.env.GH_REPO || "wzhaihqy/seekdb";
const BASE = process.env.GH_BASE || "634888d9b037153fa143d2c913ba4b25503e1d62";
const BRANCH = process.env.GH_BRANCH || "amd-cagra-submit";
const DRY = process.env.GH_DRY === "1";
const API = "https://api.github.com";
const ROOT = "D:\\project\\OceanBase\\ai-ecosystem\\amd\\submit\\files";

const headers = {
  authorization: `Bearer ${TOKEN}`,
  accept: "application/vnd.github+json",
  "x-github-api-version": "2022-11-28",
  "user-agent": "dsh-amd-push",
};

async function api(path, init = {}) {
  const res = await fetch(`${API}${path}`, { ...init, headers: { ...headers, ...(init.headers || {}) } });
  const text = await res.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!res.ok) throw new Error(`${res.status} ${path}: ${text.slice(0, 400)}`);
  return body;
}

const FILES = [
  ["docs/AMD_PERF_REPORT.md", "100644", "docs\\AMD_PERF_REPORT.md"],
  ["src/oblib/lib/vector/ob_vsag_adaptor.cpp", "100644", "src\\oblib\\lib\\vector\\ob_vsag_adaptor.cpp"],
  ["tools/hipvs_bridge/0001-ob-vsag-adaptor-direct-search.patch", "100644", "tools\\hipvs_bridge\\0001-ob-vsag-adaptor-direct-search.patch"],
  ["tools/hipvs_bridge/bench_bridge.py", "100755", "tools\\hipvs_bridge\\bench_bridge.py"],
  ["tools/hipvs_bridge/build.sh", "100755", "tools\\hipvs_bridge\\build.sh"],
  ["tools/hipvs_bridge/seekdb_cuvs_bridge.c", "100644", "tools\\hipvs_bridge\\seekdb_cuvs_bridge.c"],
];

const MESSAGE = `perf(vector): optimize hipVS CAGRA build/search

- seekdb_cuvs_bridge.c: lower CAGRA build params (graph_degree 96,
  intermediate_graph_degree 144, nn_descent_niter 40), build directly from a
  device tensor to drop a redundant H2D copy, and cache per-handle query
  device/pinned buffers and search params instead of reallocating per query.
- ob_vsag_adaptor.cpp: drop the per-query pthread_create/join; the bridge now
  runs queries on a resident large-stack worker.
- build.sh: add -O3 -DNDEBUG -pthread; other flags unchanged from baseline.
- bench_bridge.py: bridge-level build/QPS/recall benchmark harness.
- 0001-ob-vsag-adaptor-direct-search.patch: standalone adaptor revert patch.
- docs/AMD_PERF_REPORT.md: method, parameter table, rollback and rerun notes.
`;

const AUTHOR = {
  name: "wzhaihqy",
  email: "wzhaihqy@users.noreply.github.com",
  date: "2026-11-12T05:11:17Z",
};

console.log(`repo   : ${REPO}`);
console.log(`base   : ${BASE}`);
console.log(`branch : ${BRANCH}`);
console.log(`dryRun : ${DRY}`);

const baseCommit = await api(`/repos/${REPO}/git/commits/${BASE}`);
const baseTree = baseCommit.tree.sha;
console.log(`base tree: ${baseTree}`);

const entries = [];
for (const [repoPath, mode, localPath] of FILES) {
  const content = readFileSync(join(ROOT, localPath));
  let sha;
  if (DRY) {
    const { createHash } = await import("node:crypto");
    const h = createHash("sha1").update(`blob ${content.length}\0`).update(content).digest("hex");
    sha = h;
  } else {
    const blob = await api(`/repos/${REPO}/git/blobs`, {
      method: "POST",
      body: JSON.stringify({ content: content.toString("base64"), encoding: "base64" }),
    });
    sha = blob.sha;
  }
  entries.push({ path: repoPath, mode, type: "blob", sha });
  console.log(`blob ${mode} ${content.length.toString().padStart(6)} bytes ${sha.slice(0, 10)} ${repoPath}`);
}

if (DRY) { console.log("\nDRY RUN - no tree/commit/ref written"); process.exit(0); }

const tree = await api(`/repos/${REPO}/git/trees`, {
  method: "POST",
  body: JSON.stringify({ base_tree: baseTree, tree: entries }),
});
console.log(`\nnew tree: ${tree.sha}`);

const commit = await api(`/repos/${REPO}/git/commits`, {
  method: "POST",
  body: JSON.stringify({ message: MESSAGE, tree: tree.sha, parents: [BASE], author: AUTHOR, committer: AUTHOR }),
});
console.log(`new commit: ${commit.sha}`);
console.log(`matches local equivalent 483d3011? ${commit.sha.startsWith("483d3011") ? "YES - exact reconstruction" : "no (content-equivalent commit)"}`);

try {
  await api(`/repos/${REPO}/git/refs`, {
    method: "POST",
    body: JSON.stringify({ ref: `refs/heads/${BRANCH}`, sha: commit.sha }),
  });
  console.log(`ref created: refs/heads/${BRANCH}`);
} catch (error) {
  if (error.message.startsWith("422") || error.message.startsWith("409")) {
    await api(`/repos/${REPO}/git/refs/heads/${BRANCH}`, {
      method: "PATCH",
      body: JSON.stringify({ sha: commit.sha, force: true }),
    });
    console.log(`ref updated (forced): refs/heads/${BRANCH}`);
  } else throw error;
}

console.log(`\nBRANCH_SHA ${commit.sha}`);
console.log(`URL https://github.com/${REPO}/tree/${BRANCH}`);
