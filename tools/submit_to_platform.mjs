/**
 * Submit a task record to the OceanBase judging platform.
 *
 * Endpoints (from the platform bundle, prod host https://openwebapi.oceanbase.com):
 *   GET  /api/testplatform/taskrecord/submissionOptions?questionId=<id>
 *   POST /api/testplatform/taskrecord/commitTestPlatformTaskRecord
 *   GET  /api/testplatform/taskrecord/queryTestPlatformTaskRecordList?...
 *
 * Payload shape (built by the platform's own `buildSubmissionFields`):
 *   {
 *     questionId, gitRepo,            // gitRepo MUST be a plain https URL
 *     commitId, branch,               // omitted for artifact-style tasks
 *     extraParams: { <extraField>: value, ... }
 *   }
 *
 * The platform validates the repo link with `isValidSubmissionLink`:
 * https + hostname + NO username/password. So the token must NOT be embedded in
 * gitRepo; the private repo is reached through the platform's own credentials.
 *
 * Usage:
 *   OC_COOKIE='...' node tools/submit_to_platform.mjs --question 600076 \
 *        --repo https://github.com/tangtang-cx/ai-ecosystem \
 *        --branch 2026-competition-ecosystem --commit <sha> \
 *        --extra websiteUrl=https://cloud.dify.ai/chat/share?shareId=xxx
 */
const API_CANDIDATES = (
  process.env.OC_API_BASES ||
  "https://openwebapi.oceanbase.com,https://open.oceanbase.com,https://openwebapi-pre.oceanbase.com"
).split(",");
let API = API_CANDIDATES[0];
const COOKIE = process.env.OC_COOKIE || "";

function parseArgs(argv) {
  const args = { extra: {} };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const value = argv[index + 1];
    if (token === "--question") { args.questionId = Number(value); index += 1; }
    else if (token === "--repo") { args.gitRepo = value; index += 1; }
    else if (token === "--branch") { args.branch = value; index += 1; }
    else if (token === "--commit") { args.commitId = value; index += 1; }
    else if (token === "--extra") {
      for (const pair of value.split(",")) {
        const [key, ...rest] = pair.split("=");
        args.extra[key] = rest.join("=");
      }
      index += 1;
    }
  }
  return args;
}

async function call(path, init = {}) {
  const headers = {
    accept: "application/json",
    "content-type": "application/json",
    "x-requested-with": "XMLHttpRequest",
    referer: "https://open.oceanbase.com/",
    origin: "https://open.oceanbase.com",
    ...(init.headers || {}),
  };
  if (COOKIE) headers.cookie = COOKIE;
  const response = await fetch(`${API}${path}`, { ...init, headers });
  const text = await response.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    /* not json */
  }
  return { status: response.status, body };
}

/** Find the API host that actually serves the test-platform endpoints. */
async function discoverApi() {
  for (const candidate of API_CANDIDATES) {
    const previous = API;
    API = candidate;
    const probe = await call("/api/testplatform/taskrecord/submissionOptions?questionId=600076");
    const looksJson = probe.body && typeof probe.body === "object" && !("html" in String(probe.body).slice(0, 40));
    if (probe.status !== 404 && looksJson) {
      console.log(`api host: ${candidate}`);
      return candidate;
    }
    API = previous;
  }
  console.log(`api host: ${API} (no candidate returned JSON; check OC_API_BASES)`);
  return API;
}

const args = parseArgs(process.argv.slice(2));

if (!args.questionId) {
  console.error("usage: submit_to_platform.mjs --question <id> --repo <url> [--branch <b> --commit <sha>] [--extra k=v,...]");
  process.exit(2);
}

console.log(`question ${args.questionId}`);

await discoverApi();

// 1. what does this task ask for?
const options = await call(`/api/testplatform/taskrecord/submissionOptions?questionId=${args.questionId}`);
console.log("submissionOptions:", options.status, JSON.stringify(options.body).slice(0, 1200));

// 2. validate the repo link with the platform's own rule
try {
  const url = new URL(args.gitRepo);
  const valid = url.protocol === "https:" && Boolean(url.hostname) && !url.username && !url.password;
  console.log("gitRepo valid per platform rule:", valid, args.gitRepo);
  if (!valid) {
    console.error("gitRepo must be a plain https URL without credentials");
    process.exit(2);
  }
} catch {
  console.error("gitRepo is not a valid URL");
  process.exit(2);
}

// 3. submit
const payload = {
  questionId: args.questionId,
  gitRepo: args.gitRepo,
  ...(args.branch ? { branch: args.branch } : {}),
  ...(args.commitId ? { commitId: args.commitId } : {}),
  ...(Object.keys(args.extra).length ? { extraParams: args.extra } : {}),
};
console.log("payload:", JSON.stringify(payload));
const result = await call("/api/testplatform/taskrecord/commitTestPlatformTaskRecord", {
  method: "POST",
  body: JSON.stringify(payload),
});
console.log("submit ->", result.status, JSON.stringify(result.body).slice(0, 1500));
