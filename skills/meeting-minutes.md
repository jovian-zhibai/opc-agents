---
name: meeting-minutes
description: "会议纪要写作规范。用于 Director 在每次会议结束后撰写标准化会议纪要并归档到知识库。"
---

# 会议纪要 Skill

Director 在每次会议结束后必须执行此流程，会议未写纪要视为未完成。

## 写入流程

1. 会议决策完成后，Director 输出：`[Director] 会议结束，正在写入纪要...`
2. 按下方模板撰写纪要
3. 写入到 `../opc-knowledge/09-Conversations/{YYYY-MM-DD}-{简短标题}.md`
4. 写入完成后输出：`[Director] 纪要已归档，散会。`

## 纪要模板

```yaml
---
date: 2026-05-20
type: meeting
participants: [Director, Dev, QA, Advisor]
topic: "会议主题"
status: active
related: [关联的 ADR 或 PRD 文件名]
---
```

## 正文结构

### 议题
一段话说清楚这次会议讨论什么。

### 发言记录
按参会顺序记录每位 Agent 的核心观点，格式：

**[Agent/中文名]**
- 观点 1
- 观点 2

### 决策
明确列出会议达成的决策，格式：
1. 决策内容 — 理由
2. 决策内容 — 理由

### 待办
列出会后需要执行的行动项，格式：
- [ ] [Agent] 具体任务 — 截止时间
- [ ] [Agent] 具体任务 — 截止时间

### 遗留问题
未达成一致或需要后续跟进的问题：
- 问题描述 — 下次讨论时间

## 质量要求

- 纪要必须在会议结束后立即写入，不能拖延
- 每位参会 Agent 的发言都要记录，不能遗漏
- 决策必须明确，不能有模糊表述
- 待办必须有负责人和截止时间
- 文件命名必须遵循 `{YYYY-MM-DD}-{简短标题}.md` 格式
