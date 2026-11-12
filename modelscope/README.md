# 魔搭社区（ModelScope）赛题交付物

> 题目要求：复用 StepFun 的 Python 代码，把 **API URL 和 Model 名字换成魔搭的**，跑通并录屏。
> 本目录已完成：Base URL 换成 `https://api-inference.modelscope.cn/v1`（OpenAI 兼容），
> 模型换成魔搭免费推理模型，**代码真实调用魔搭接口**（不再是占位回复）。

---

## 1. 交付物清单

| 文件 | 说明 |
| --- | --- |
| `app.py` | Streamlit 聊天应用（侧边栏填 Key / 选模型 / 调温，多轮对话） |
| `modelscope_client.py` | 魔搭客户端：模型列表 + 聊天补全 + 错误分级（401/403/404/429/5xx） |
| `scripts/smoke_test.py` | 连通性自检脚本（不依赖 Streamlit） |
| `requirements.txt` / `.env.example` | 依赖与配置样例 |
| `第三题.mp4` | 运行成功录屏（30~120 秒） |
| `screenshots/` | 魔搭控制台 / 运行界面截图 |

在线体验（公网 Demo，已实测 HTTP 200）：

```text
https://entrance-hansen-button-professional.trycloudflare.com
```

> 该地址由本机的 cloudflared 隧道暴露（隧道地址会变）。**永久**链接请按 §6 部署到魔搭创空间，
> 拿到 `*.modelscope.cn` 后回填到本文件与根 README 的「作品链接」表。
> 第一次打开时，请在左侧边栏粘贴魔搭访问令牌（`ms-...`），否则聊天会提示缺少 Key。
> （也可以先设置环境变量 `MODELSCOPE_API_KEY` 再启动。）

## ⭐ 本赛题的正式提交物：已上传的 Skill

| 项 | 值 |
|---|---|
| **Skill 网址** | `https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer` |
| 英文名称 | `oceanbase-sql-reviewer` |
| 展示名称 | OceanBase SQL 审查专家 |
| 可见范围 | 公开（实测未登录 HTTP 200） |
| License | Apache-2.0 |
| 源码 | `modelscope/SKILL.md` + `scripts/review_rules.py` + `references/rules.md` |
| 打包 | `modelscope/oceanbase-sql-reviewer-skill.zip` |

上传步骤与表单填写见 [`SKILL_UPLOAD.md`](SKILL_UPLOAD.md)。

---

## 2. API Key 获取（3 分钟）

1. 打开 <https://modelscope.cn>，用**阿里云账号**登录（或直接注册）。
2. 右上角头像 → **访问令牌** → 「新建访问令牌」→ 复制生成的 `ms-...` 字符串。
3. 贴到应用的左侧边栏，或写进环境变量 `MODELSCOPE_API_KEY`。

免费推理额度：魔搭「模型服务 / API 推理」对注册用户提供免费调用额度，
足够跑完整个 Demo 与答辩演示。

---

## 3. 本地运行

```bash
cd 魔搭
pip install -r requirements.txt

# Windows PowerShell
$env:MODELSCOPE_API_KEY="ms-xxxxxxxx"

# macOS / Linux
export MODELSCOPE_API_KEY=ms-xxxxxxxx

streamlit run app.py
```

浏览器打开 <http://localhost:8501>，左侧粘贴 Key、右侧输入问题即可对话。

### 连通性自检（答辩前先跑一遍）

```bash
cd 魔搭
python scripts/smoke_test.py
# [1/3] GET https://api-inference.modelscope.cn/v1/models   -> OK: 38 个模型可用
# [2/3] 选定模型: Qwen/Qwen3.5-27B
# [3/3] POST .../v1/chat/completions                      -> OK: xxx ms  usage={...}
```

指定别的模型：

```bash
python scripts/smoke_test.py --model stepfun-ai/Step-3.5-Flash
python scripts/smoke_test.py --model MiniMax/MiniMax-M3
```

---

## 4. 从 StepFun 迁移到魔搭的改动点

| 项 | StepFun 版 | 魔搭版 |
| --- | --- | --- |
| Base URL | `https://api.stepfun.com/v1` | `https://api-inference.modelscope.cn/v1` |
| 模型 | `step-2-16k` 等 | `Qwen/Qwen3.5-27B`（也支持 `stepfun-ai/Step-3.5-Flash`、`MiniMax/MiniMax-M3`） |
| 鉴权 | Bearer | 同样是 Bearer，**协议完全一致** |
| 客户端 | openai SDK | 标准库 `urllib`（零依赖，且把 401/429 等错误翻译成中文提示） |
| 模型选择 | 写死 | 运行时拉取 `/v1/models` 动态下拉，可一键切 MiniMax / StepFun / GLM / DeepSeek |

> 这也顺带证明了「同一套 OpenAI 兼容代码可以无缝切换 4 家推理服务」，
> 与 `Qoder/` 目录里的 provider 预置是同一套设计。

---

## 5. 魔搭可用的免费推理模型（2026-11 实测 `/v1/models`，共 38 个）

节选（含本大赛其它赛题用到的模型）：

```text
Qwen/Qwen3.5-27B
Qwen/Qwen3.8-Flash-Next
deepseek-ai/DeepSeek-V4.1-Flash
stepfun-ai/Step-3.5-Flash
stepfun-ai/Step-3.7-Flash
MiniMax/MiniMax-M3
MiniMax/MiniMax-M1-80k
ZhipuAI/GLM-4.7-Flash
XGenerationLab/XiYanSQL-QwenCoder-32B-2504   # SQL 专用
Shanghai_AI_Laboratory/Intern-S2-Preview
```

---

## 6. 部署到魔搭创空间（拿公网链接）

1. 魔搭官网 → 「创空间」→ 创建创空间 → 选择 **Streamlit** 模板。
2. 把本目录的 `app.py`、`modelscope_client.py`、`requirements.txt` 上传进去。
3. 在「环境变量」里加 `MODELSCOPE_API_KEY`（不要把 Key 写进代码）。
4. 启动命令保持 `streamlit run app.py`，点「启动」，得到
   `https://<你的用户名>/<创空间名>` 形式的公网地址。
5. 创空间本身也支持直接访问 `/api/v1/chat` 等能力，必要时可加一层 API 包装。

---

## 7. 录屏脚本（30~60 秒，建议按这个顺序）

| 时间 | 画面 | 旁白 |
| --- | --- | --- |
| 0:00-0:08 | 终端跑 `python scripts/smoke_test.py` | 「先跑连通性自检，38 个模型可用」 |
| 0:08-0:16 | 展示输出里的模型列表与 usage | 「接口完全兼容 OpenAI 协议」 |
| 0:16-0:30 | 浏览器打开 Streamlit，输入「HNSW 向量索引怎么建？」 | 「侧边栏填魔搭访问令牌」 |
| 0:30-0:50 | 展示模型真实回答 + 底部 `model / 耗时 / usage` | 「这是魔搭模型的真实回复，不是占位」 |
| 0:50-1:00 | 切换模型为 `stepfun-ai/Step-3.5-Flash` 再问一次 | 「同一套代码切换推理服务」 |

录屏文件命名：`第三题.mp4`（已提交）。

---

## 8. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| HTTP 401 | Key 填错或过期 | 重新在「访问令牌」页创建 |
| HTTP 429 | 免费额度用尽 / 限流 | 换模型（Flash 系列）或稍后再试 |
| HTTP 404 | 模型名已下线 | 从 `/v1/models` 实时列表里选 |
| 模型列表拉取失败 | 网络受限 | 客户端会自动回退到内置 `CURATED_MODELS` 列表 |
| 回答很慢 | 选了超大模型 | 换 `Qwen/Qwen3.8-Flash-Next` 或 `DeepSeek-V4.1-Flash` |
