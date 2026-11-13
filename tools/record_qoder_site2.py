#!/usr/bin/env python3
"""Patch the two remaining anchors with the published Qoder Sites URL."""

from __future__ import annotations

from pathlib import Path

SITE = "https://sql-review-assistant-8ptbxy0nhc9.qoder.zone/"

# Qoder/README.md — title differs from the earlier anchor
p = Path("Qoder/README.md")
text = p.read_text(encoding="utf-8")
if SITE not in text:
    anchor = "# Qoder 赛题交付物：数据库代码审查助手（seekdb 医书版）\n"
    insert = anchor + f"""
## ★ 已发布的项目网站（提测填这个）

```text
{SITE}
```

- 未登录访问返回 **HTTP 200**，页面标题「数据库代码审查助手 · Qoder × seekdb」；
- 页面是本目录 `site/index.html` 的发布版：**浏览器内可直接跑 15 条规则**
  （粘 SQL → 点「开始审查」→ 三级结果），并含真实截图、seekdb 表结构与
  `DBMS_HYBRID_SEARCH` 检索链路、运行说明、验证样例、仓库链接；
- 两张截图在站点上实测可加载（HTTP 200 / image/png）。
"""
    if anchor in text:
        text = text.replace(anchor, insert, 1)
        p.write_text(text, encoding="utf-8", newline="")
        print("Qoder/README.md patched")
    else:
        print("Qoder/README.md: anchor still not found")

# root README — add a 作品链接 row for Qoder
p2 = Path("README.md")
text2 = p2.read_text(encoding="utf-8")
if SITE not in text2:
    old = """| `qoder/` | Qoder：Build with Qoder | 数据库代码审查助手（**接 seekdb 检索与存储**）+ 运行说明 + 验证样例 |"""
    new = old + f"""
| **Qoder 项目网站** | `{SITE}` | ✅ 已发布到 Qoder Sites，未登录 HTTP 200（浏览器端 15 条规则可交互） |"""
    if old in text2:
        text2 = text2.replace(old, new, 1)
        p2.write_text(text2, encoding="utf-8", newline="")
        print("README.md patched")
    else:
        print("README.md: anchor still not found")
