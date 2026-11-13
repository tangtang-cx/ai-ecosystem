# 15 条审查规则（oceanbase-sql-reviewer Skill）

| 编号 | 级别 | 标题 | 说明 |
| --- | --- | --- | --- |
| OB-001 | 🔴 阻断 | UPDATE / DELETE 缺 WHERE | 无 WHERE 会更新/删除全表 |
| OB-002 | 🔴 阻断 | JOIN 缺 ON/USING | 笛卡尔积 |
| OB-003 | 🔴 阻断 | 建表缺主键 | 无 PRIMARY KEY |
| OB-004 | 🟠 警告 | `SELECT *` | 无法用覆盖索引、回表多 |
| OB-005 | 🟠 警告 | `LIKE '%x'` 前置通配 | 索引失效 |
| OB-006 | 🟠 警告 | 索引列被函数包裹 | `DATE(col)`/`lower(col)` 等 |
| OB-007 | 🟠 警告 | 深分页 OFFSET | 大 OFFSET 扫描并丢弃 |
| OB-008 | 🟠 警告 | NOT IN / != 与 NULL | 遇 NULL 结果集异常 |
| OB-009 | 🟠 警告 | IN 列表过长 | >50 项拖慢解析 |
| OB-010 | 🟠 警告 | FOR UPDATE 无 WHERE | 锁全表 |
| OB-011 | 🔵 提示 | UNION 去重开销 | 不需要去重用 UNION ALL |
| OB-012 | 🔵 提示 | TRUNCATE 清表 | DDL 语义、不可回滚 |
| OB-013 | 🔵 提示 | 缺执行计划验证 | 建议 EXPLAIN |
| OB-014 | 🔵 提示 | 疑似隐式类型转换 | 数字字面量 vs 字符串列 |
| OB-015 | 🔵 提示 | `COUNT(1)` | 统一 `COUNT(*)` |

规则与 `scripts/review_rules.py` 一一对应，纯标准库实现，离线可用、确定性可复现。
