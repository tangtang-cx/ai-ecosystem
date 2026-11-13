"""Extract every test-platform API path and method name from the platform bundle."""

from __future__ import annotations

import re
import urllib.request

BUNDLE = "https://gw.alipayobjects.com/render/p/yuyan/180020010001011015/umi.b83b3fea.js"
UA = {"User-Agent": "Mozilla/5.0 (opencode-research)"}

request = urllib.request.Request(BUNDLE, headers=UA)
with urllib.request.urlopen(request, timeout=90) as response:
    body = response.read().decode("utf-8", "replace")
print("bundle bytes:", len(body))

print("\n=== /api/testplatform/... paths ===")
for hit in sorted(set(re.findall(r"/api/testplatform/[a-zA-Z0-9/_-]+", body))):
    print("  ", hit)

print("\n=== *TestPlatform* identifiers ===")
for hit in sorted(set(re.findall(r"[a-zA-Z]{0,12}TestPlatform[a-zA-Z]{0,24}", body))):
    print("  ", hit)

print("\n=== context around repo/branch/commit fields ===")
for key in ("repoUrl", "repo_url", "branch", "commitId", "commit_id", "gitUrl", "codeUrl", "taskId", "questionId", "siteUrl", "websiteUrl"):
    indexes = [m.start() for m in re.finditer(key, body)][:2]
    for index in indexes:
        snippet = body[max(0, index - 160): index + 220].replace("\n", " ")
        print(f"  [{key}] ...{snippet}...")
