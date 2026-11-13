# MiniMax × seekdb · SQL 处方助手

> 赛题目录（官方脚手架 `minimax/`）：MiniMax 负责「表达」，seekdb 负责「事实」。

## 组件分工

| 组件 | 作用 | 在项目流程中的实际体现 |
| --- | --- | --- |
| **MiniMax**（OpenAI 兼容） | 理解病历并按「诊断 / 处方 / 复查」三段式输出 | 每次提问都会真实调用 `POST {base_url}/chat/completions` |
| **seekdb**（知识服务，见 `../dify/seekdb_service/`） | 本地 bge-small-zh 向量 + IK 全文 + RRF 混合检索，给出事实依据 | 回答前先 `/search`，检索到的原文会作为「seekdb 医书」注入提示词，并在界面上可展开核对 |

**只装组件、只测连接不满足要求**——这里每次提问都会真实走一遍「seekdb 检索 → 模型作答」。

## 运行

```bash
pip install -r requirements.txt

# 1) 起 seekdb 知识服务（真 seekdb 内核 + 本地 bge 向量）
python ../dify/seekdb_service/serve.py --port 8848

# 2) 起应用
export MINIMAX_API_KEY=xxxxxxxx        # MiniMax 官方 Key
# 或用魔搭上的 MiniMax/MiniMax-M3（免费额度）：
# export MODELSCOPE_API_KEY=ms-xxxx
streamlit run app.py
```

打开 <http://localhost:8501>，左侧选推理服务并填 Key，右侧贴 SQL → 点「🩺 开处方」。

## 验证样例

1. 输入：

   ```sql
   SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id
   WHERE DATE(o.created_at) = '2026-01-01' ORDER BY o.created_at DESC LIMIT 20, 200000;
   ```

2. 预期：`seekdb 检索到的原文` 展开后应包含《seekdb / OceanBase 向量库速查》或
   《混合检索（向量 + 全文）与 RRF 融合》中的条目；模型回答包含「诊断 / 处方 / 复查」三段，
   处方里给出去掉 `DATE()` 函数、改游标分页等可执行改写。

3. 核对 seekdb 确实起作用：点开「seekdb 检索到的原文」expander，里面是 `dify_knowledge_base`
   表（VECTOR(512) + IK 全文 + HNSW 索引）里真实检索出的段落，不是内置字符串。

## 依赖

`requirements.txt`：仅 `streamlit`（HTTP 调用用标准库，无需 openai SDK）。
seekdb 服务依赖见 `../dify/seekdb_service/requirements.txt`。
