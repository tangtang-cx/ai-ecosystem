#!/usr/bin/env python3
"""Make the repo docs explicit about which link belongs to which task."""

from __future__ import annotations

from pathlib import Path

# 1) Dify/README.md — a prominent link table right after the H1
p = Path("Dify/README.md")
text = p.read_text(encoding="utf-8")
if "LINK_GUIDE.md" not in text:
    anchor = "# Dify 赛题交付物：SQL 老中医 · 数据库问诊室\n"
    insert = anchor + """
> ★ **作品链接该给哪一条** → 见 [`LINK_GUIDE.md`](LINK_GUIDE.md)。
> 结论：交 **cloud.dify.ai 上导入 `app.yml` 后发布的分享链接**；
> 之前那条 `cloud.fastgpt.cn/...` 是另一个应用（通用问答助手），评委按验证样例跑它
> 跑不出我们声明的六段式开方，因此被判「主要功能运行失败」。
"""
    if anchor in text:
        text = text.replace(anchor, insert, 1)
        p.write_text(text, encoding="utf-8", newline="")
        print("Dify/README.md patched")
    else:
        print("Dify/README.md: anchor not found")

# 2) root README — a per-task link table
p2 = Path("README.md")
text2 = p2.read_text(encoding="utf-8")
if "Dify（600076）" not in text2:
    anchor2 = "## 提测信息（仓库 / 分支 / Commit SHA）"
    insert2 = """## 作品链接（每题交哪一条）

| 赛题 | 作品链接 | 状态 |
| --- | --- | --- |
| **Dify（600076）** | `https://cloud.dify.ai/chat/share?shareId=...`（导入 `dify/app.yml` 后发布） | ⏳ 待发布 —— 见 `Dify/LINK_GUIDE.md` |
| **Qoder（600077）** | `https://sql-review-assistant-8ptbxy0nhc9.qoder.zone/` | ✅ 已发布，未登录 HTTP 200，浏览器端 15 条规则可交互 |
| **魔搭社区** | `https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer` | ✅ 已提交成功（公开可访问） |
| 高德 / StepFun | 按对应赛题要求提供（Skill 文件 / Web 应用） | ✅ |

> ⚠️ `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` **不是 Dify 题的作品链接**：
> 它是另一个通用问答助手，跑不出我们声明的玩法，提交它会被判「主要功能运行失败」。

""" + anchor2
    if anchor2 in text2:
        text2 = text2.replace(anchor2, insert2, 1)
        p2.write_text(text2, encoding="utf-8", newline="")
        print("README.md patched")
    else:
        print("README.md: anchor not found")

# 3) overview
p3 = Path("AI-Ecosystem-Solutions/README.md")
text3 = p3.read_text(encoding="utf-8")
if "cloud.fastgpt.cn" not in text3:
    old = """| **作品链接（已实测存活）** | `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ`（应用「我的问答助手」，appId `6af43fdc657c1ade990e7dd0`，datasetId `PvxGnL0sbXZQu1owx1QAX65S`，HTTP 200） |"""
    new = """| **作品链接** | ⏳ 待发布：`cloud.dify.ai` 上导入 `dify/app.yml` 后分享（见 `Dify/LINK_GUIDE.md`） |
| ~~（旧）FastGPT 链接~~ | `cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` —— **不是本作品的 Dify 应用**，评委按样例跑它跑不出声明的六段式 → 判「主要功能运行失败」 |"""
    if old in text3:
        text3 = text3.replace(old, new, 1)
        p3.write_text(text3, encoding="utf-8", newline="")
        print("overview patched")
    else:
        print("overview: anchor not found")
