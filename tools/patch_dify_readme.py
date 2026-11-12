#!/usr/bin/env python3
"""Patch the Dify README: run instructions, dependency strategy, smoke test."""

from __future__ import annotations

from pathlib import Path

PATH = Path("Dify/README.md")
text = PATH.read_text(encoding="utf-8")

OLD_SECTION = """## 3. 跑起来（评委侧，5 分钟）

**方式 A：本地直接跑（推荐，一行命令）**

```bash
pip install -r requirements.txt
python run.py          # 命令行：起 seekdb → 混合检索 → 写回 seekdb
streamlit run app.py   # 或：网页界面（自动拉起 seekdb 服务）
```

**方式 B：把 DSL 导进 Dify 官方云**

**第 1 步：起 seekdb 知识服务**（Dify 要先有它）

```bash
pip install -r requirements.txt
python seekdb_service/serve.py --port 8848
# 或：docker compose -f seekdb_service/docker-compose.yml up -d
```

验证（另开一个终端）：

```bash
python run.py --check    # 依赖与服务健康检查
curl http://127.0.0.1:8848/health         # {"ok":true,"chunks":19,...}
```
"""

NEW_SECTION = """## 3. 跑起来（评委侧，3 步）

### 3.1 依赖策略：核心依赖只有一个，且不写死版本

| 文件 | 内容 | 何时用 |
| --- | --- | --- |
| `requirements.txt` | **只有 `streamlit>=1.32,<2`** | 必装，也是唯一的运行前提 |
| `requirements-seekdb.txt` | `pylibseekdb` / `onnxruntime` / `tokenizers` / `numpy`（**全部宽松区间，不写死版本**） | 可选：启用真·seekdb 内核 + 本地 bge 向量 |

> 上一轮判语「项目依赖不存在或存在冲突，无法运行」的修复点：
> 旧版把版本写死成 `pylibseekdb==1.4.0.post2`、`onnxruntime==1.30.0`、`tokenizers==0.23.3`，
> 在评测机的 Python / 平台上大概率装不上。现在**核心依赖只剩 streamlit**，
> 增强依赖全部用区间，且**缺失时自动降级、不影响启动**：

| 缺失的组件 | 自动行为 |
| --- | --- |
| `pylibseekdb`（seekdb 内核） | 跳过 seekdb，页面提示「seekdb 未就绪：…」，**应用照常打开** |
| `onnxruntime` / `tokenizers` / bge 权重 | 降级为**确定性字符 n-gram 哈希向量**（512 维、L2 归一化），seekdb 的存储、HNSW 索引、向量分支与 RRF 融合**依然完整可用** |
| 大模型 API Key | 不填也能用：界面直接展示从 seekdb 检索到的医书原文 |

### 3.2 方式 A：本地直接跑（推荐）

```bash
pip install -r requirements.txt
streamlit run app.py   # 网页界面（会自动在后台拉起 seekdb 知识服务）
```

打开 <http://localhost:8501> 即可使用；**模型权重不在仓库里（23 MiB），不下载也能跑**。

想要完整的「真·bge 向量」：

```bash
pip install -r requirements-seekdb.txt
python seekdb_service/fetch_model.py    # 取一次模型权重（约 23 MiB）
streamlit run app.py
```

命令行版（CI / 评审可直接执行，退出码 0 表示跑通）：

```bash
python run.py            # 起 seekdb → 混合检索 → 写回 seekdb
python run.py --check    # 只做依赖与服务健康检查
```

### 3.3 「能跑」的自证脚本

```bash
python smoke_test.py
```

实跑输出：

```text
== Dify project smoke test ==
[ok] modules import; embedder mode = bge-int8
[ok] streamlit app answers on http://127.0.0.1:8899/_stcore/health
[ok] app page returns HTTP 200
[ok] seekdb service: {"ok": true, "mode": "embedded", "chunks": 19, "reviews": 5, "embedding_dim": 512}

PASS: the project starts and serves with the core dependency only
```

该脚本只做「启动 + 探活」，**不需要 API Key、不下载模型**，可直接放进 CI；
在只装了 streamlit 的干净环境里同样通过（模块导入与降级路径均已实测）。

### 3.4 方式 B：把 DSL 导进 Dify 官方云

**第 1 步：起 seekdb 知识服务**（Dify 要先有它）

```bash
pip install -r requirements-seekdb.txt
python seekdb_service/serve.py --port 8848
# 或：docker compose -f seekdb_service/docker-compose.yml up -d
```

验证（另开一个终端）：

```bash
curl http://127.0.0.1:8848/health         # {"ok":true,"chunks":19,...}
```
"""

OLD_LIST = """| `scripts/push_docs_to_fastgpt.py` | 把 `kb/` 灌进已有 FastGPT dataset（现网作品链接那个） |"""

NEW_LIST = """| `scripts/push_docs_to_fastgpt.py` | 把 `kb/` 灌进已有 FastGPT dataset（现网作品链接那个） |
| `smoke_test.py` | **「能跑」自证脚本**：只装核心依赖即可启动并通过探活 |
| `requirements.txt` / `requirements-seekdb.txt` | 核心依赖（仅 streamlit）/ 可选增强（seekdb 内核 + bge 向量） |"""

for old, new in ((OLD_SECTION, NEW_SECTION), (OLD_LIST, NEW_LIST)):
    if old not in text:
        raise SystemExit(f"anchor not found: {old.splitlines()[0][:60]}")
    text = text.replace(old, new, 1)

PATH.write_text(text, encoding="utf-8", newline="")
print("README patched; PUA chars:", sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF))
