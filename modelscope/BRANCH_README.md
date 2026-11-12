# 魔搭社区（ModelScope）赛题提交分支

题目：**魔搭社区 · AI 问答助手（复用 StepFun 代码，换成魔搭推理 API）**

提测时填写：

| 项 | 值 |
| --- | --- |
| 仓库 | `https://github.com/tangtang-cx/ai-ecosystem` |
| 分支 | `modelscope` |
| Commit SHA | 取该分支最新 commit 的完整 40 位 SHA（见 <https://github.com/tangtang-cx/ai-ecosystem/commits/modelscope>） |

## 提交物

```text
魔搭/
  app.py                  # Streamlit 聊天应用（真实调用魔搭接口，零占位）
  modelscope_client.py    # 魔搭客户端：模型列表 + 聊天补全 + 401/403/404/429 中文报错
  scripts/smoke_test.py   # 连通性自检脚本（不依赖 Streamlit）
  tests/test_client.py    # 9 个单元测试（含真实连通性用例）
  第三题.mp4               # 运行成功录屏
  README.md               # 完整交付说明（取 Key / 运行 / 部署创空间 / 录屏脚本）
  requirements.txt / .env.example
```

## 评测怎么跑（评委侧，2 分钟）

```bash
pip install -r requirements.txt
export MODELSCOPE_API_KEY=ms-xxxxxxxx    # 魔搭 -> 头像 -> 访问令牌 -> 新建令牌
python scripts/smoke_test.py             # 先自检：38 个模型可用 + 真实对话
streamlit run app.py                     # 再看界面
```

打开 <http://localhost:8501>，左侧填 API Key，右侧直接提问，回复是**魔搭模型的真实输出**
（界面底部显示 model / 耗时 / usage 三个指标）。

## 关键点

- 接口：`POST https://api-inference.modelscope.cn/v1/chat/completions`（OpenAI 兼容）
- 默认模型：`Qwen/Qwen3.5-27B`，下拉里可切 38 个免费模型
  （含 `stepfun-ai/Step-3.5-Flash`、`MiniMax/MiniMax-M3`、`ZhipuAI/GLM-4.7-Flash`）
- 相对 StepFun 版本只改了 **Base URL + 模型名**，其余代码结构完全复用

详细文档见 [`魔搭/README.md`](魔搭/README.md)。
