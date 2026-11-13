// End-to-end verification of the pushed branch against the local files/ payload.
import { readFileSync } from "node:fs";
import { join } from "node:path";

const TOKEN = process.env.GH_T;
const REPO = process.env.GH_REPO || "wzhaihqy/seekdb";
const BRANCH = process.env.GH_BRANCH || "amd-cagra-submit";
const BASE = "634888d9b037153fa143d2c913ba4b25503e1d62";
const API = "https://api.github.com";
const ROOT = "D:\\project\\OceanBase\\ai-ecosystem\\amd\\submit\\files";

const headers = {
  authorization: `Bearer ${TOKEN}`,
  accept: "application/vnd.github+json",
  "x-github-api-version": "2022-11-28",
  "user-agent": "dsh-amd-push",
};
async function api(path) {
  const res = await fetch(`${API}${path}`, { headers });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${path}: ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

const EXPECTED = new Map([
  ["docs/AMD_PERF_REPORT.md", { mode: "100644", local: "docs\\AMD_PERF_REPORT.md", status: "added" }],
  ["src/oblib/lib/vector/ob_vsag_adaptor.cpp", { mode: "100644", local: "src\\oblib\\lib\\vector\\ob_vsag_adaptor.cpp", status: "modified" }],
  ["tools/hipvs_bridge/0001-ob-vsag-adaptor-direct-search.patch", { mode: "100644", local: "tools\\hipvs_bridge\\0001-ob-vsag-adaptor-direct-search.patch", status: "added" }],
  ["tools/hipvs_bridge/bench_bridge.py", { mode: "100755", local: "tools\\hipvs_bridge\\bench_bridge.py", status: "added" }],
  ["tools/hipvs_bridge/build.sh", { mode: "100755", local: "tools\\hipvs_bridge\\build.sh", status: "modified" }],
  ["tools/hipvs_bridge/seekdb_cuvs_bridge.c", { mode: "100644", local: "tools\\hipvs_bridge\\seekdb_cuvs_bridge.c", status: "modified" }],
]);

let fails = 0;
const check = (name, ok, detail = "") => {
  if (!ok) fails += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
};

// 1. ref exists and points at a commit
const ref = await api(`/repos/${REPO}/git/ref/heads/${BRANCH}`);
check("branch ref exists", ref.ref === `refs/heads/${BRANCH}`, `${ref.ref} = ${ref.object.sha}`);
const sha = ref.object.sha;

// 2. base is the direct parent
const commit = await api(`/repos/${REPO}/git/commits/${sha}`);
check("base commit is the direct parent", commit.parents.length === 1 && commit.parents[0].sha === BASE, `parents=${commit.parents.map((p) => p.sha).join(",")}`);
check("commit message subject", commit.message.split("\n")[0] === "perf(vector): optimize hipVS CAGRA build/search", commit.message.split("\n")[0]);

// 3. ancestry check
const mb = await api(`/repos/${REPO}/compare/${BASE}...${sha}`);
check("base is an ancestor (status=ahead)", mb.status === "ahead", `status=${mb.status} ahead_by=${mb.ahead_by}`);
check("merge-base equals frozen base", mb.merge_base_commit && mb.merge_base_commit.sha === BASE, mb.merge_base_commit && mb.merge_base_commit.sha);

// 4. exactly the six expected paths changed
const got = new Map((mb.files || []).map((f) => [f.filename, f]));
check("changed file count is exactly 6", got.size === 6, `got ${got.size}: ${[...got.keys()].join(", ")}`);
for (const [path, spec] of EXPECTED) {
  const f = got.get(path);
  check(`changed: ${path}`, Boolean(f), f ? `${f.status} +${f.additions}/-${f.deletions}` : "NOT IN DIFF");
}
for (const path of got.keys()) {
  check(`unexpected path listing: ${path}`, EXPECTED.has(path));
}

// 5. modes in the pushed tree
const trees = new Map([["", commit.tree.sha]]);
for (const path of EXPECTED.keys()) {
  const parts = path.split("/");
  let dir = "";
  let treeSha = commit.tree.sha;
  let entry = null;
  for (const part of parts) {
    const tree = await api(`/repos/${REPO}/git/trees/${treeSha}`);
    entry = tree.tree.find((e) => e.path === part);
    if (!entry) break;
    dir = dir ? `${dir}/${part}` : part;
    treeSha = entry.sha;
  }
  const spec = EXPECTED.get(path);
  check(`tree mode ${path}`, entry && entry.mode === spec.mode, entry ? `mode=${entry.mode} expected=${spec.mode} type=${entry.type}` : "missing");
}

// 6. byte-identical contents on the remote
for (const [path, spec] of EXPECTED) {
  const local = readFileSync(join(ROOT, spec.local));
  const content = await api(`/repos/${REPO}/contents/${encodeURI(path)}?ref=${sha}`);
  const remote = Buffer.from(content.content, "base64");
  check(`bytes identical ${path}`, Buffer.compare(local, remote) === 0, `${local.length} vs ${remote.length} bytes`);
}

console.log(`\n===== ${fails === 0 ? "ALL CHECKS PASSED" : fails + " CHECK(S) FAILED"} =====`);
console.log(`repo    ${REPO}`);
console.log(`branch  ${BRANCH}`);
console.log(`commit  ${sha}`);
console.log(`url     https://github.com/${REPO}/tree/${BRANCH}`);
process.exit(fails === 0 ? 0 : 1);
