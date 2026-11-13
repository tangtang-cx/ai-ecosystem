"""Locate the judging platform's submission endpoints (open.oceanbase.com).

Fetches the training platform page, follows its JS bundles and greps for the
test-platform API paths, so we know exactly what to POST when we have a session.
"""

from __future__ import annotations

import re
import urllib.request

PAGES = [
    "https://open.oceanbase.com/train",
    "https://open.oceanbase.com/competition",
]

UA = {"User-Agent": "Mozilla/5.0 (opencode-research)"}


def get(url: str, timeout: int = 45) -> str:
    try:
        request = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", "replace")
    except Exception as error:
        return f"<!-- ERR {type(error).__name__}: {error} -->"


PATTERNS = [
    r"/api/[a-z0-9/_-]*(?:test|testplatform|train|competition|submit|task)[a-z0-9/_-]*",
    r"[a-zA-Z]*(?:queryTestPlatform|submitTestPlatform|saveTestPlatform|createTestPlatform)[a-zA-Z]*",
]

seen: set[str] = set()
scripts: list[str] = []

for page in PAGES:
    html = get(page)
    print(f"\n### {page}  ({len(html)} bytes)")
    if html.startswith("<!-- ERR"):
        print("   ", html[:200])
        continue
    for match in re.findall(r'<script[^>]+src="([^"]+)"', html):
        if match not in scripts:
            scripts.append(match)
    for pattern in PATTERNS:
        for hit in sorted(set(re.findall(pattern, html))):
            if hit not in seen:
                seen.add(hit)
                print("   inline:", hit)

print(f"\n### scripts referenced: {len(scripts)}")
for src in scripts[:12]:
    url = src if src.startswith("http") else "https://open.oceanbase.com" + ("" if src.startswith("/") else "/") + src
    body = get(url)
    if body.startswith("<!-- ERR"):
        print(f"   - {url}  {body[:80]}")
        continue
    hits: set[str] = set()
    for pattern in PATTERNS:
        hits.update(re.findall(pattern, body))
    if hits:
        print(f"   - {url}  ({len(body)} bytes)")
        for hit in sorted(hits)[:25]:
            print("        ", hit)
