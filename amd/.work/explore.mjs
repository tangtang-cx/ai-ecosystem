// Explore the frozen baseline commit tree so we can build a new commit via the REST API.
const TOKEN = process.env.GH_T;
if (!TOKEN) throw new Error("GH_T missing");
const REPO = process.env.GH_REPO || "wzhaihqy/seekdb";
const BASE = process.env.GH_BASE || "634888d9b037153fa143d2c913ba4b25503e1d62";
const API = "https://api.github.com";

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
  if (!res.ok) throw new Error(`${res.status} ${path}: ${text.slice(0, 300)}`);
  return body;
}

const commit = await api(`/repos/${REPO}/git/commits/${BASE}`);
console.log("base commit   :", commit.sha);
console.log("base tree     :", commit.tree.sha);
console.log("base message  :", JSON.stringify(commit.message).slice(0, 200));
console.log("parents       :", commit.parents.map((p) => p.sha).join(", "));

const top = await api(`/repos/${REPO}/git/trees/${commit.tree.sha}`);
const byPath = new Map(top.tree.map((e) => [e.path, e]));
for (const name of ["docs", "src", "tools"]) {
  const e = byPath.get(name);
  console.log(`top/${name} -> ${e ? e.type + " " + e.mode + " " + e.sha : "MISSING"}`);
}

async function walk(parts) {
  let entry = { sha: commit.tree.sha, type: "tree" };
  for (const part of parts) {
    const t = await api(`/repos/${REPO}/git/trees/${entry.sha}`);
    const next = t.tree.find((x) => x.path === part);
    if (!next) return null;
    entry = next;
  }
  return entry;
}

const targets = [
  ["docs"],
  ["src", "oblib", "lib", "vector"],
  ["tools", "hipvs_bridge"],
];
const resolved = {};
for (const parts of targets) {
  const e = await walk(parts);
  console.log(`\n=== ${parts.join("/")} -> ${e ? e.sha : "MISSING"}`);
  if (!e) continue;
  resolved[parts.join("/")] = e.sha;
  const t = await api(`/repos/${REPO}/git/trees/${e.sha}`);
  console.log(`    entries: ${t.tree.length}`);
  for (const x of t.tree) console.log(`      ${x.type} ${x.mode} ${x.sha.slice(0, 8)} ${x.path}`);
}

console.log("\nRESOLVED " + JSON.stringify(resolved));
