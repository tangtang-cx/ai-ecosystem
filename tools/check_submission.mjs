/**
 * Simulate what the judging platform does with our submission coordinates:
 *
 *   1. clone the repo with the token-embedded URL (auth check)
 *   2. resolve the requested branch (case-sensitive!)
 *   3. check that the requested commit id exists and is reachable from that branch
 *   4. check the required asset directory is present in that commit
 *
 * Usage:
 *   GITHUB_TOKEN=... node tools/check_submission.mjs <branch> <commit> <dir>
 */

const TOKEN = process.env.GITHUB_TOKEN;
if (!TOKEN) throw new Error("GITHUB_TOKEN is required");
const REPO = process.env.GITHUB_REPO || "tangtang-cx/ai-ecosystem";
const API = "https://api.github.com";

async function api(path) {
  const response = await fetch(`${API}${path}`, {
    headers: {
      authorization: `Bearer ${TOKEN}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "dsh-check-submission",
    },
  });
  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { status: response.status, body };
}

function fail(msg) {
  console.log(`  FAIL  ${msg}`);
  process.exitCode = 1;
}
function ok(msg) {
  console.log(`  ok    ${msg}`);
}

const [branch, commit, dir] = process.argv.slice(2);

console.log(`== submission check: ${REPO} @ ${branch} / ${commit} / ${dir}/ ==`);

// 1. the repo must be clonable with the submitted credentials
{
  const res = await api(`/repos/${REPO}`);
  if (res.status === 200) ok(`repository reachable (private=${res.body.private})`);
  else fail(`repository not reachable: HTTP ${res.status}`);
}

// 2. the branch must exist EXACTLY as written (git is case-sensitive)
let branchSha = null;
for (const candidate of [branch, branch.toLowerCase(), branch.toUpperCase()]) {
  const res = await api(`/repos/${REPO}/git/ref/heads/${encodeURIComponent(candidate)}`);
  if (res.status === 200) {
    branchSha = res.body.object.sha;
    if (candidate === branch) ok(`branch "${branch}" exists -> ${branchSha}`);
    else fail(`branch "${branch}" NOT FOUND (git is case-sensitive); "${candidate}" exists -> ${branchSha}`);
    break;
  }
}
if (!branchSha) fail(`no branch matches "${branch}"`);

// 3. the commit must exist AND belong to that branch (head or ancestor)
{
  const res = await api(`/repos/${REPO}/git/commits/${commit}`);
  if (res.status !== 200) {
    fail(`commit ${commit} not found (HTTP ${res.status})`);
  } else {
    const parents = res.body.parents.map((p) => p.sha);
    if (branchSha === commit) {
      ok(`commit ${commit} is the branch head`);
    } else if (parents.includes(branchSha)) {
      ok(`commit ${commit} is a direct child of the branch head`);
    } else {
      // walk back from the branch head to see whether the commit is an ancestor
      let cursor = branchSha;
      let found = false;
      for (let hop = 0; hop < 60 && !found; hop += 1) {
        const step = await api(`/repos/${REPO}/git/commits/${cursor}`);
        if (step.status !== 200) break;
        const sha = step.body.sha;
        if (sha === commit) {
          found = true;
          break;
        }
        const next = (step.body.parents || [])[0];
        if (!next || next === cursor) break;
        cursor = next;
      }
      if (found) ok(`commit ${commit} is an ancestor of the branch head (${branchSha})`);
      else fail(`commit ${commit} is NOT on branch "${branch}" (head is ${branchSha}) — 分支与 commit 不匹配`);
    }
  }
}

// 4. the required asset directory must be present in that commit
if (commit) {
  const res = await api(`/repos/${REPO}/git/trees/${commit}?recursive=1`);
  if (res.status === 200) {
    const files = res.body.tree.filter((item) => item.type === "blob").map((item) => item.path);
    const prefix = `${dir}/`;
    const hits = files.filter((p) => p.startsWith(prefix));
    if (hits.length) ok(`${dir}/ contains ${hits.length} files (e.g. ${hits.slice(0, 3).join(", ")})`);
    else fail(`${dir}/ is EMPTY in commit ${commit} — the platform will not find the assets`);
    console.log(`  top-level: ${res.body.tree.filter((i) => i.type === "tree").map((i) => i.path).join(", ")}`);
  } else {
    fail(`cannot read the tree of ${commit}`);
  }
}

console.log(process.exitCode ? "\nRESULT: NOT SUBMITTABLE" : "\nRESULT: submittable");
