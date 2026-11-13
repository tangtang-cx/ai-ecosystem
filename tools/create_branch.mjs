/** Create a single task branch (used for the AMD planning branch). */
import { readFile } from "node:fs/promises";

const TOKEN = process.env.GITHUB_TOKEN;
if (!TOKEN) throw new Error("GITHUB_TOKEN is required");
const REPO = process.env.GITHUB_REPO || "tangtang-cx/ai-ecosystem";
const BRANCH = process.env.BRANCH || "amd";
const PREFIXES = (process.env.PREFIXES || "amd").split(",").map((item) => item.trim());
const BASE = process.env.GITHUB_BASE || "39e069f42940f726ef655e8f49aba2c527bf4f1c";
const README_PATH = process.env.README_PATH;
const MESSAGE = process.env.MESSAGE || `feat(${BRANCH}): add ${PREFIXES.join(", ")} assets`;
const API = "https://api.github.com";

async function api(path, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${TOKEN}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "dsh-branch",
      ...(init.headers || {}),
    },
  });
  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!response.ok) {
    const error = new Error(`${response.status} ${path}: ${text.slice(0, 300)}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

const baseCommit = await api(`/repos/${REPO}/git/commits/${BASE}`);
const baseTree = await api(`/repos/${REPO}/git/trees/${baseCommit.tree.sha}?recursive=1`);
const blobs = baseTree.tree.filter((item) => item.type === "blob");
const selected = blobs.filter((item) =>
  PREFIXES.some((prefix) => item.path === prefix || item.path.startsWith(`${prefix}/`)),
);

const tree = selected.map((item) => ({ path: item.path, mode: "100644", type: "blob", sha: item.sha }));
for (const name of [".gitignore", ".gitattributes"]) {
  const item = blobs.find((entry) => entry.path === name);
  if (item) tree.push({ path: name, mode: "100644", type: "blob", sha: item.sha });
}

const overrides = (process.env.OVERRIDE_PATHS || "")
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean);
for (const path of overrides) {
  const content = await readFile(path);
  const blob = await api(`/repos/${REPO}/git/blobs`, {
    method: "POST",
    body: JSON.stringify({ content: content.toString("base64"), encoding: "base64" }),
  });
  const index = tree.findIndex((item) => item.path === path);
  const entry = { path, mode: "100644", type: "blob", sha: blob.sha };
  if (index >= 0) tree[index] = entry;
  else tree.push(entry);
}

if (README_PATH) {
  const content = await readFile(README_PATH);
  const blob = await api(`/repos/${REPO}/git/blobs`, {
    method: "POST",
    body: JSON.stringify({ content: content.toString("base64"), encoding: "base64" }),
  });
  tree.push({ path: "README.md", mode: "100644", type: "blob", sha: blob.sha });
}

const treeResult = await api(`/repos/${REPO}/git/trees`, {
  method: "POST",
  body: JSON.stringify({ tree }),
});
const commit = await api(`/repos/${REPO}/git/commits`, {
  method: "POST",
  body: JSON.stringify({ message: MESSAGE, tree: treeResult.sha, parents: [BASE] }),
});

try {
  await api(`/repos/${REPO}/git/refs/heads/${BRANCH}`, {
    method: "PATCH",
    body: JSON.stringify({ sha: commit.sha, force: true }),
  });
} catch (error) {
  if (error.status !== 404 && error.status !== 422) throw error;
  await api(`/repos/${REPO}/git/refs`, {
    method: "POST",
    body: JSON.stringify({ ref: `refs/heads/${BRANCH}`, sha: commit.sha }),
  });
}

console.log(`${BRANCH}: ${commit.sha} (${tree.length} files)`);
console.log(`https://github.com/${REPO}/tree/${BRANCH}`);
