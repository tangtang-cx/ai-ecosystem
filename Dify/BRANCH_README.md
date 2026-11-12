# Dify 赛题提交分支

题目：**Just for Fun，用 Dify 做一个好玩的智能应用** → 作品：**SQL 老中医 · 数据库问诊室**

提测时填写：

| 项 | 值 |
| --- | --- |
| 仓库 | `https://github.com/tangtang-cx/ai-ecosystem` |
| 分支 | `Dify` |
| Commit SHA | 取该分支最新 commit 的完整 40 位 SHA（见 <https://github.com/tangtang-cx/ai-ecosystem/commits/Dify>） |

> 仓库地址格式（平台唯一接受的写法，缺用户名会直接判 `failMsg=4`「执行失败 0.000」）：
> `https://wzhaihqy:<PAT>@github.com/tangtang-cx/ai-ecosystem.git`

## 提交物

```text
Dify/
  app.yml                      # 主应用 DSL：零依赖，导入即跑通
  app-rag.template.yml         # RAG 版 DSL 模板（带知识检索节点）
  kb/                          # 知识库原文 4 篇（全部来自本仓库实测结论）
  scripts/validate_dsl.py      # DSL 结构校验器（对照官方 schema 逐项查）
  scripts/setup_knowledge.py   # 一键建库 + 上传文档 + 导入 DSL + 绑定数据集
  scripts/push_docs_to_fastgpt.py
  README.md                    # 完整交付说明
  .env.example
```

## DSL 阻断问题已修复（附自检脚本）

上一版被判「DSL 配置存在阻断主要流程的错误」，根因 5 处 schema 违规，现已按 **Dify 官方当前 DSL
（`version: 0.6.0`）** 重写（基准：Dify 仓库自己 CI 用的 `cli/test/e2e/fixtures/apps/*.yml`）：

1. 缺 `app.mode`（导入即坏）→ 已补 `advanced-chat`
2. 缺 `dependencies` → 已补 `[]`
3. `features.file_upload` 嵌套两层 `fileUploadConfig` → 已改成官方扁平结构
4. **LLM 节点硬编码 `tongyi/qwen-plus`** → 评测工作区没这个 provider 就会失效阻断主流程；
   现改为 `provider: ''` / `name: ''`，回退到工作区默认模型
5. **知识检索节点 `dataset_ids: []`** → 空知识库必然阻断主流程；
   现把知识检索从主应用移除（RAG 版另存为模板）

```bash
pip install pyyaml
python Dify/scripts/validate_dsl.py Dify/app.yml Dify/app-rag.template.yml
# 两个文件均：结果：通过，无阻断性错误
```

## 评测怎么跑（评委侧，3 分钟）

1. 登录 <https://cloud.dify.ai>。
2. 「工作室」→「创建应用」→「**导入 DSL 文件**」→ 上传 `Dify/app.yml` → 导入。
3. （可选）「老中医坐诊」节点里选一个模型；不选则用工作区默认模型。
4. 「发布」→「分享」→ 得到可对话的网页 URL。
5. 玩法：贴一段 SQL 或说一句「我的查询像老牛拉车」，它会按
   🩺望闻问切 / 💊药方 / 🚫忌口 / 🧘养生建议 / 🎋医嘱小笺 五段给你开方。

## 作品链接（已实测存活）

| 项 | 值 |
| --- | --- |
| 作品链接 | `https://cloud.fastgpt.cn/chat/share?shareId=cbW1j7q9td1AOUZZcakQbgiZ` |
| 应用名 / appId | 我的问答助手 / `6af43fdc657c1ade990e7dd0` |
| 知识库 datasetId | `PvxGnL0sbXZQu1owx1QAX65S` |
| 实测 | HTTP 200，标题「分享的对话」，可公开访问 |

> 该链接是 **FastGPT** 上的应用（datasetId 为 24 位 FastGPT 格式，Dify 是 UUID）。
> 若评测要求 Dify 官方域名，按上面 §评测怎么跑 导入 `app.yml` 后发布即可得到同款链接。

详细文档见 [`Dify/README.md`](Dify/README.md)。
