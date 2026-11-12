# Dify 赛题提交分支

题目：**Dify · OceanBase 向量库文档问答助手**

提测时填写：

| 项 | 值 |
| --- | --- |
| 仓库 | `https://github.com/tangtang-cx/ai-ecosystem` |
| 分支 | `Dify` |
| Commit SHA | 取该分支最新 commit 的完整 40 位 SHA（见 <https://github.com/tangtang-cx/ai-ecosystem/commits/Dify>） |

## 提交物

```text
Dify/
  app.yml                  # Dify 应用 DSL（知识检索 + LLM + 直接回复），一键导入
  kb/                      # 知识库原文 4 篇（全部来自本仓库实测结论）
    01-seekdb-向量库速查.md
    02-混合检索与RRF.md
    03-端侧向量化与量化对比.md
    04-AMD-GPU加速HNSW.md
  scripts/setup_knowledge.py   # 一键：建知识库 + 上传文档 + 导入 DSL + 绑定数据集
  README.md                # 完整交付说明（零代码路径 + 自动化路径 + 截图清单）
  .env.example             # 配置样例
```

## 作品链接（已实测存活）

| 项 | 值 |
| --- | --- |
| 作品链接 | `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` |
| 应用名 / appId | 我的问答助手 / `6af43fdc657c1ade990e7dd0` |
| 知识库 datasetId | `PvxGnL0sbXZQu1owx1QAX65S` |
| 实测 | HTTP 200，标题「分享的对话」，可公开访问 |

> 该链接是 **FastGPT**（`cloud.fastgpt.cn`）上的应用——datasetId 是 24 位 FastGPT 格式（Dify 是 UUID）。
> 若评测要求 Dify 官方域名，用下面的 `app.yml` 在 cloud.dify.ai 导入后发布即可得到同款链接。

## 评测怎么跑（评委侧，5 分钟）

1. 登录 <https://cloud.dify.ai>。
2. 「知识库」→ 创建 → 从文件导入 → 上传 `Dify/kb/` 下 4 个 `.md` → 索引选「高质量」。
3. 「工作室」→ 创建应用 → **导入 DSL 文件** → 上传 `Dify/app.yml`。
4. 「知识检索」节点选中刚建的知识库 → 「生成回答」节点选模型 → 保存。
5. 「发布」→「分享」→ 得到可对话的网页 URL。

不想手点就跑脚本：

```bash
export DIFY_BASE_URL=https://cloud.dify.ai
export DIFY_API_KEY=app-xxxxxxxx      # 知识库 -> API -> Knowledge API key
python Dify/scripts/setup_knowledge.py dataset
export DIFY_CONSOLE_TOKEN=xxxxxxxx    # 浏览器 cookie
python Dify/scripts/setup_knowledge.py app --dataset-id <上一步输出的 id>
```

## 自检问题（知识库内均有答案）

```text
HNSW 向量索引的建表语句是什么？
混合检索（向量 + 全文）如何用 RRF 融合？
端侧 INT8 量化会损失多少召回率？
```

详细文档见 [`Dify/README.md`](Dify/README.md)。
