"""Find the judging platform's API host (config module: Or / Ij)."""

from __future__ import annotations

import re
import urllib.request

BUNDLE = "https://gw.alipayobjects.com/render/p/yuyan/180020010001011015/umi.b83b3fea.js"
UA = {"User-Agent": "Mozilla/5.0 (opencode-research)"}

request = urllib.request.Request(BUNDLE, headers=UA)
with urllib.request.urlopen(request, timeout=90) as response:
    body = response.read().decode("utf-8", "replace")

print("=== oceanbase hosts in the bundle ===")
for hit in sorted(set(re.findall(r"https?://[a-zA-Z0-9.\-]*oceanbase[a-zA-Z0-9.\-/]*", body))):
    print("  ", hit)

print("\n=== config-ish assignments around 'Or:' / 'Ij:' ===")
for key in ("Or:", "Ij:", "or:", "ij:"):
    for match in list(re.finditer(re.escape(key), body))[:4]:
        index = match.start()
        snippet = body[max(0, index - 120): index + 200].replace("\n", " ")
        print(f"  [{key}] ...{snippet}...")

print("\n=== '/api/' style base strings ===")
for hit in sorted(set(re.findall(r"[\"']/[a-zA-Z0-9/_-]{2,40}[\"']", body)))[:0]:
    print("  ", hit)
for hit in sorted(set(re.findall(r"[\"']https?://[^\"']{6,80}openapi[^\"']{0,30}[\"']", body)))[:20]:
    print("  ", hit)
