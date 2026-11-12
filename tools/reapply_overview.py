#!/usr/bin/env python3
"""Re-apply the AI-Ecosystem-Solutions updates on top of the clean README.

Run once after restoring the file from git (the previous in-place edits were
applied with a GBK-decoding editor and corrupted the encoding).
"""

from __future__ import annotations

import sys
from pathlib import Path

PATH = Path("AI-Ecosystem-Solutions/README.md")
text = PATH.read_text(encoding="utf-8")

# ---------------------------------------------------------------- 1. 提测信息表
OLD_TABLE = """## 提测信息（仓库 / 分支 / Commit SHA）

仓库：`https://github.com/tangtang-cx/ai-ecosystem`（私有库）

| 赛题 | 分支 | Commit SHA（40 位） | 分支内容 |
| --- | --- | --- | --- |
| Dify | `Dify` | `88b8460113b56f1a99590c8326f2a0a025f636a8` | `Dify/`（DSL + 知识库 + 脚本） |
| Qoder | `qoder` | `a97d78f4bf837fa6bc04a8ef02253a03c4f0aee6` | `Qoder/`（应用 + 规则 + 测试） |
| 魔搭社区 | `modelscope` | `c5bfe6e237d77941fb77eb7a5b098d29db8acd94` | `魔搭/`（代码 + 录屏 + 测试） |
| 高德 | `gaode` | `55c0faebea36a0900d7c54ee647a9c453e099fa7` | `gaode/SKILL.md` |
| StepFun | `stepfun` | `ec22a31e539d4ece0657b68ebdbc35f02c9bff92` | `stepfun/` |
| AMD | `amd-cagra-solution` | `fced626b49611b8e37be0dd1bac8559220cfabe6` | `amd/`（需 apply 到 seekdb fork） |
| 生态赛题合并版 | `2026-competition-ecosystem` | `81e8c574ba8a0a48ca33285434766f84046825eb` | 三个生态赛题 + 高德 + StepFun |
"""

NEW_TABLE = """## 提测信息（仓库 / 分支 / Commit SHA）

仓库：`https://github.com/tangtang-cx/ai-ecosystem`（私有库）

> **所有赛题分支都基于官方基线** `oceanbase/powercontext@2026-competition-ecosystem`
> = `d647275c308e09b7b623f322a26f5c4e85734fb0`（该基线已在我们的仓库中重建为同名 commit，
> 因此 `git merge-base --is-ancestor d647275c <提交>` 可直接校验）。
> 资产按官方脚手架放在对应目录：`dify/` `qoder/` `gaode/` `stepfun/` `minimax/`。

| 赛题 | 分支 | Commit SHA（40 位） | 分支内容 |
| --- | --- | --- | --- |
| Dify | `Dify` | `9e0f9518c0bb265042e82f99c59c78d3ee1a2608` | `dify/`（DSL + 真·seekdb 服务） |
| Qoder | `qoder` | `1d7511a27b1b705d314116bec8ca7ad38541ac95` | `qoder/`（审查助手 + seekdb 集成） |
| 魔搭社区 | `modelscope` | `21859ebcbbe273a0e2d6cc181437bbda05ffba6d` | `modelscope/`（助手 + 已上传的 Skill） |
| 高德 | `gaode` | `8ffa33ae6a9cf0f2b3b969e858b9c846fb867dd3` | `gaode/SKILL.md` |
| StepFun | `stepfun` | `062d9c12e48abb91f20033b2135585495bf2ced7` | `stepfun/` |
| 全部生态赛题合并版 | `2026-competition-ecosystem` | `b03806478ee18ea0bc9469389e9da534adcaecb4` | 六个赛题目录 + 总览 |
| 加赛（PowerContext） | `2026-competition-powercontext` | `c06bca1b9a134231689d5616f7f0f5392cd005a4` | PowerContext 实现 |

> 仓库地址在提测平台必须写成 `https://<用户名>:<令牌>@github.com/tangtang-cx/ai-ecosystem.git`
> （官方只接受这一种格式，缺用户名会判 `failMsg=4` → 「执行失败 0.000」）。
"""

# ---------------------------------------------------------------- 2. Qoder 段
OLD_QODER_HEAD = """## 3. Qoder · 数据库代码审查助手

**目录**：`Qoder/` · 提示词与发布说明见 `Qoder/PROMPT.md`
"""

NEW_QODER_HEAD = """## 3. Qoder · 数据库代码审查助手（seekdb 版）

**目录**：`qoder/` · 提示词与发布说明见 `qoder/PROMPT.md`
"""

OLD_QODER_BODY = """3. **两层合并展示**：规则层给「问题 + 建议 + 命中片段」，LLM 层给语义级判断，
   统一成 🔴阻断 / 🟠警告 / 🔵提示 三级。
4. **可导出**：Markdown 评审报告 + JSON，答辩直接贴报告。
"""

NEW_QODER_BODY = """3. **真正用上 seekdb**（官方要求「实际使用」，只装不跑不算）：
   - **检索**：每次审查先用 seekdb 做「向量 + 全文 + RRF」混合检索，取回相关「医书」条目作为审查依据，
     界面可展开核对；
   - **存储**：每一轮审查结果**写回 seekdb** 的 `qoder_review_log` 表，
     界面里的「seekdb 里的审查历史」是实时从 seekdb 查出来的；
   - 底层实现与服务端见 `dify/seekdb_service/`（真 seekdb 内核 + 本地 bge-small-zh INT8 向量）。
4. **可导出**：Markdown 评审报告 + JSON，答辩直接贴报告。
"""

OLD_QODER_LINKS = """| Qoder 对话 + 生成 diff | ⏳ `Qoder/screenshots/01-qoder-chat.png`（发布后补） |
| Qoder Sites 公网链接 | ⏳ `Qoder/screenshots/03-qoder-sites.png`（发布后补） |
| 应用运行界面 | ⏳ `Qoder/screenshots/04-app-running.png`（发布后补） |
"""

NEW_QODER_LINKS = """| Qoder 对话 + 生成 diff | ⏳ `qoder/screenshots/01-qoder-chat.png`（发布后补） |
| Qoder Sites 公网链接 | ⏳ `qoder/screenshots/03-qoder-sites.png`（发布后补） |
| 应用运行界面（已自动实拍） | ✅ `qoder/screenshots/04-app-home.png`、`05-app-review-results.png` |
| 运行说明 + 验证样例（4 组，可按步骤执行） | ✅ `qoder/README.md` §2、§3 |
| Qoder 开发记录清单（截图位 + 账号 UID） | ✅ `qoder/README.md` §4 |
"""

OLD_QODER_CODE = """# Qoder/app.py —— 两层合并
findings = analyze(sql)          # 确定性规则
llm_result = reviewer.review(sql, extra_context=extra_context)   # LLM 深审
merged = findings + llm_result.findings
```

测试：`python Qoder/tests/test_rules.py -v` → **23 passed**（22 规则 + 1 UI 冒烟）。
"""

NEW_QODER_CODE = """# qoder/seekdb_bridge.py —— 与 seekdb 的双向交互
hits = seekdb_bridge.search_knowledge(sql[:500], kb_url, top_k=3)    # 检索依据
seekdb_bridge.save_review(sql=sql, findings=..., engine="rules+llm")  # 写回历史
seekdb_bridge.list_reviews()                                            # 实时查历史

# qoder/app.py —— 三层合并
findings = analyze(sql)                        # 确定性规则
kb_hits = seekdb_bridge.search_knowledge(...)  # seekdb 混合检索
llm_findings = reviewer.review(sql, extra_context=kb_context).findings
```

测试：`python qoder/tests/test_rules.py -v` → **22 passed**；
`python qoder/tests/test_app_smoke.py -v` → **1 passed**。
"""

# ---------------------------------------------------------------- 3. 魔搭段
OLD_MS_HEAD = """## 7. 魔搭社区（ModelScope）· AI 问答助手

**目录**：`魔搭/` · 客户端 `魔搭/modelscope_client.py` · 录屏 `魔搭/第三题.mp4`
"""

NEW_MS_HEAD = """## 7. 魔搭社区（ModelScope）· 上传并分享一个 Skill

**目录**：`modelscope/` · **提交物：`modelscope/SKILL.md`（Skill 本体）** · 上传指引 `modelscope/SKILL_UPLOAD.md`
"""

OLD_MS_LINKS = """| **运行录屏** | `魔搭/第三题.mp4`（已提交） |
| 魔搭 API Key 获取路径 | `魔搭/README.md` §2 |
| 创空间部署步骤 | `魔搭/README.md` §6 |
| 创空间公网链接 | ⏳ 待部署后补 |
"""

NEW_MS_LINKS = """| **Skill 网址（已上传，公开可访问，实测 HTTP 200）** | `https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer` |
| Skill 本体（源码留档） | ✅ `modelscope/SKILL.md`（+ `scripts/`、`references/`） |
| 上传步骤 + 表单填写 | ✅ `modelscope/SKILL_UPLOAD.md` |
| 规则脚本自检 | ✅ `python modelscope/scripts/review_rules.py "<SQL>"` |
| 运行录屏（推理助手） | ✅ `modelscope/第三题.mp4` |
"""

OLD_MS_CODE = """# 魔搭/modelscope_client.py
"""

NEW_MS_CODE = """# modelscope/modelscope_client.py
"""

REPLACEMENTS = [
    (OLD_TABLE, NEW_TABLE),
    (OLD_QODER_HEAD, NEW_QODER_HEAD),
    (OLD_QODER_BODY, NEW_QODER_BODY),
    (OLD_QODER_LINKS, NEW_QODER_LINKS),
    (OLD_QODER_CODE, NEW_QODER_CODE),
    (OLD_MS_HEAD, NEW_MS_HEAD),
    (OLD_MS_LINKS, NEW_MS_LINKS),
    (OLD_MS_CODE, NEW_MS_CODE),
]

missing = []
for old, new in REPLACEMENTS:
    if old not in text:
        missing.append(old.splitlines()[0][:70])
        continue
    text = text.replace(old, new, 1)

if missing:
    print("anchors not found:")
    for item in missing:
        print("  ", item)

PATH.write_text(text, encoding="utf-8", newline="")
pua = sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF)
print(f"written, PUA chars: {pua}")
