#!/usr/bin/env python3
"""Document the edge fix in the Dify README (why a re-import is required)."""

from __future__ import annotations

from pathlib import Path

p = Path("Dify/README.md")
text = p.read_text(encoding="utf-8")

block = """
---

## 0.1 ★重要：上一版「主要功能运行失败」的根因（已修，必须重新导入发布）

判语：**「主要功能运行失败。」**

用真浏览器驱动已发布应用，抓到的 SSE 事件给出了确切原因：

```text
node_finished  llm     status=succeeded  elapsed=28.46s  total_tokens=3049
node_finished  answer  status=succeeded  outputs={}          ← 空
workflow_finished        outputs={"answer": ""}               ← 空
node_finished  llm     predecessor_node_id = null            ← 边没接上
```

模型**确实生成了内容**（3049 tokens、28 秒），但**回答节点输出为空**，
原因是 **DSL 的 `edges` 少了 `type: custom` 与 `data.sourceType/targetType`**：
Dify 导入时**丢弃了这些边**，三个节点各跑各的，answer 节点拿不到 `llm.text`，
于是 `{{#llm.text#}}` 解析成空串 → 界面上只看到开场白，看不到回答。

现在所有边都改成 Dify 官方导出的形状：

```yaml
    edges:
      - data:
          sourceType: start
          targetType: llm
        id: start-llm
        source: start
        sourceHandle: source
        target: llm
        targetHandle: target
        type: custom
```

校验器也加了这条规则（去掉 `type: custom` 会直接判不通过）：

```bash
python Dify/scripts/validate_dsl.py Dify/app.yml     # 通过
```

> ⚠️ **必须用新 DSL 重新导入并重新发布**：老应用里的图还是断的，发布也不会自动更新图。
> 导入新 `app.yml` 后**再点一次「发布」**，然后用无痕窗口按 §4 的样例验证：
> 提问后应当出现**完整六段**，而不是只有开场白。

"""

anchor = "---\n\n## 1. 核心玩法与声明"
if "0.1 ★重要" not in text and anchor in text:
    text = text.replace(anchor, block + "\n## 1. 核心玩法与声明", 1)
    p.write_text(text, encoding="utf-8", newline="")
    print("README patched")
elif "0.1 ★重要" in text:
    print("already patched")
else:
    print("anchor not found")
