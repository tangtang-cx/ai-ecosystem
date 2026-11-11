import streamlit as st

# 页面基础配置
st.set_page_config(page_title="AI 文本润色小工具", page_icon="✨")

st.title("✨ AI 文本润色与翻译小工具")
st.write("这是一个为了快速交付而使用 AI 辅助生成的网页小工具。")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 工具设置")
    mode = st.selectbox(
        "请选择功能模式",
        ("日常润色 (使其更通顺)", "职场润色 (使其更专业)", "中译英翻译")
    )
    st.info("💡 提示：本演示工具使用本地规则模拟 AI 处理效果，无需消耗 API 额度。")

# 主界面布局
st.subheader("📝 请输入原始文本：")
input_text = st.text_area("在这里粘贴或输入你需要处理的文字...", height=150)

# 按钮与处理逻辑
if st.button("🚀 开始处理", type="primary"):
    if not input_text.strip():
        st.warning("请输入内容后再点击处理哦！")
    else:
        st.subheader("🎯 处理结果：")
        
        # 模拟 AI 处理逻辑 (基于简单规则)
        with st.spinner("AI 正在努力处理中..."):
            if mode == "日常润色 (使其更通顺)":
                result = f"【润色后】：{input_text.strip()}。（注：此处为演示效果，实际应用中此处接入大模型 API，让表达更加自然流畅。）"
            elif mode == "职场润色 (使其更专业)":
                result = f"【职场版】：关于该项事宜，{input_text.strip()}。我们将持续跟进并确保落实。（注：此处为演示效果，实际应用会转换为正式商务口吻。）"
            else:
                result = f"【Translation】：Here is the translated text for: '{input_text.strip()}'. (This is a demo result.)"
            
            # 展示结果
            st.success("处理完成！")
            st.info(result)