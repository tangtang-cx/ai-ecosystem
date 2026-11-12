# Qoder 赛题交付物：数据库代码审查助手

> 题目要求：用 Qoder 的 AI 在云端生成代码，并把项目发布成可访问的链接。
> 本目录是 **Qoder 生成 + 本仓库增强** 的完整项目：`app.py`（Streamlit UI）、
> `reviewer.py`（静态规则引擎 + OpenAI 兼容客户端）、`rules/`（规则文档）、`tests/`（单测）。

---

## 1. 交付物清单

| 文件 | 说明 |
| --- | --- |
| `app.py` | Streamlit 主程序（侧边栏模型配置 + SQL 输入 + 三级结果 + 报告导出） |
| `reviewer.py` | 15 条确定性静态规则 + OpenAI 兼容 LLM 客户端（仅标准库） |
| `rules/sql_review_rules.md` | 规则说明，编号与实现一一对应 |
| `tests/test_rules.py` | 22 个单测，覆盖每条规则的「触发 / 不触发」样例 |
| `requirements.txt` / `.env.example` | 依赖与配置样例 |
| `PROMPT.md` | 在 Qoder 里用的提示词、生成物与增强点对照表、Qoder Sites 发布步骤 |
| `screenshots/` | Qoder 对话截图 + 发布链接截图（见 `PROMPT.md` §5） |

在线演示（发布后填这里）：

```text
Qoder Sites 链接：https://________________.qoder.site
```

---

## 2. 本地运行

```bash
cd Qoder
pip install -r requirements.txt

# 二选一：填 API Key（魔搭 / StepFun / MiniMax 都行），或留空只跑离线规则
export MODELSCOPE_API_KEY=xxxxxxxx     # 或 STEPFUN_API_KEY / MINIMAX_API_KEY

streamlit run app.py
```

浏览器打开 <http://localhost:8501>。

### 跑测试

```bash
cd Qoder
python tests/test_rules.py -v      # 22 passed in 0.003s
```

---

## 3. 功能一览

1. **离线规则引擎**（默认开启，毫秒级）
   15 条规则分三级：`🔴 阻断`（UPDATE/DELETE 无 WHERE、JOIN 无 ON、建表无主键）、
   `🟠 警告`（SELECT \*、LIKE '%x'、索引列被函数包裹、深分页、NOT IN 与 NULL、IN 过长、FOR UPDATE 无 WHERE）、
   `🔵 提示`（UNION 去重、TRUNCATE、缺 EXPLAIN、隐式类型转换、COUNT(1)）。
2. **大模型深度审查**（可切换）
   走 OpenAI 兼容协议，预置魔搭 / StepFun / MiniMax / OpenAI 四套 endpoint，
   模型返回 JSON 后自动解析成同样格式的三级结果。
3. **报告导出**：Markdown 评审报告 + JSON（可接 CI 卡口）。
4. **示例 SQL**：慢查询深分页、全表更新、缺主键建表、NOT IN 空集陷阱、seekdb 向量建表。
5. **附加上下文**：可补充表结构、数据量、慢查询耗时，提升模型判断准确度。

---

## 4. 架构

```text
app.py  ──输入 SQL──► reviewer.analyze()      # 确定性规则（标准库 re）
        │                     └─► Finding[]    # id / level / message / suggestion / snippet
        ├──(可选)──► reviewer.LLMReviewer      # OpenAI 兼容 HTTP（urllib）
        │                     └─► LLMResult    # content + 解析出的 Finding[]
        └────────────────► 合并排序 → 三级展示 → Markdown / JSON 导出
```

`LLMReviewer` 只用 `urllib` 发请求，所以**不需要安装 openai SDK**，
换 provider 只是改 Base URL 和模型名。

---

## 5. 与题目要求的对应关系

| 题目要求 | 本项目 |
| --- | --- |
| 用 Python 写 Streamlit 应用 | ✅ `app.py`，`streamlit run app.py` |
| 调用大模型 API | ✅ OpenAI 兼容 `chat/completions`，四家 provider 预置 |
| 主题是「数据库代码审查助手」 | ✅ 15 条规则 + LLM 语义审查，输出三级评审报告 |
| 在 Qoder 云端环境跑起来 | 见 `PROMPT.md` §4 的 Qoder Sites 发布步骤 |
| 截图证明是 Qoder 生成 | `screenshots/01-qoder-chat.png`（含提示词与生成 diff） |

---

## 6. 已知边界

- 静态规则基于正则，只覆盖通用反模式，**不替代** `EXPLAIN` 与压测；
  规则 OB-013 会主动提醒补执行计划。
- LLM 审查结果依赖所选模型能力；模型不可用时应用不会崩，只跳过 LLM 层。
- 未接入真实数据库连接，因此不做「实际执行计划分析」；如果评测需要，
  可在 `reviewer.py` 增加 `EXPLAIN` 采集层。
