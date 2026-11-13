/**
 * Push local files into another repository on top of an existing branch,
 * without rewriting the branch's existing content.
 *
 * Uses the Git Data API's `base_tree` parameter: only the paths we push are
 * written into the new tree, every other file of the base branch is kept.
 *
 * Usage:
 *   GITHUB_TOKEN=... GITHUB_REPO=wzhaihqy/seekdb \
 *   node tools/push_into_repo.mjs <base-branch> <new-branch> <local-path>[:<repo-path>] ...
 */
import { readFileSync, existsSync, statSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, relative, sep } from "node:path";

const TOKEN = process.env.GITHUB_TOKEN;
if (!TOKEN) throw new Error("GITHUB_TOKEN is required");
const REPO = process.env.GITHUB_REPO || "tangtang-cx/ai-ecosystem";
const API = "https://api.github.com";
const ROOT = process.cwd();

async function api(path, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${TOKEN}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "dsh-push-into",
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

const [baseBranch, newBranch, ...mappings] = process.argv.slice(2);
if (!baseBranch || !newBranch || !mappings.length) {
  throw new Error("usage: push_into_repo.mjs <base-branch> <new-branch> <local-path>[:<repo-path>]...");
}

const baseRef = await api(`/repos/${REPO}/git/ref/heads/${encodeURIComponent(baseBranch)}`);
const baseSha = baseRef.object.sha;
const baseCommit = await api(`/repos/${REPO}/git/commits/${baseSha}`);
const baseTree = baseCommit.tree.sha;
console.log(`base ${baseBranch} = ${baseSha} (tree ${baseTree})`);

const entries = [];
for (const mapping of mappings) {
  const [source, dest] = mapping.includes("::") ? mapping.split("::") : [mapping, mapping];
  const absolute = join(ROOT, source);
  if (!existsSync(absolute)) {
    console.log(`skip (missing): ${source}`);
    continue;
  }
  const files = statSync(absolute).isDirectory()
    ? execFileSync("git", ["ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", source], { cwd: ROOT, encoding: "utf8" })
        .split("\0")
        .filter(Boolean)
    : [relative(ROOT, absolute).split(sep).join("/")];

  for (const relativePath of files) {
    const file = join(ROOT, relativePath);
    if (!existsSync(file) || !statSync(file).isFile()) continue;
    const target = relativePath.startsWith(`${source}/`)
      ? `${dest.replace(/\/$/, "")}/${relativePath.slice(source.length + 1)}`
      : dest;
    const content = readFileSync(file);
    const blob = await api(`/repos/${REPO}/git/blobs`, {
      method: "POST",
      body: JSON.stringify({ content: content.toString("base64"), encoding: "base64" }),
    });
    entries.push({ path: target, mode: "100644", type: "blob", sha: blob.sha });
    console.log(`blob ${target} (${content.length} bytes)`);
  }
}

if (!entries.length) {
  console.log("nothing to push");
  process.exit(0);
}

const tree = await api(`/repos/${REPO}/git/trees`, {
  method: "POST",
  body: JSON.stringify({ base_tree: baseTree, tree: entries }),
});
const commit = await api(`/repos/${REPO}/git/commits`, {
  method: "POST",
  body: JSON.stringify({ message: `feat: add the AI ecosystem track assets (${mappings.join(", ")})`, tree: tree.sha, parents: [baseSha] }),
});

try {
  await api(`/repos/${REPO}/git/refs/heads/${encodeURIComponent(newBranch)}`, {
    method: "PATCH",
    body: JSON.stringify({ sha: commit.sha, force: true }),
  });
  console.log(`updated ${newBranch}`);
} catch (error) {
  if (error.status !== 404 && error.status !== 422) throw error;
  await api(`/repos/${REPO}/git/refs`, {
    method: "POST",
    body: JSON.stringify({ ref: `refs/heads/${newBranch}`, sha: commit.sha }),
  });
  console.log(`created ${newBranch}`);
}
console.log(`${REPO}@${newBranch} = ${commit.sha}`);
