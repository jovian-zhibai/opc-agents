---
name: meeting-minutes
description: OPC 会议纪要生成，自动整理会议记录并写入知识库
triggers:
  - "会议纪要"
  - "会议记录"
  - "写入纪要"
  - "散会"
auto_load: false
---

# OPC 会议纪要

## 会议纪要格式

写入 $OPC_KNOWLEDGE_PATH/09-Conversations/ 目录（默认 /Users/souljian/code/opc/opc-knowledge）。

文件命名：{YYYY-MM-DD}-{议题简述}.md

## 模板

```markdown
---
date: {YYYY-MM-DD}
type: meeting
participants: {参会 Agent 列表}
topic: {议题}
status: {decided|pending|cancelled}
---

# {议题}

## 参会人员
- Director/总指挥
- {其他参会 Agent}

## 议题
{议题描述}

## 发言记录

### {Agent名}
{发言内容}

### Advisor/智囊 评论
{Advisor 对上述发言的分析}

## 决策
{最终决策}

## 待办
- [ ] {待办事项1} — 负责人：{Agent}
- [ ] {待办事项2} — 负责人：{Agent}
```

## 规则

1. 会议结束后 Director 必须先写入纪要，再宣布散会
2. 写入格式：`[Director] 会议结束，正在写入纪要...` → 写入完成 → `[Director] 纪要已归档，散会。`
3. 纪要必须包含：参会人、议题、发言记录、决策、待办
4. 写入时替换所有占位符：{YYYY-MM-DD} → 实际日期，{议题} → 实际议题，{参会 Agent 列表} → 实际参会 Agent，{发言内容} → 实际发言，{最终决策} → 实际决策，{待办事项} → 实际待办
