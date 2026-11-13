/**
 * Create (or move) a branch that points at an existing commit.
 *
 * Used to keep a backup of the previous layout before the submission branch is
 * rebuilt on top of the official powercontext base.
 *
 * Usage:
 *   GITHUB_TOKEN=... node tools/alias_branch.mjs <source-branch> <target-branch>
 */
const TOKEN = process.env.GITHUB_TOKEN;
if (!TOKEN) throw new Error("GITHUB_TOKEN is required");
const REPO = process.env.GITHUB_REPO || "tangtang-cx/ai-ecosystem";
const API = "https://api.github.com";

async function api(path, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${TOKEN}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "dsh-alias",
      ...(init.headers || {}),
    },
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`${response.status} ${path}: ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

const [source, target] = process.argv.slice(2);
if (!source || !target) throw new Error("usage: node tools/alias_branch.mjs <source-branch> <target-branch>");

const sha = await api(`/repos/${REPO}/git/ref/heads/${encodeURIComponent(source)}`).then((r) => r.object.sha);
console.log(`source ${source} = ${sha}`);

try {
  await api(`/repos/${REPO}/git/refs/heads/${encodeURIComponent(target)}`, {
    method: "PATCH",
    body: JSON.stringify({ sha, force: true }),
  });
  console.log(`updated ${target}`);
} catch (error) {
  await api(`/repos/${REPO}/git/refs`, {
    method: "POST",
    body: JSON.stringify({ ref: `refs/heads/${target}`, sha }),
  });
  console.log(`created ${target}`);
}
console.log(`https://github.com/${REPO}/tree/${target}`);
