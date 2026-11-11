import streamlit as st
from openai import OpenAI

# 设置网页标题
st.title("🎈 我的第一个 AI 网页小工具")
st.write("这是一个基于 Streamlit 搭建的问答助手，用于快速交付演示。")

# 在侧边栏让用户输入 API Key
with st.sidebar:
    st.header("🔑 配置区")
    api_key = st.text_input("请输入你的 API Key", type="password")
    st.caption("如果没有Key，可以直接随便输入几个字母体验一下页面功能。")

# 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 展示历史聊天记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 聊天输入框
if prompt := st.chat_input("你好，有什么我可以帮你的吗？"):
    # 把用户输入加入聊天记录
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 生成 AI 回复
    with st.chat_message("assistant"):
        if not api_key:
            st.warning("请在左侧边栏输入 API Key！(演示用，随便填几个字母也行)")
        else:
            # 这里为了演示，如果没有真实API，我们返回一个固定的占位回复
            # 如果你有真实的 MiniMax 或通义千问 API，可以在这里替换成真实的调用代码
            response = f"我已经收到你的消息：'{prompt}'。由于这是演示工具，AI 逻辑已占位。"
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})