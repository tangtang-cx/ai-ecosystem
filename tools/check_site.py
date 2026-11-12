import re
from pathlib import Path

html = Path("Qoder/site/index.html").read_text(encoding="utf-8")
imgs = re.findall(r'src="([^"]+)"', html)
print("images referenced:", imgs)
for name in imgs:
    print("  ", name, "exists:", (Path("Qoder/site") / name).exists())
print("has run button:", "开始审查" in html)
print("rules embedded:", len(re.findall(r"id:'OB-", html)))
print("size:", len(html), "chars")
