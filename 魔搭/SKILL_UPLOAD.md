# 魔搭社区赛题 · 提交指引（提交物是 Skill 网址/编号）

> 题目要求：**上传并分享自己的 Skill**；提交产物 = **该 Skill 在魔搭社区的网址或编号**。
> （不是提交代码仓库，也不是提交录屏。）

---

## 0. 已完成：Skill 已上传（提测就填这个链接）

```text
https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer
```

- 已实测：未登录直接访问返回 **HTTP 200**，页面标题含 `oceanbase-sql-reviewer`（可见范围=公开生效）。
- 提测平台「魔搭社区」入口 → 粘贴上面这条网址 → 提交。

---

## 0.1 ⚠️ 验证行（第二轮判题要求，必须补）

第一轮判语：**「未找到提交时的验证行」** —— 平台签发了一行防伪标记，判题时要在**已发布的
SKILL.md** 里找到它。我们已把它插进 `SKILL.md` 的 frontmatter 之后（文件头部，任何头部校验都能命中）：

```markdown
<!-- OB-S:RmvSuPnRvTjZd4kLBSIaTg -->
```

**你还需要做的两步**（我无法代做，要用你的魔搭账号）：

1. 打开 Skill 页面 → 文件 → `SKILL.md` → 用新版内容覆盖上传（新版文件在本目录，
   也打包在 `oceanbase-sql-reviewer-skill.zip`），或者直接把上面那行加到旧文件末尾再保存；
2. 点「发布」让线上版本更新（**发布后修改需要再点一次发布才会更新线上**）；
3. 回提测平台，**重新提测**（网址不变，仍是 `https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer`）。

> 平台提示「无需主动重新生成验证行」——这行是平台签发的，照抄即可，不要自己编。

验证是否生效（发布后随时可查）：

```bash
curl -s https://modelscope.cn/skills/wzhaihqy/oceanbase-sql-reviewer/resolve/master/SKILL.md | grep -n 'OB-S:'
# 期望输出：6:<!-- OB-S:RmvSuPnRvTjZd4kLBSIaTg -->
```

---

## 1. 我们上传的 Skill

| 项 | 值 |
| --- | --- |
| 名称 | `oceanbase-sql-reviewer` |
| 一句话简介 | 审查 OceanBase / seekdb / MySQL 的 SQL 与 DDL，输出「病灶诊断 / 药方 / 忌口 / 养生建议」四段式报告；可用本地 bge-small-zh 向量 + seekdb 混合检索取回官方文档依据 |
| 目录 | 本目录（`modelscope/`）：`SKILL.md` + `scripts/review_rules.py` + `references/rules.md` |

内容要点：

- `SKILL.md`：带 YAML frontmatter（`name` / `description` / `license`）的完整技能说明，
  含触发场景、工作流程（先查 seekdb → 再跑静态规则 → 按四段式输出）、**技术准确性硬约束**
  （`VECTOR(n)`、HNSW/IK 索引写法、`@search_parm` + `DBMS_HYBRID_SEARCH.GET_SQL`、
  `dbms_index_manager.refresh()`，以及「不许编造 API」）。
- `scripts/review_rules.py`：15 条确定性规则扫描器，**仅标准库**，离线可用。
- `references/rules.md`：规则表。

---

## 2. 上传步骤（约 5 分钟）

1. 登录 <https://modelscope.cn>（用阿里云账号）。
2. 进入个人空间 → **创建 Skill / 上传 Skill**（模型社区的 Skill 入口）。
3. 填写：
   - 名称：`oceanbase-sql-reviewer`
   - 简介：见上表
   - README / 描述：可直接粘贴本文件 §1 的内容
4. 上传文件（把下面这些放进 Skill 目录）：

   ```text
   SKILL.md
   scripts/review_rules.py
   references/rules.md
   ```

5. 发布后确认**未登录也能打开**该页面（若可见范围可选，请选公开）。
6. 复制**完整页面链接**（形如 `https://modelscope.cn/skills/<你的账号>/oceanbase-sql-reviewer`）
   或页面上的 **Skill 编号**。

> ⚠️ 提交的信息必须能**准确定位到你上传的 Skill**：
> 不要填个人主页、账号 ID 或只有 Skill 名称。

---

## 3. 提测平台怎么填

进入「魔搭社区」赛题的提交入口，把第 2 步拿到的**网址或编号**粘进去：

```text
https://modelscope.cn/skills/<你的账号>/oceanbase-sql-reviewer
```

或

```text
<Skill 编号>
```

---

## 4. 上传前自检

```bash
# 规则脚本能跑（应当输出 WARN OB-004 / OB-007 等）
python scripts/review_rules.py "SELECT * FROM t WHERE DATE(c)='2026-01-01' LIMIT 20, 200000;"

# frontmatter 完整（name / description 必须有）
head -5 SKILL.md
```

- [ ] `SKILL.md` 的 frontmatter 里 `name` 与目录/页面名称一致
- [ ] 描述里写清了**什么时候该用**这个 Skill
- [ ] 附了简短使用示例（已在 SKILL.md 的「示例」一节）
- [ ] Skill 页面未登录可访问
- [ ] 已把完整网址或编号填进提测平台

---

## 5. 附：本目录里的另一件作品（ModelScope 推理 API 助手）

`app.py` + `modelscope_client.py` 是我们**调用魔搭免费推理 API** 的 Streamlit 助手
（题目「Just for Fun」那题的另一份产物，也是这个 Skill 的能力来源：Skill 里的
seekdb 检索 + LLM 深审就是它的一部分）。

```bash
pip install -r requirements.txt
export MODELSCOPE_API_KEY=ms-xxxx
python scripts/smoke_test.py     # 自检：38 个免费模型可用 + 真实对话
streamlit run app.py
```

但**魔搭社区这一题的提交物是上面 §2 的 Skill 网址/编号**，不是这个应用。
