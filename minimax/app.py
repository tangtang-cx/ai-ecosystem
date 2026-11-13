"""MiniMax × seekdb · SQL 处方助手

用 MiniMax（OpenAI 兼容）给 SQL「开处方」，处方依据来自一台真实的 seekdb 向量库
（本地 bge-small-zh 向量 + IK 全文 + RRF 混合检索，服务见 ``dify/seekdb_service``）。

运行：

    pip install -r requirements.txt
    export MINIMAX_API_KEY=xxxxxxxx      # 或用魔搭上的 MiniMax/MiniMax-M3
    python ../dify/seekdb_service/serve.py --port 8848   # 起 seekdb 知识服务
    streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st

from minimax_client import PROVIDER_PRESETS, LLMError, MiniMaxClient, search_knowledge

st.set_page_config(page_title="MiniMax × seekdb · SQL 处方助手", page_icon="💊")

SYSTEM = (
    "你是资深数据库工程师，专为 SQL 开「处方」。回答分三段："
    "【诊断】问题出在哪；【处方】给出可直接执行的优化后 SQL；【复查】如何验证效果。"
    "只使用检索到的 seekdb 医书原文作为事实依据，覆盖不到就直说，不要编造 API。"
)

with st.sidebar:
    st.header("⚙️ 模型")
    provider = st.selectbox(
        "推理服务",
        list(PROVIDER_PRESETS),
        format_func=lambda key: {"minimax": "MiniMax", "modelscope": "魔搭（MiniMax-M3）", "stepfun": "StepFun"}[key],
    )
    preset = PROVIDER_PRESETS[provider]
    api_key = st.text_input("API Key", value=os.environ.get(preset["env_key"], ""), type="password")
    model = st.text_input("模型", value=os.environ.get(f"{provider.upper()}_MODEL", preset["model"]))
    kb_url = st.text_input("seekdb 知识服务", value=os.environ.get("SEEKDB_SERVICE_URL", "http://127.0.0.1:8848"))
    use_kb = st.checkbox("先查 seekdb 再回答", value=True)

st.title("💊 MiniMax × seekdb · SQL 处方助手")
st.caption("MiniMax 出方，seekdb 翻医书 —— 两个组件各司其职：模型负责表达，seekdb 负责事实。")

sql = st.text_area("贴一段 SQL 或一条报错", height=200, placeholder="SELECT * FROM orders WHERE DATE(created_at) = '2026-01-01';")

if st.button("🩺 开处方", type="primary"):
    if not sql.strip():
        st.warning("先贴点病历进来。")
    elif not api_key.strip():
        st.info("左侧填 API Key（MINIMAX_API_KEY）。")
    else:
        context = ""
        if use_kb:
            with st.spinner("正在 seekdb 里翻医书…"):
                try:
                    context = search_knowledge(sql[:500], kb_url)
                except Exception as error:
                    st.warning(f"seekdb 检索失败（{error}），将只靠模型回答。")
        client = MiniMaxClient(api_key.strip(), model=model, provider=provider)
        with st.spinner(f"{model} 正在开方…"):
            try:
                result = client.chat(
                    [{"role": "user", "content": f"【seekdb 医书】\n{context}\n\n【病历】\n{sql}"}],
                    system=SYSTEM,
                )
            except LLMError as error:
                st.error(str(error))
            else:
                st.markdown(result.content)
                st.caption(f"{result.model} · {result.elapsed_ms} ms · {result.usage}")
                if context:
                    with st.expander("seekdb 检索到的原文"):
                        st.text(context)
