#!/usr/bin/env python3
"""Insert the per-task link table into the root README (correct anchor)."""

from __future__ import annotations

from pathlib import Path

p = Path("README.md")
text = p.read_text(encoding="utf-8")

if "Dify（600076）" not in text:
    anchor = "## 提测怎么填"
    insert = """## 作品链接（每题交哪一条）

| 赛题 | 作品链接 | 状态 |
| --- | --- | --- |
| **Dify（600076）** | `https://cloud.dify.ai/chat/share?shareId=...`（导入 `dify/app.yml` 后发布） | ⏳ 待发布 —— 操作见 `Dify/LINK_GUIDE.md` |
| **Qoder（600077）** | `https://sql-review-assistant-8ptbxy0nhc9.qoder.zone/` | ✅ 已发布，未登录 HTTP 200，浏览器端 15 条规则可交互 |
| **魔搭社区** | `https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer` | ✅ 已提交成功（公开可访问） |
| 高德 / StepFun | 按对应赛题要求提供（Skill 文件 / Web 应用） | ✅ |

> ⚠️ `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` **不是 Dify 题的作品链接**：
> 它是另一个通用问答助手，跑不出我们声明的玩法，提交它会被判「主要功能运行失败」。

""" + anchor
    if anchor in text:
        text = text.replace(anchor, insert, 1)
        p.write_text(text, encoding="utf-8", newline="")
        print("README.md patched")
    else:
        print("anchor not found")
else:
    print("already present")
