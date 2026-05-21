---
name: write-adr
description: "架构决策记录（ADR）写作规范。用于记录重要的技术或产品架构决策。"
---

# ADR 写作 Skill

当团队做出重要架构决策时，必须写 ADR 记录到知识库。

## 何时写 ADR

- 选择两种以上的技术方案时
- 改变已有架构或设计时
- 拒绝某个需求为不可行时
- 任何未来 Agent 会问"为什么这样做"的决策

## 写入流程

1. 确认决策已达成
2. 按下方模板撰写 ADR
3. 写入到 `../opc-knowledge/01-ADR/{YYYY-MM-DD}-{简短标题}.md`
4. 在相关 PRD 或会议纪要中引用此 ADR

## ADR 模板

```yaml
---
date: 2026-05-20
type: adr
status: proposed | accepted | deprecated | superseded
author: Dev
related: [关联的 PRD 或会议纪要]
---
```

## 正文结构

### 背景
为什么需要做这个决策？当前遇到了什么问题或需求？

### 选项
列出考虑过的所有方案，每个方案包含：

**选项 A：[方案名]**
- 优势：
- 劣势：

**选项 B：[方案名]**
- 优势：
- 劣势：

### 决策
选择哪个方案，以及选择的理由。

### 后果
这个决策带来的影响：
- 正面影响：
- 负面影响/风险：
- 需要的后续行动：

## 状态流转

```
proposed → accepted → deprecated
                   → superseded (被新 ADR 替代)
```

- `proposed`：刚提出，待确认
- `accepted`：已确认，正在执行
- `deprecated`：已废弃，不再适用
- `superseded`：被新的 ADR 替代（在 related 中引用新 ADR）

## 质量要求

- 选项必须至少两个，不能只有一个"方案"
- 决策理由必须具体，不能是"感觉这样好"
- 后果必须包含负面影响，不能只说好处
- 被拒绝的方案也要记录，防止后人重复讨论
