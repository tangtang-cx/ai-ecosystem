// Create a branch ref pointing at an existing commit (correct creation endpoint).
const TOKEN = process.env.GH_T;
const REPO = process.env.GH_REPO;
const BRANCH = process.env.GH_BRANCH;
const SHA = process.env.GH_SHA;
if (!TOKEN || !REPO || !BRANCH || !SHA) throw new Error("GH_T/GH_REPO/GH_BRANCH/GH_SHA required");
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
  if (!res.ok) { const e = new Error(`${res.status} ${path}: ${text.slice(0, 300)}`); e.status = res.status; throw e; }
  return text ? JSON.parse(text) : null;
}
try {
  await api(`/repos/${REPO}/git/refs`, {
    method: "POST",
    body: JSON.stringify({ ref: `refs/heads/${BRANCH}`, sha: SHA }),
  });
  console.log(`created refs/heads/${BRANCH} -> ${SHA}`);
} catch (error) {
  if (error.status === 422) {
    await api(`/repos/${REPO}/git/refs/heads/${BRANCH}`, {
      method: "PATCH",
      body: JSON.stringify({ sha: SHA, force: true }),
    });
    console.log(`updated refs/heads/${BRANCH} -> ${SHA} (forced)`);
  } else throw error;
}
const ref = await api(`/repos/${REPO}/git/ref/heads/${BRANCH}`);
console.log(`VERIFIED ${REPO} ${ref.ref} = ${ref.object.sha}`);
