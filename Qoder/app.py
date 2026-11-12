"""数据库代码审查助手 · Qoder 生成并增强的 Streamlit 应用。

由 Qoder（AI IDE）根据如下提示词生成，本仓库在其基础上补齐了规则引擎与多模型接入：

    请帮我用 Python 写一个 Streamlit 应用，调用大模型 API 做一个「数据库代码审查助手」。

运行：

    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import json
import os

import streamlit as st

from reviewer import (
    LEVELS,
    LEVEL_LABEL,
    PROVIDER_PRESETS,
    Finding,
    LLMReviewer,
    analyze,
    summarize,
)

st.set_page_config(
    page_title="数据库代码审查助手",
    page_icon="🧐",
    layout="wide",
)

SAMPLES: dict[str, str] = {
    "慢查询 / 深分页": """SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id
WHERE DATE(o.created_at) = '2026-01-01'
  AND o.status IN ('NEW', 'PAID', 'SHIPPED', 'DONE')
  AND c.city LIKE '%杭州%'
ORDER BY o.created_at DESC
LIMIT 20, 200000;""",
    "全表更新": """UPDATE orders SET status = 'ARCHIVED';""",
    "缺失主键": """CREATE TABLE order_items (
  id BIGINT NOT NULL,
  order_id BIGINT NOT NULL,
  price DECIMAL(10, 2)
);""",
    "NOT IN 空集陷阱": """SELECT id FROM orders
WHERE customer_id NOT IN (SELECT id FROM blacklist_customer);""",
    "OceanBase 向量检索": """CREATE TABLE doc_chunk (
  id VARBINARY(512) PRIMARY KEY NOT NULL,
  document STRING,
  embedding VECTOR(512),
  FULLTEXT INDEX idx_fts (document) WITH PARSER ik PARSER_PROPERTIES=(ik_mode='smart'),
  VECTOR INDEX idx_vec (embedding) WITH(distance=cosine, type=hnsw, lib=vsag,
       m=16, ef_construction=200, ef_search=64)
) ORGANIZATION = HEAP;""",
}

LEVEL_COLORS = {"error": "🔴", "warn": "🟠", "info": "🔵"}


def render_finding(finding: Finding) -> None:
    icon = LEVEL_COLORS.get(finding.level, "⚪")
    label = LEVEL_LABEL.get(finding.level, finding.level)
    st.markdown(
        f"##### {icon} `{finding.id}` {finding.title} <span style='font-size:0.8em;color:#888'>"
        f"· {label} · {finding.source}</span>",
        unsafe_allow_html=True,
    )
    if finding.snippet:
        st.code(finding.snippet, language="sql")
    st.markdown(f"**问题**：{finding.message}")
    st.markdown(f"**建议**：{finding.suggestion}")
    st.divider()


def export_markdown(findings: list[Finding], sql: str, llm_text: str) -> str:
    lines = ["# 数据库代码审查报告", "", "## 待审查 SQL", "", "```sql", sql, "```", ""]
    counts = summarize(findings)
    lines.append(
        "## 统计：" + " / ".join(f"{LEVEL_LABEL[level]} {counts.get(level, 0)}" for level in LEVELS)
    )
    lines.append("")
    for finding in findings:
        lines.append(f"### [{finding.id}] {LEVEL_LABEL.get(finding.level, finding.level)} {finding.title}")
        lines.append(f"- 问题：{finding.message}")
        lines.append(f"- 建议：{finding.suggestion}")
        if finding.snippet:
            lines.append(f"- 命中片段：`{finding.snippet}`")
        lines.append("")
    if llm_text:
        lines += ["## 大模型深度审查", "", llm_text]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("⚙️ 模型配置")
    provider = st.selectbox(
        "推理服务",
        list(PROVIDER_PRESETS),
        index=0,
        format_func=lambda key: {
            "modelscope": "魔搭 ModelScope",
            "stepfun": "阶跃星辰 StepFun",
            "minimax": "MiniMax",
            "openai": "OpenAI 兼容（自定义）",
        }[key],
    )
    preset = PROVIDER_PRESETS[provider]
    base_url = st.text_input("Base URL", value=os.environ.get(f"{provider.upper()}_BASE_URL", preset["base_url"]))
    model = st.text_input("模型名", value=os.environ.get(f"{provider.upper()}_MODEL", preset["model"]))
    api_key = st.text_input(
        "API Key",
        value=os.environ.get(preset["env_key"], ""),
        type="password",
        help=f"环境变量 {preset['env_key']} 优先；留空则只跑本地规则引擎。",
    )
    use_llm = st.checkbox("同时调用大模型做深度审查", value=bool(api_key))
    st.caption(f"协议：OpenAI 兼容 `{base_url}/chat/completions`")

    st.header("📋 规则集")
    st.caption("本地静态规则（无需 API）：15 条 OceanBase / MySQL 通用规则，详见 rules/sql_review_rules.md")

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("🧐 数据库代码审查助手")
st.markdown(
    "输入 SQL 或 DDL，助手先跑**确定性静态规则**（毫秒级、离线可用），"
    "再可选调用大模型做**语义级深度审查**，最后导出 Markdown 评审报告。"
)
st.caption("生成方式：本项目由 Qoder AI IDE 生成并在本仓库增强；支持 OceanBase / seekdb / MySQL 语法。")

left, right = st.columns([3, 2])
with left:
    st.subheader("① 待审查的 SQL")
    sample_name = st.selectbox("示例", list(SAMPLES) + ["（自己粘贴）"])
    default_sql = SAMPLES.get(sample_name, "")
    sql = st.text_area(
        "SQL / DDL",
        value=default_sql,
        height=280,
        placeholder="SELECT ... FROM ...",
    )
with right:
    st.subheader("② 审查选项")
    dialect = st.selectbox("目标数据库", ["OceanBase 4.x (MySQL 模式)", "seekdb", "MySQL 8.0"])
    include_ddl = st.checkbox("同时检查 DDL（建表 / 索引）", value=True)
    extra_context = st.text_area("附加上下文（可选）", height=90, placeholder="表结构、数据量、慢查询耗时…")

run = st.button("🚀 开始审查", type="primary", use_container_width=True)

if run:
    if not sql.strip():
        st.warning("请先输入要审查的 SQL。")
        st.stop()

    st.session_state["last_sql"] = sql
    with st.spinner("正在执行静态规则…"):
        findings = analyze(sql)
        if not include_ddl:
            findings = [item for item in findings if "create table" not in item.message.lower()]

    llm_result_text = ""
    llm_findings: list[Finding] = []
    if use_llm:
        if not api_key.strip():
            st.info("未填 API Key，跳过大模型深度审查（规则结果仍然有效）。")
        else:
            with st.spinner(f"正在调用 {model} 做深度审查…"):
                reviewer = LLMReviewer(base_url=base_url, model=model, api_key=api_key.strip())
                result = reviewer.review(sql, extra_context)
            if result.ok:
                llm_result_text = result.content
                llm_findings = result.findings
            else:
                st.error(f"大模型调用失败：{result.error}")

    merged = findings + llm_findings
    counts = summarize(merged)

    st.subheader("③ 审查结果")
    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 阻断", counts.get("error", 0))
    c2.metric("🟠 警告", counts.get("warn", 0))
    c3.metric("🔵 提示", counts.get("info", 0))

    if not merged:
        st.success("✅ 没有发现明显问题。")
    for finding in merged:
        render_finding(finding)

    if llm_result_text:
        with st.expander("大模型原始输出", expanded=False):
            st.markdown(llm_result_text)

    report = export_markdown(merged, sql, llm_result_text)
    st.download_button(
        "⬇️ 导出 Markdown 评审报告",
        data=report,
        file_name="sql-review-report.md",
        mime="text/markdown",
    )
    st.download_button(
        "⬇️ 导出 JSON（可接入 CI）",
        data=json.dumps([item.to_dict() for item in merged], ensure_ascii=False, indent=2),
        file_name="sql-review-report.json",
        mime="application/json",
    )

    st.caption(f"目标数据库：{dialect}")
