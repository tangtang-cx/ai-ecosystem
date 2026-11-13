#!/usr/bin/env python3
"""Rewrite SUBMISSION_CHECKLIST.md with the platform's real submission rules."""

from __future__ import annotations

from pathlib import Path

NEW = """# 提测清单（按平台真实规则）

> 平台 API（prod 主机 `https://openwebapi.oceanbase.com`）：
> `GET /api/testplatform/taskrecord/submissionOptions?questionId=<id>` 拿这题要填哪些字段，
> `POST /api/testplatform/taskrecord/commitTestPlatformTaskRecord` 提交。

---

## 0. 仓库地址怎么填（**最容易错的一条**）

平台前端的校验函数是：

```js
function isValidSubmissionLink(M) {
  if (typeof M !== "string" || M.trim().length > 2048) return false;
  var C = new URL(M.trim());
  return C.protocol === "https:" && Boolean(C.hostname) && !C.username && !C.password;
}
```

也就是说 **「代码仓库地址」栏必须填不带用户名/密码的纯 https 地址**：

```text
https://github.com/tangtang-cx/ai-ecosystem
```

**不要**写成 `https://wzhaihqy:<PAT>@github.com/...`（带凭据会被判不合法）。
私有库的访问由平台自己的凭据 / 官方测试账号 `oceanbase-ce-game-test` 协作者授权解决，
不需要（也不允许）把 token 写进仓库地址。

提交体由平台前端自己组装：

```js
{ gitRepo,                      // 纯 https 地址
  commitId, branch,             // 非「提交物型」题目必填
  extraParams: { <额外字段>: 值 } }
```

---

## 1. 六个赛题的提交坐标

仓库地址统一为：

```text
https://github.com/tangtang-cx/ai-ecosystem
```

| 赛题 | Branch | Commit id | 额外字段（extraParams） |
| --- | --- | --- | --- |
| **Dify**（600076） | `2026-competition-ecosystem` | `5fde725088adbb3f9f9134411fb2cd24865fb8ef` | 项目网站网址（cloud.dify.ai 分享链接） |
| **Qoder**（600077） | `2026-competition-ecosystem` | `5fde725088adbb3f9f9134411fb2cd24865fb8ef` | Qoder Sites 网址 + Qoder 账号 UID |
| **魔搭社区** | — | — | **Skill 网址或编号**（`https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer`）；这题是「提交物型」，只填网址 |
| 高德 | `gaode` | `1ff93437c1a3f996b7e18998d3da48ea103b6ec9` | `gaode/SKILL.md` |
| StepFun | `stepfun` | `0c11f29bb9180671ce02d7b9cb070ffd12db6213` | Web 应用 + 技术说明 |
| 加赛（PowerContext） | `2026-competition-powercontext` | `c06bca1b9a134231689d5616f7f0f5392cd005a4` | — |

> 合并分支 `2026-competition-ecosystem` 同时包含六个赛题目录
> （`dify/ qoder/ gaode/ stepfun/ minimax/ modelscope/`），
> 它的父提交就是官方基线 `oceanbase/powercontext@2026-competition-ecosystem`（`d647275c`），
> 满足「基于该分支开发、资产放入对应目录」的要求。

### 提交前 30 秒自查

```bash
export GITHUB_TOKEN=<你的 GitHub PAT>
node tools/check_submission.mjs 2026-competition-ecosystem <40位commit> dify
# 期望：4 个 ok + RESULT: submittable
```

它验证：仓库可读 → **分支存在（大小写敏感）** → **commit 确实是该分支的 head 或祖先**
→ 资产目录非空。

---

## 2. failMsg 对照表（平台自带枚举）

| failMsg | 含义 | 常见原因 |
| --- | --- | --- |
| 1 | branch 不存在 | **分支名大小写写错**（Qoder 题就踩过：`Qoder` vs `qoder`） |
| 2 | commit_id 不存在 | SHA 写错，或不是该分支上的 commit |
| 3 | 编译失败 | — |
| 4 | git clone 失败 | 仓库地址带了凭据 / token 无权限 / 仓库不可读 |
| 5 | git clone 超时 | 网络或仓库过大 |
| 6 | git reset 失败 | — |
| 7 | cmake 失败 | — |
| 8 | 验证失败 | 跑起来后的用例不通过 |
| 100 | 其他异常 | 平台侧（可发帖请官方查后台日志） |

---

## 3. 各赛题「主要功能运行失败」的三个已知坑与对策

| 坑 | 对策（已在仓库里实现） |
| --- | --- |
| **DSL 边被丢弃** → 节点不连通 → 回答为空 | `dify/app.yml` 等四个 DSL 的 `edges` 已改成官方导出形状（`type: custom` + `data.sourceType/targetType`）；`validate_dsl.py` 现在会判不通过 |
| **LLM 节点没有模型** → 节点无效 | `dify/app.yml` 留空（用工作区默认模型）；`dify/app-with-model.yml` 写死 `tongyi/qwen-plus`；README 与 DSL 描述里都写明「导入后必做一步：选模型」 |
| **评测机干净环境 / 重启后数据丢失** | `dify/DEPLOY.md`（持久化表、依赖顺序、零插件依赖、重启恢复自检）+ `dify/deploy/docker-compose.yml`（volume + healthcheck + depends_on）+ `dify/deploy/quickstart.sh`（一键拉起 + 端到端验证） |
| **Qoder 的 seekdb 只是"装了个连接"** | `qoder/app.py` 启动时**自动拉起** seekdb 知识服务，检索与历史落库都在核心链路上；`qoder/smoke_test.py` 自证 |

---

## 4. 还需要人提供的东西

| # | 需要 | 为什么我给不了 |
| --- | --- | --- |
| 1 | 提测平台的登录态（cookie，或账号+验证码） | 提测接口需要登录 session |
| 2 | 各赛题的 questionId | 提测记录里有（Dify=600076、Qoder=600077、魔搭=?） |
| 3 | **Dify 重新发布后的分享链接** | 边修了必须重新导入+发布，否则仍是旧的断图应用 |
| 4 | **Qoder 账号 UID** | 官方要求，用于核对站点归属（设置 → 个人资料 → 编辑） |

拿到 1、2 之后，`tools/submit_to_platform.mjs` 可以直接提交：

```bash
export OC_COOKIE='<你的平台 cookie>'
node tools/submit_to_platform.mjs --question 600076 \\
  --repo https://github.com/tangtang-cx/ai-ecosystem \\
  --branch 2026-competition-ecosystem --commit 5fde725088adbb3f9f9134411fb2cd24865fb8ef \\
  --extra websiteUrl=https://cloud.dify.ai/chat/share?shareId=xxxxxxxx
```

脚本会先读 `submissionOptions` 确认这题要哪些字段，再按平台自己的字段规则提交，
并打印平台返回的结果。
"""

Path("SUBMISSION_CHECKLIST.md").write_text(NEW, encoding="utf-8", newline="")
print("SUBMISSION_CHECKLIST.md rewritten; PUA:", sum(1 for ch in NEW if 0xE000 <= ord(ch) <= 0xF8FF))
