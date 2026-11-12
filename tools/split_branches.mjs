/**
 * Create one isolated branch per competition task from the combined commit.
 *
 *   gaode   -> gaode/SKILL.md (+ validation helper)
 *   stepfun -> stepfun/** (browser app, server, tests, docs)
 *
 * Uses the GitHub REST API because git's smart-HTTP endpoint is blocked here.
 */
import { readFile } from "node:fs/promises";

const TOKEN = process.env.GITHUB_TOKEN;
if (!TOKEN) throw new Error("GITHUB_TOKEN is required");
const REPO = process.env.GITHUB_REPO || "tangtang-cx/ai-ecosystem";
const BASE = process.env.GITHUB_BASE || "39e069f42940f726ef655e8f49aba2c527bf4f1c";
const API = "https://api.github.com";

async function api(path, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${TOKEN}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "dsh-split",
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

async function blobFromFile(path) {
  const content = await readFile(path);
  return api(`/repos/${REPO}/git/blobs`, {
    method: "POST",
    body: JSON.stringify({ content: content.toString("base64"), encoding: "base64" }),
  });
}

async function blobFromText(text) {
  return api(`/repos/${REPO}/git/blobs`, {
    method: "POST",
    body: JSON.stringify({ content: Buffer.from(text, "utf8").toString("base64"), encoding: "base64" }),
  });
}

async function upsertRef(branch, sha) {
  try {
    await api(`/repos/${REPO}/git/refs/heads/${branch}`, {
      method: "PATCH",
      body: JSON.stringify({ sha, force: true }),
    });
  } catch (error) {
    if (error.status !== 404 && error.status !== 422) throw error;
    await api(`/repos/${REPO}/git/refs`, {
      method: "POST",
      body: JSON.stringify({ ref: `refs/heads/${branch}`, sha }),
    });
  }
}

const baseCommit = await api(`/repos/${REPO}/git/commits/${BASE}`);
const baseTree = await api(`/repos/${REPO}/git/trees/${baseCommit.tree.sha}?recursive=1`);
const entries = new Map(baseTree.tree.filter((item) => item.type === "blob").map((item) => [item.path, item]));

function pick(prefix) {
  return [...entries.values()].filter(
    (item) => item.path === prefix || item.path.startsWith(`${prefix}/`),
  );
}

async function createBranch({ name, paths, readme, message }) {
  const selected = paths.flatMap((prefix) => pick(prefix));
  const gitignore = entries.get(".gitignore");
  const gitattributes = entries.get(".gitattributes");
  const readmeBlob = await blobFromText(readme);

  const tree = [];
  for (const item of selected) {
    tree.push({ path: item.path, mode: "100644", type: "blob", sha: item.sha });
  }
  if (gitignore) tree.push({ path: ".gitignore", mode: "100644", type: "blob", sha: gitignore.sha });
  if (gitattributes) tree.push({ path: ".gitattributes", mode: "100644", type: "blob", sha: gitattributes.sha });
  tree.push({ path: "README.md", mode: "100644", type: "blob", sha: readmeBlob.sha });

  const treeResult = await api(`/repos/${REPO}/git/trees`, {
    method: "POST",
    body: JSON.stringify({ tree }),
  });
  const commit = await api(`/repos/${REPO}/git/commits`, {
    method: "POST",
    body: JSON.stringify({ message, tree: treeResult.sha, parents: [BASE] }),
  });
  await upsertRef(name, commit.sha);
  console.log(`${name}: ${commit.sha} (${selected.length + 2 + 1} files)`);
  return { name, sha: commit.sha, files: selected.length };
}

const gaodeReadme = `# 高德赛题提交分支

题目：**周边去哪儿：基于高德的地点推荐助手**

提交物只有一个文件：

- [\`gaode/SKILL.md\`](gaode/SKILL.md)

该 Skill 指导 Agent 使用高德 MCP 的地点搜索、POI 详情和步行路径规划，
按用户给出的起点、地点类型、步行时间上限和数量推荐最多 3 个真实可达地点。

提测时上传 \`gaode/SKILL.md\` 即可，不需要 API Key 或后端代码。
`;

const stepfunReadme = `# StepFun 赛题提交分支

题目：**端侧 AI 推理性能优化与 seekdb 混合检索**

源码与应用在 [\`stepfun/\`](stepfun/)，包括：

- 浏览器本地 embedding（WebGPU + FP16 优先，WASM + INT8 回退）
- seekdb 内的向量 + 全文混合检索（RRF）
- 增量导入、索引刷新、质量对比
- 一页技术说明：[\`stepfun/TECH_REPORT.md\`](stepfun/TECH_REPORT.md)

启动：

\`\`\`bash
cd stepfun
npm install
npm run model:fetch
npm run serve
\`\`\`

模型权重不提交到 Git，首次运行通过 \`npm run model:fetch\` 获取。
`;

const results = [];
results.push(
  await createBranch({
    name: "gaode",
    paths: ["gaode", "tools/check_skill.py"],
    readme: gaodeReadme,
    message: "feat(gaode): add nearby destination recommendation skill",
  }),
);
results.push(
  await createBranch({
    name: "stepfun",
    paths: ["stepfun"],
    readme: stepfunReadme,
    message: "feat(stepfun): add browser-local embedding and seekdb hybrid retrieval app",
  }),
);

console.log("\nBranches:");
for (const item of results) {
  console.log(`  ${item.name}  ${item.sha}`);
  console.log(`  https://github.com/${REPO}/tree/${item.name}`);
}
