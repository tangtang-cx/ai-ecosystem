import re
import urllib.request

BASE = "https://sql-review-assistant-8ptbxy0nhc9.qoder.zone/"
req = urllib.request.Request(BASE, headers={"User-Agent": "opencode-check"})
with urllib.request.urlopen(req, timeout=40) as response:
    html = response.read().decode("utf-8", "replace")

print("length:", len(html))
ids = sorted(set(re.findall(r"OB-\d{3}", html)))
print("rule ids present:", ids)
print("count:", len(ids))
for marker in ("function analyze", "addEventListener", "开始审查", "seekdb", "qoder_review_log",
                "向量 + 全文 + RRF", "DBMS_HYBRID_SEARCH", "验证样例", "运行说明",
                "screenshots/", "trycloudflare", "github.com/tangtang-cx/ai-ecosystem"):
    print(f"  contains {marker!r}: {marker in html}")
scripts = re.findall(r"<script[^>]*>([\s\S]{0,400})", html)
print("inline script blocks:", len(scripts))
inline = "\n".join(scripts)
print("inline js chars:", len(inline))
print("inline has analyze():", "analyze(" in inline)
print("inline has OB- rules:", len(re.findall(r"OB-\d{3}", inline)))
imgs = re.findall(r'src="([^"]+)"', html)
print("images:", imgs[:6])
