"""魔搭社区（ModelScope）AI 问答助手 · Streamlit 应用。

复用 StepFun 赛题的 Python 结构（Streamlit + OpenAI 兼容客户端），
把 Base URL 与模型名换成魔搭的免费推理服务：

    Base URL : https://api-inference.modelscope.cn/v1
    模型     : Qwen/Qwen3.5-27B（也可用 stepfun-ai/Step-3.5-Flash、MiniMax/MiniMax-M3 等）

运行：

    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st

from modelscope_client import (
    CURATED_MODELS,
    DEFAULT_MODEL,
    ModelScopeClient,
    ModelScopeError,
    pick_model,
)

st.set_page_config(page_title="魔搭 AI 问答助手", page_icon="🎈", layout="centered")

SYSTEM_PROMPT = (
    "你是第六届 OceanBase 数据库大赛的参赛助理，"
    "擅长 OceanBase / seekdb 向量数据库、SQL 调优与大模型应用开发。"
    "回答要具体、可执行；涉及 SQL 时给出可直接复制的语句。"
)

SAMPLES = [
    "用一段话解释 OceanBase 的 HNSW 向量索引是怎么工作的？",
    "写一条 seekdb 的混合检索 SQL，要求向量 + 全文用 RRF 融合。",
    "我有一个 2000 万行的订单表，最近深分页很慢，给我三种优化方案。",
    "帮我写一个 Python 脚本，把 Markdown 文档切块后批量写入向量库。",
]


@st.cache_data(ttl=600, show_spinner=False)
def cached_models(base_url: str) -> list[str]:
    try:
        client = ModelScopeClient("", base_url=base_url)
        models = client.list_models()
        return models or list(CURATED_MODELS)
    except ModelScopeError:
        return list(CURATED_MODELS)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("🔑 配置区")
    api_key = st.text_input(
        "魔搭 API Key（访问令牌）",
        value=os.environ.get("MODELSCOPE_API_KEY", ""),
        type="password",
        help="魔搭官网 -> 头像 -> 访问令牌 -> 新建令牌",
    )
    base_url = st.text_input(
        "Base URL",
        value=os.environ.get("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
    )

    available = cached_models(base_url)
    default_model = os.environ.get("MODELSCOPE_MODEL", DEFAULT_MODEL)
    options = [default_model] + [m for m in available if m != default_model]
    model = st.selectbox("模型", options, index=0)
    temperature = st.slider("temperature", 0.0, 1.0, 0.7, 0.1)
    max_tokens = st.slider("max_tokens", 256, 4096, 1024, 256)

    st.divider()
    st.caption(f"可用模型 {len(available)} 个（含 MiniMax-M3 / Step-3.5-Flash / GLM 等）")
    if st.button("🔄 刷新模型列表"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.rerun()

# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #
st.title("🎈 魔搭 AI 问答助手")
st.caption("ModelScope 免费推理 API · OpenAI 兼容协议 · 零成本跑通的大模型 Demo")

for message in st.session_state.get("messages", []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("meta"):
            st.caption(message["meta"])

if prompt := st.chat_input("问我点什么，例如：怎么给 OceanBase 建 HNSW 向量索引？"):
    st.session_state.setdefault("messages", []).append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key.strip():
            st.warning("请在左侧边栏填入魔搭 API Key（访问令牌）后提问。")
        else:
            client = ModelScopeClient(api_key.strip(), base_url=base_url, model=model)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
                {"role": item["role"], "content": item["content"]}
                for item in st.session_state["messages"]
            ]
            try:
                with st.spinner(f"{model} 思考中…"):
                    result = client.chat(
                        messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
            except ModelScopeError as error:
                st.error(str(error))
            else:
                st.markdown(result.content)
                usage = result.usage or {}
                meta = f"{result.model} · {result.elapsed_ms} ms"
                if usage:
                    meta += " · " + " / ".join(f"{key}={value}" for key, value in usage.items())
                st.caption(meta)
                st.session_state["messages"].append(
                    {"role": "assistant", "content": result.content, "meta": meta}
                )

with st.expander("💡 示例问题", expanded=False):
    for sample in SAMPLES:
        st.markdown(f"- {sample}")

st.divider()
st.caption("接口：POST https://api-inference.modelscope.cn/v1/chat/completions（OpenAI 兼容）")
