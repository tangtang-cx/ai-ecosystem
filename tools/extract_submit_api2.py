"""Extract the test-platform task-record endpoints and the submit payload shape."""

from __future__ import annotations

import re
import urllib.request

BUNDLE = "https://gw.alipayobjects.com/render/p/yuyan/180020010001011015/umi.b83b3fea.js"
UA = {"User-Agent": "Mozilla/5.0 (opencode-research)"}

request = urllib.request.Request(BUNDLE, headers=UA)
with urllib.request.urlopen(request, timeout=90) as response:
    body = response.read().decode("utf-8", "replace")

print("=== all taskrecord paths ===")
for hit in sorted(set(re.findall(r"/testplatform/taskrecord/[a-zA-Z0-9/_?=&${}.-]+", body))):
    print("  ", hit)

print("\n=== 'modelscope/verification' occurrences with context ===")
for match in list(re.finditer(r"modelscope/verification", body))[:6]:
    index = match.start()
    print("   ...", body[max(0, index - 420): index + 320].replace("\n", " "), "\n")

print("\n=== submit-ish identifiers ===")
for hit in sorted(set(re.findall(r"[a-zA-Z]{0,20}(?:[Ss]ubmit|[Tt]askRecord|taskrecord)[a-zA-Z]{0,24}", body))):
    if len(hit) > 4:
        print("  ", hit)
