#!/usr/bin/env python3
"""Final patch of AI-Ecosystem-Solutions/README.md (UTF-8 safe, exact anchors)."""

from __future__ import annotations

from pathlib import Path

PATH = Path("AI-Ecosystem-Solutions/README.md")
text = PATH.read_text(encoding="utf-8")

OLD_TABLE = """| 赛题 | 分支 | Commit SHA（40 位） | 分支内容 |
| --- | --- | --- | --- |
| Dify | `Dify` | `50437db84813970208381f931147eb57deca8c6b` | `Dify/`（DSL + 知识库 + 脚本） |
| Qoder | `qoder` | `a97d78f4bf837fa6bc04a8ef02253a03c4f0aee6` | `Qoder/`（应用 + 规则 + 测试） |
| 魔搭社区 | `modelscope` | `c5bfe6e237d77941fb77eb7a5b098d29db8acd94` | `魔搭/`（代码 + 录屏 + 测试） |
| 高德 | `gaode` | `55c0faebea36a0900d7c54ee647a9c453e099fa7` | `gaode/SKILL.md` |
| StepFun | `stepfun` | `ec22a31e539d4ece0657b68ebdbc35f02c9bff92` | `stepfun/` |
| AMD | `amd-cagra-solution` | `fced626b49611b8e37be0dd1bac8559220cfabe6` | `amd/`（需 apply 到 seekdb fork） |
| 生态赛题合并版 | `2026-competition-ecosystem` | 见仓库该分支最新提交 | 三个生态赛题 + 高德 + StepFun |

> 每个分支都含官方基线提交 `39e069f4`；每个分支根目录的 `README.md` 都写了该题的评测跑法。"""

NEW_TABLE = """> **所有赛题分支都基于官方基线** `oceanbase/powercontext@2026-competition-ecosystem`
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
> （官方只接受这一种格式，缺用户名会判 `failMsg=4` → 「执行失败 0.000」）。"""

OLD_QODER_CODE = """# Qoder/app.py —— 两层合并
findings = analyze(sql)          # 确定性规则
llm_result = reviewer.review(sql, extra_context)   # LLM 深审
merged = findings + llm_result.findings
```

测试：`python Qoder/tests/test_rules.py -v` → **23 passed**（22 规则 + 1 UI 冒烟）。"""

NEW_QODER_CODE = """# qoder/seekdb_bridge.py —— 与 seekdb 的双向交互
hits = seekdb_bridge.search_knowledge(sql[:500], kb_url, top_k=3)     # 检索依据
seekdb_bridge.save_review(sql=sql, findings=..., engine="rules+llm")  # 写回历史
seekdb_bridge.list_reviews()                                            # 实时查历史

# qoder/app.py —— 三层合并
findings = analyze(sql)                        # 确定性规则
kb_hits = seekdb_bridge.search_knowledge(...)  # seekdb 混合检索
llm_findings = reviewer.review(sql, extra_context=kb_context).findings
```

测试：`python qoder/tests/test_rules.py -v` → **22 passed**；
`python qoder/tests/test_app_smoke.py -v` → **1 passed**。"""

missing = []
for old, new in ((OLD_TABLE, NEW_TABLE), (OLD_QODER_CODE, NEW_QODER_CODE)):
    if old not in text:
        missing.append(old.splitlines()[0][:60])
        continue
    text = text.replace(old, new, 1)

PATH.write_text(text, encoding="utf-8", newline="")
pua = sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF)
print(f"written, PUA chars: {pua}")
if missing:
    print("anchors not found:", missing)
