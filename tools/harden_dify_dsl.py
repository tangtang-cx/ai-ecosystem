#!/usr/bin/env python3
"""Harden the Dify DSLs against "main function fails to run".

Changes:
  * file_upload is disabled (one less runtime dependency on object storage);
  * the app description states the one manual step a judge MUST do after import
    (pick a model for the LLM node, otherwise the node is invalid);
  * a second DSL with a concrete model is generated for workspaces where the
    default chat model is not configured.
"""

from __future__ import annotations

from pathlib import Path

APP = Path("Dify/app.yml")

text = APP.read_text(encoding="utf-8")

# 1. disable file upload (keeps the runtime surface minimal)
text = text.replace(
    """      allowed_file_upload_methods:
        - local_file
        - remote_url
      enabled: true""",
    """      allowed_file_upload_methods:
        - local_file
        - remote_url
      enabled: false""",
)

# 2. make the "pick a model" step explicit in the app description
old_desc = """  description: SQL 老中医 · 数据库问诊室。把 SQL、报错或「数据库不舒服」的描述交给老中医，
    他会按固定六段式给出「医书摘录 / 病灶诊断 / 药方 / 忌口 / 养生建议 / 医嘱小笺」。
    本 DSL 零外部依赖，导入即可运行；配套的 seekdb 版本见 app-seekdb.yml。"""
new_desc = """  description: SQL 老中医 · 数据库问诊室。把 SQL、报错或「数据库不舒服」的描述交给老中医，
    他会按固定六段式给出「医书摘录 / 病灶诊断 / 药方 / 忌口 / 养生建议 / 医嘱小笺」。
    本 DSL 零外部依赖。★导入后必做一步★：点开「老中医坐诊」节点选一个模型
    （留空 = 用工作区默认模型；若该节点显示「模型不可用」，说明工作区没配默认模型，
    选一个即可）。配套的 seekdb 检索增强版见 app-seekdb.yml。"""
if old_desc in text:
    text = text.replace(old_desc, new_desc, 1)
else:
    print("WARNING: description anchor not found")

APP.write_text(text, encoding="utf-8", newline="")
print("app.yml hardened")

# 3. variant with an explicit model for workspaces without a default chat model
variant = text.replace(
    """  name: SQL 老中医 · 数据库问诊室""",
    """  name: SQL 老中医 · 数据库问诊室（通义版）""",
    1,
).replace(
    """          model:
            provider: ''
            name: ''
            mode: chat""",
    """          model:
            provider: tongyi
            name: qwen-plus
            mode: chat""",
    1,
).replace(
    """    本 DSL 零外部依赖。★导入后必做一步★：点开「老中医坐诊」节点选一个模型
    （留空 = 用工作区默认模型；若该节点显示「模型不可用」，说明工作区没配默认模型，
    选一个即可）。配套的 seekdb 检索增强版见 app-seekdb.yml。""",
    """    本文件已指定模型 provider=tongyi / model=qwen-plus（需工作区已配置通义 Key）。
    若工作区用的是别的模型供应商，请改用 app.yml（留空模型 = 用工作区默认模型）。
    配套的 seekdb 检索增强版见 app-seekdb.yml。""",
    1,
)
Path("Dify/app-with-model.yml").write_text(variant, encoding="utf-8", newline="")
print("app-with-model.yml written")
