#!/usr/bin/env python3
"""Add the 'after import you MUST pick a model' step to the Dify README."""

from __future__ import annotations

from pathlib import Path

PATH = Path("Dify/README.md")
text = PATH.read_text(encoding="utf-8")

ANCHOR = """## 2. 三个 DSL 分别怎么用"""

NEW = """## 1.5 ★导入后必做的一步（不配模型 = 主要功能运行失败）

Dify 的 LLM 节点必须绑定一个模型，否则该节点无效，应用跑起来直接报错。本目录两个主 DSL 的模型策略：

| 文件 | 模型 | 适用 |
| --- | --- | --- |
| `app.yml` | **留空**（= 用工作区默认模型） | 工作区已配好默认模型的场景（推荐） |
| `app-with-model.yml` | 写死 `tongyi` / `qwen-plus` | 工作区已配置通义 Key，但没设默认模型 |

**操作**：cloud.dify.ai → 创建应用 → 导入 DSL 文件 → 上传 `Dify/app.yml` →
**点开「老中医坐诊」节点 → 在「模型」下拉里选一个你有 Key 的模型** → 保存。

> 如果该节点已经显示了具体模型（说明工作区有默认模型），那就不用改，直接发布即可。
> 若节点显示「模型不可用 / 未选择模型」，就是这一步没做。

然后：**发布 → 分享 → 复制链接**，把这个链接填进提测平台的「项目网站网址」——
评测要「评审可按样例体验主要功能」，所以**必须有可访问的应用链接**。

### 验证样例（照着跑，预期输出固定六段）

输入：

```sql
SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id
WHERE DATE(o.created_at) = '2026-01-01'
ORDER BY o.created_at DESC
LIMIT 20, 200000;
```

预期（**六段齐全、顺序不变**）：

```text
## 📖 医书摘录      ← 提到「函数包裹索引列 / 深分页 / SELECT *」等医书条目
## 🩺 望闻问切      ← 至少 3 条：SELECT * 全列回表、DATE(col) 索引失效、深分页扫描丢行
## 💊 药方          ← 显式列 + created_at 范围条件 + 游标分页（可复制执行）
## 🚫 忌口          ← 不要在索引列套函数、不要大 OFFSET
## 🧘 养生建议      ← 给 orders(created_at) 建索引 / 覆盖索引带排序列
## 🎋 医嘱小笺      ← 俏皮话 + 最该先改的那处
```

完整样例见 §4。

---

## 2. 三个 DSL 分别怎么用"""

if ANCHOR not in text:
    raise SystemExit("anchor not found")

text = text.replace(ANCHOR, NEW, 1)

# refresh the DSL table with the new variant
OLD_ROW = """| `app-seekdb.yml` | 检索增强版：HTTP 节点调真·seekdb 混合检索，原文注入提示词 | 自建 Dify / 本机有 seekdb 服务时 |"""
NEW_ROW = """| `app-with-model.yml` | 同上但**写死模型** `tongyi/qwen-plus` | 工作区没设默认模型时用 |
| `app-seekdb.yml` | 检索增强版：HTTP 节点调真·seekdb 混合检索，原文注入提示词 | 自建 Dify / 本机有 seekdb 服务时 |"""
text = text.replace(OLD_ROW, NEW_ROW, 1)

PATH.write_text(text, encoding="utf-8", newline="")
print("README updated; PUA chars:", sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF))
