"""Extract the exact payload of commitTestPlatformTaskRecord and the submission options."""

from __future__ import annotations

import re
import urllib.request

BUNDLE = "https://gw.alipayobjects.com/render/p/yuyan/180020010001011015/umi.b83b3fea.js"
UA = {"User-Agent": "Mozilla/5.0 (opencode-research)"}

request = urllib.request.Request(BUNDLE, headers=UA)
with urllib.request.urlopen(request, timeout=90) as response:
    body = response.read().decode("utf-8", "replace")

for needle, span in (
    ("commitTestPlatformTaskRecord", 900),
    ("submissionOptions", 500),
    ("backFillCommitDetail", 500),
):
    print(f"\n================ {needle} ================")
    for match in list(re.finditer(needle, body))[:3]:
        index = match.start()
        print("   ...", body[max(0, index - span): index + span].replace("\n", " "))
        print()

print("\n=== validation helpers (E / T / O around the git url) ===")
for needle in ("function E(", "function T(", "extraParams"):
    for match in list(re.finditer(re.escape(needle), body))[:2]:
        index = match.start()
        print(f"   [{needle}] ...", body[max(0, index - 260): index + 700].replace("\n", " "))
        print()
