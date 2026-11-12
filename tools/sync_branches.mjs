/**
 * Sync local files onto a GitHub branch through the REST API.
 *
 * git's smart-HTTP endpoint is blocked in this environment, but api.github.com
 * is reachable, so this script builds blobs/tree/commit/ref by hand.
 *
 * The target branch keeps everything it already has; only the paths passed
 * with --paths are overwritten, and --delete removes repo-relative paths.
 *
 * Usage:
 *   GITHUB_TOKEN=... node tools/sync_branches.mjs \
 *     --branch main --base main \
 *     --paths Dify Qoder 魔搭 AI-Ecosystem-Solutions README.md \
 *     --message "feat: add dify, qoder and modelscope deliverables"
 */
import { readFile, readdir, stat } from "node:fs/promises";
import { join, relative, sep } from "node:path";

const TOKEN = process.env.GITHUB_TOKEN;
if (!TOKEN) throw new Error("GITHUB_TOKEN is required");
const REPO = process.env.GITHUB_REPO || "tangtang-cx/ai-ecosystem";
const API = "https://api.github.com";
const ROOT = process.cwd();

function parseArgs(argv) {
  const args = { branch: "", base: "", paths: [], delete: [], keep: [], message: "", config: "" };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const value = argv[index + 1];
    if (token === "--branch") args.branch = value;
    else if (token === "--base") args.base = value;
    else if (token === "--paths") {
      index += 1;
      while (index < argv.length && !argv[index].startsWith("--")) {
        args.paths.push(argv[index]);
        index += 1;
      }
      index -= 1;
    } else if (token === "--delete") {
      index += 1;
      while (index < argv.length && !argv[index].startsWith("--")) {
        args.delete.push(argv[index]);
        index += 1;
      }
      index -= 1;
    } else if (token === "--message") args.message = value;
    else if (token === "--config") args.config = value;
    else if (token === "--keep") {
      index += 1;
      while (index < argv.length && !argv[index].startsWith("--")) {
        args.keep.push(argv[index]);
        index += 1;
      }
      index -= 1;
    }
  }
  return args;
}

const IGNORED = new Set(["node_modules", "__pycache__", ".git", ".data", ".cache", "dist", "build", ".npm-cache", ".tmp", ".venv"]);

function isIgnored(relativePath) {
  const parts = relativePath.split(/[\\/]/);
  if (parts.some((part) => IGNORED.has(part))) return true;
  const name = parts[parts.length - 1];
  if (name.endsWith(".pyc") || name.endsWith(".pyo")) return true;
  if (name === ".env" || name === ".DS_Store" || name.endsWith(".log")) return true;
  return false;
}

async function walk(directory, files = []) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const full = join(directory, entry.name);
    if (entry.isDirectory()) await walk(full, files);
    else files.push(full);
  }
  return files;
}

async function api(path, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${TOKEN}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "dsh-sync",
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

async function refSha(branch) {
  const ref = await api(`/repos/${REPO}/git/ref/heads/${encodeURIComponent(branch)}`);
  return ref.object.sha;
}

async function treeEntries(sha) {
  const tree = await api(`/repos/${REPO}/git/trees/${sha}?recursive=1`);
  const entries = new Map();
  for (const item of tree.tree) {
    if (item.type === "blob") entries.set(item.path, { mode: item.mode, sha: item.sha });
  }
  return entries;
}

async function upsertRef(branch, sha) {
  try {
    await api(`/repos/${REPO}/git/refs/heads/${encodeURIComponent(branch)}`, {
      method: "PATCH",
      body: JSON.stringify({ sha, force: false }),
    });
  } catch (error) {
    if (error.status !== 404 && error.status !== 422) throw error;
    await api(`/repos/${REPO}/git/refs`, {
      method: "POST",
      body: JSON.stringify({ ref: `refs/heads/${branch}`, sha }),
    });
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.config) {
    const { readFile: read } = await import("node:fs/promises");
    const config = JSON.parse(await read(join(ROOT, args.config), "utf8"));
    args.branch = config.branch ?? args.branch;
    args.base = config.base ?? args.base;
    args.paths = config.paths ?? args.paths;
    args.delete = config.delete ?? args.delete;
    args.keep = config.keep ?? args.keep;
    args.message = config.message ?? args.message;
  }
  if (!args.branch || !args.base) throw new Error("--branch and --base are required");
  if (!args.message) args.message = `chore: sync ${args.paths.join(", ")}`;

  const baseSha = await refSha(args.base);
  const entries = await treeEntries(baseSha);
  console.log(`base ${args.base} @ ${baseSha.slice(0, 8)} (${entries.size} blobs)`);

  let uploaded = 0;
  for (const localPath of args.paths) {
    const absolute = join(ROOT, localPath);
    const info = await stat(absolute).catch(() => null);
    if (!info) {
      console.log(`skip (missing): ${localPath}`);
      continue;
    }
    const files = info.isDirectory() ? await walk(absolute) : [absolute];
    for (const file of files) {
      const relativePath = relative(ROOT, file).split(sep).join("/");
      if (isIgnored(relativePath)) continue;
      const content = await readFile(file);
      const blob = await api(`/repos/${REPO}/git/blobs`, {
        method: "POST",
        body: JSON.stringify({ content: content.toString("base64"), encoding: "base64" }),
      });
      entries.set(relativePath, { mode: "100644", sha: blob.sha });
      uploaded += 1;
      console.log(`blob ${relativePath} (${content.length} bytes) ${blob.sha.slice(0, 8)}`);
    }
  }

  for (const path of args.delete) {
    if (entries.delete(path)) console.log(`deleted ${path}`);
  }

  if (args.keep.length) {
    const keepPrefixes = args.keep.map((item) => item.replace(/\/$/, "") + "/");
    for (const path of [...entries.keys()]) {
      const keepFile = args.keep.some((item) => !item.endsWith("/") && item === path);
      if (!keepFile && !keepPrefixes.some((prefix) => path.startsWith(prefix))) {
        entries.delete(path);
      }
    }
    console.log(`kept only: ${args.keep.join(", ")} (${entries.size} blobs left)`);
  }

  const tree = [...entries.entries()].map(([path, value]) => ({
    path,
    mode: value.mode,
    type: "blob",
    sha: value.sha,
  }));
  const treeResult = await api(`/repos/${REPO}/git/trees`, {
    method: "POST",
    body: JSON.stringify({ tree }),
  });
  const commit = await api(`/repos/${REPO}/git/commits`, {
    method: "POST",
    body: JSON.stringify({
      message: args.message,
      tree: treeResult.sha,
      parents: [baseSha],
    }),
  });
  await upsertRef(args.branch, commit.sha);
  console.log(`\n${args.branch}: ${commit.sha} (${uploaded} files uploaded, ${tree.length} blobs in tree)`);
  console.log(`https://github.com/${REPO}/tree/${args.branch}`);
}

await main();
