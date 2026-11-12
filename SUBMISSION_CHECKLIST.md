# 提测清单（填表前先自查）

> 官方要求：「在测评平台提交时的分支/commit hash 基于此分支进行开发，相关项目资产放入对应
> <task> 目录中」——**分支名大小写敏感**（git 行为），资产目录名必须与官方脚手架一致（小写）。

---

## 0. 先跑一次自查（30 秒）

```bash
# 用与提测相同的凭据校验：仓库可达 / 分支存在 / commit 可达 / 资产目录非空
export GITHUB_TOKEN=<你的 GitHub PAT>
node tools/check_submission.mjs <分支> <40位commit> <资产目录>
# 期望输出：4 个 ok + RESULT: submittable
```

> 踩过的坑（2026-11-12）：分支写成 `Qoder`，而仓库里的分支叫 `qoder` →
> 平台 `clone --branch Qoder` 找不到分支 → **执行失败 0.000**。
> 现在两种大小写都建了别名，但**建议统一写小写**（与官方脚手架目录名一致）。

---

## 1. 五个赛题的提测坐标（全部基于官方基线 `d647275c`）

仓库地址（**唯一可用格式**，缺用户名或缺令牌都会判 `failMsg=4` → 0.000 秒失败）：

```text
https://wzhaihqy:<你的 GitHub PAT>@github.com/tangtang-cx/ai-ecosystem.git
```

| 赛题 | Branch | Commit id | 资产目录 | 自查 |
| --- | --- | --- | --- | --- |
| Dify | `dify`（或 `Dify`） | `006f0f7094ef46f81606551962d5b763dcb2c21b` | `dify/` | ✅ |
| Qoder | `qoder`（或 `Qoder`） | `b66ed07b4f6a9b154a0996d55f721f7289ab9cad` | `qoder/` | ✅ |
| 魔搭社区 | `modelscope` | `46299d3d294df7200142c33728a70d3fb8022558` | `modelscope/` | ✅ |
| 高德 | `gaode` | `1ff93437c1a3f996b7e18998d3da48ea103b6ec9` | `gaode/` | ✅ |
| StepFun | `stepfun` | `0c11f29bb9180671ce02d7b9cb070ffd12db6213` | `stepfun/` | ✅ |
| 全部生态赛题合并版 | `2026-competition-ecosystem` | `828a874bfbbac392d2b6340b51d39e9ddeb5d30a` | 全部 | ✅ |
| 加赛（向量库 / PowerContext） | `2026-competition-powercontext` | `c06bca1b9a134231689d5616f7f0f5392cd005a4` | `src/powercontext/` | ✅ |

> **魔搭社区这一题不填仓库**：它的提交物是 Skill 网址
> `https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer`（已提交成功）。

---

## 2. 提测前必须做的三件事

| # | 事项 | 状态 |
| --- | --- | --- |
| 1 | 分支名 / commit / 资产目录三项对上，跑 `check_submission.mjs` 确认 | ✅ 上表已验 |
| 2 | 仓库保持**私有**（官方不允许 Public 参赛） | ✅ private=true |
| 3 | 仓库里**没有真实凭据**（`.env.example` 全是占位值） | ✅ |

---

## 3. 各赛题还需要单独提供的材料

| 赛题 | 额外材料 | 在哪 |
| --- | --- | --- |
| Dify | DSL（`dify/app.yml`）、运行说明、验证样例 | `dify/README.md` §1–§4 |
| Qoder | **项目网站网址（Qoder Sites，任何人可访问）**、运行说明、验证样例、**Qoder 开发记录截图**、**Qoder 账号 UID** | `qoder/SITES_GUIDE.md`、`qoder/DEVELOPMENT_LOG.md` |
| 魔搭社区 | **Skill 网址或编号** | `modelscope/SKILL_UPLOAD.md` |
| 高德 | `gaode/SKILL.md` | — |
| StepFun | Web 应用 + 技术说明 | `stepfun/README.md`、`stepfun/TECH_REPORT.md` |

---

## 4. 平台返回码速查（社区实测）

| failMsg | 含义 | 常见原因 |
| --- | --- | --- |
| 1 | branch 不存在 | **分支名大小写写错**（本次 Qoder 就是这个） |
| 2 | commit_id 不存在 | SHA 写错/不是 40 位 |
| 3 | 编译失败 | — |
| 4 | git clone 失败 | 仓库地址格式不对（缺 `用户名:`）、token 无权限、仓库非私有 |
| 5 | git clone 超时 | 网络/仓库过大 |
| 6 | git reset 失败 | — |
| 7 | cmake 失败 | — |
| 8 | 验证失败 | 跑起来后的用例不通过 |
| 100 | 其他异常 | 提测侧问题（可发社区帖） |

出处：<https://ask.oceanbase.com/t/topic/35653426>
