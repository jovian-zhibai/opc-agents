# C2/C3 设计方案

## C2 反馈闭环

> **C2 状态：已评估·暂不实施（2026-08-29）**。反馈是涓流，给涓流建消费/看板属过早工程；现状"只记不消费"够用。待反馈量起来再议看板。

### 数据来源
复用 `feedback.schema.json` 格式，三种信号：
- `user_confirm` — 创始人接受产出
- `user_reject` — 打回（最强负反馈）
- `user_rate` — 1-5 评分

### 写入时机
Director 在会话收尾（`prompts/director.md` 已有"反馈信号"步骤）时，
若创始人明确接受/打回/评分，按 schema 格式写入一条 JSONL 到
`$OPC_WORK_PATH/agent-metrics/{agent-name}.jsonl`。

### 消费方
AgentManager 定期（批量扫描时）读取 metrics 数据，产出"Agent 表现评估"：
- 打回率趋势
- 各 agent 薄弱维度
- 优化建议（走人在回路流程：AgentManager 建议 → Director 审查 → Dev 执行 → 创始人确认）

### 冷启动
不等 100 条。`user_reject`（打回）是最强信号，几条就有意义。

---

## C3 老笔记复审

> **实现状态：扫描已落地**（`scripts/auto-check.sh`，以 `last_reviewed` 字段判断、mtime 兜底，超 180 天未复审即列出）。以下"标记与重置"的日常执行（复审后更新 `last_reviewed` 字段）仍需人工/Director 在自检时完成，脚本只负责发现、不负责写回。

### 触发时机
挂在每日自检（Director 说"自检"/"巡检"时执行）或 quality-gate 定期自检。

### 扫描逻辑
遍历 `$OPC_KNOWLEDGE_PATH` 下所有 `.md` 文件，
`find -name "*.md" -mtime +180` 找超过 180 天未修改的笔记。

### 提醒方式
列出超期条目清单，由 Director 在自检报告中输出：
"⚠️ 以下知识条目超过 180 天未复审：[列表]，建议确认是否仍有效。"

### 标记与重置
复审后在文中加/更新 `last_reviewed: YYYY-MM-DD` 字段，扫描基于该字段判断（不用 touch——touch 会污染 mtime，无法区分"内容更新"和"复审过"）。
不改内容结构，不改文件命名。
