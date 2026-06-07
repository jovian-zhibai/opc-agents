---
name: daily-check
description: OPC 每日自检，检查知识库、任务状态、Git 状态、过期知识
triggers:
  - "每日自检"
  - "daily check"
  - "状态速览"
  - "今天做什么"
  - "系统自检"
auto_load: true
---

# OPC 每日自检

## 检查项目

1. **知识库 Inbox** — 扫描 $OPC_KNOWLEDGE_PATH/00-Inbox/ 未处理内容（默认 /Users/souljian/code/opc/opc-knowledge）
2. **活跃任务** — 扫描 $OPC_KNOWLEDGE_PATH/10-Tasks/ 中活跃任务
3. **Git 状态** — 检查当前项目的未提交变更
4. **过期知识** — 超过 180 天的 active 知识需复审
5. **巡检提醒** — 超过 7 天未巡检则建议触发 Guardian

## 输出格式

**[Director/总指挥]** 每日自检报告：
📋 状态速览：
- 知识库：{未处理条目数} 条待整理
- 任务：{活跃任务数} 个进行中
- Git：{未提交变更数} 个变更
- 过期知识：{过期条目数} 条需复审
📌 今日建议：{优先处理事项}
