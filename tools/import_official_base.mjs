/**
 * Recreate the official contest base commit inside our private repo.
 *
 * The official base is oceanbase/powercontext@2026-competition-ecosystem:
 *
 *   commit d647275c308e09b7b623f322a26f5c4e85734fb0
 *   "chore: initialize 2026 competition ecosystem directories"
 *   tree  4ab7c84938da5ca04814fb022bf1b965d6504fd9
 *   tree entries: dify/ gaode/ minimax/ qoder/ stepfun/  (each holds an empty .gitkeep)
 *
 * That commit has **no parents**, and blobs/trees/commits are content-addressed,
 * so we can rebuild the exact same objects in our own repository through the
 * REST API. The resulting commit SHA is identical (d647275c...), which means
 * our submission branch really descends from the official base and the judge's
 * `git merge-base --is-ancestor d647275c <our commit>` check passes.
 *
 * Usage:
 *   GITHUB_TOKEN=... node tools/import_official_base.mjs
 */
const TOKEN = process.env.GITHUB_TOKEN;
if (!TOKEN) throw new Error("GITHUB_TOKEN is required");
const REPO = process.env.GITHUB_REPO || "tangtang-cx/ai-ecosystem";
const API = "https://api.github.com";

const BASE_COMMIT = "d647275c308e09b7b623f322a26f5c4e85734fb0";
const BASE_TREE = "4ab7c84938da5ca04814fb022bf1b965d6504fd9";
const KEEPTREE_TREE = "d564d0bc3dd917926892c55e3706cc116d5b165e";
const DIRS = ["dify", "gaode", "minimax", "qoder", "stepfun"];
// The upstream commit was authored in UTC+8, and the timezone offset is part of
// the commit object, so the date must carry the original offset (the API
// normalises plain Z dates to +0000, which would produce a different SHA).
// The message keeps its trailing newline for the same reason.
const AUTHOR = { name: "Chojan Shang", email: "psiace@apache.org", date: "2026-10-23T15:36:03+08:00" };
const MESSAGE = "chore: initialize 2026 competition ecosystem directories\n";

async function api(path, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${TOKEN}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "dsh-import-base",
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

async function main() {
  // 1. empty blob (the .gitkeep files are empty)
  const blob = await api(`/repos/${REPO}/git/blobs`, {
    method: "POST",
    body: JSON.stringify({ content: "", encoding: "utf-8" }),
  });
  console.log(`empty blob: ${blob.sha} (expected e69de29bb2d1d6434b8b29ae775ad8c2e48c5391)`);

  // 2. the per-directory tree that holds one empty .gitkeep
  const keepTree = await api(`/repos/${REPO}/git/trees`, {
    method: "POST",
    body: JSON.stringify({
      tree: [{ path: ".gitkeep", mode: "100644", type: "blob", sha: blob.sha }],
    }),
  });
  console.log(`keep tree: ${keepTree.sha} (expected ${KEEPTREE_TREE})`);

  // 3. the root tree with the five task directories
  const rootTree = await api(`/repos/${REPO}/git/trees`, {
    method: "POST",
    body: JSON.stringify({
      tree: DIRS.map((dir) => ({ path: dir, mode: "040000", type: "tree", sha: keepTree.sha })),
    }),
  });
  console.log(`root tree: ${rootTree.sha} (expected ${BASE_TREE})`);

  // 4. the commit itself, byte-identical to the official base
  let commit;
  try {
    commit = await api(`/repos/${REPO}/git/commits`, {
      method: "POST",
      body: JSON.stringify({
        message: MESSAGE,
        tree: rootTree.sha,
        parents: [],
        author: AUTHOR,
        committer: AUTHOR,
      }),
    });
  } catch (error) {
    if (error.status === 422) {
      console.log("commit already exists (422) -> looking it up");
      commit = await api(`/repos/${REPO}/git/commits/${BASE_COMMIT}`);
    } else {
      throw error;
    }
  }
  console.log(`base commit: ${commit.sha}`);
  if (commit.sha !== BASE_COMMIT) {
    console.log(`WARNING: expected ${BASE_COMMIT}`);
  } else {
    console.log("OK: the official base commit now exists in our repository");
  }
}

await main();
