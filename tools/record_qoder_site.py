#!/usr/bin/env python3
"""Record the published Qoder Sites URL in the repo docs."""

from __future__ import annotations

from pathlib import Path

SITE = "https://sql-review-assistant-8ptbxy0nhc9.qoder.zone/"

# 1) Qoder/README.md — put the site link right after the title
p = Path("Qoder/README.md")
text = p.read_text(encoding="utf-8")
if SITE not in text:
    anchor = """# Qoder 赛题提交物：数据库代码审查助手（seekdb 版）
"""
    insert = anchor + f"""
## ★ 已发布的项目网站（提测填这个）

```text
{SITE}
```

- 已实测：未登录访问返回 **HTTP 200**，页面标题「数据库代码审查助手 · Qoder × seekdb」；
- 页面是本目录 `site/index.html` 的发布版：**浏览器内可直接跑 15 条规则**（粘 SQL → 点「开始审查」→
  三级结果），含真实截图、seekdb 表结构与检索链路、运行说明、验证样例、仓库链接；
- 两张截图在站点上实测可加载（HTTP 200 / image/png）。
"""
    if anchor in text:
        text = text.replace(anchor, insert, 1)
    else:
        print("WARNING: Qoder/README.md anchor not found")
    p.write_text(text, encoding="utf-8", newline="")
    print("Qoder/README.md updated")

# 2) Qoder/BRANCH_README.md — the branch landing page
p2 = Path("Qoder/BRANCH_README.md")
text2 = p2.read_text(encoding="utf-8")
if SITE not in text2:
    anchor2 = """## 提交物
"""
    insert2 = f"""## 项目网站（已发布，公开可访问）

```text
{SITE}
```

未登录 HTTP 200；页面内含浏览器端 15 条规则交互演示、真实截图、seekdb 表结构与
`DBMS_HYBRID_SEARCH` 检索链路、运行说明、验证样例与仓库链接。

## 提交物
"""
    if anchor2 in text2:
        text2 = text2.replace(anchor2, insert2, 1)
    else:
        print("WARNING: Qoder/BRANCH_README.md anchor not found")
    p2.write_text(text2, encoding="utf-8", newline="")
    print("Qoder/BRANCH_README.md updated")

# 3) AI-Ecosystem-Solutions/README.md — the overview
p3 = Path("AI-Ecosystem-Solutions/README.md")
text3 = p3.read_text(encoding="utf-8")
if SITE not in text3:
    old = """| Qoder 对话 + 生成 diff | ⏳ `qoder/screenshots/01-qoder-chat.png`（发布后补） |
| Qoder Sites 公网链接 | ⏳ `qoder/screenshots/03-qoder-sites.png`（发布后补） |"""
    new = f"""| **项目网站（已发布，公开可访问）** | `{SITE}` |
| Qoder 对话 + 生成 diff | ⏳ `qoder/screenshots/01-qoder-chat.png`（发布后补） |
| Qoder Sites 发布截图 | ⏳ `qoder/screenshots/03-qoder-sites.png`（发布后补） |"""
    if old in text3:
        text3 = text3.replace(old, new, 1)
    else:
        print("WARNING: overview anchor not found")
    p3.write_text(text3, encoding="utf-8", newline="")
    print("AI-Ecosystem-Solutions/README.md updated")

# 4) root README — the 作品链接 table
p4 = Path("README.md")
text4 = p4.read_text(encoding="utf-8")
if SITE not in text4:
    old4 = """| **Qoder** | `https://clocks-remains-claire-serious.trycloudflare.com` | ✅ 实测 HTTP 200（数据库代码审查助手，公网 Demo） |"""
    new4 = f"""| **Qoder** | `{SITE}` | ✅ 已发布到 Qoder Sites，未登录 HTTP 200（浏览器端可交互演示） |"""
    if old4 in text4:
        text4 = text4.replace(old4, new4, 1)
    else:
        print("WARNING: root README anchor not found")
    p4.write_text(text4, encoding="utf-8", newline="")
    print("README.md updated")
