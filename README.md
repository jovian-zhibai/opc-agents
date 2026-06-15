# OPC 智能系统

1 个主 Agent（Director）+ 8 个子 Agent，在 OpenCode 中运行。

## 快速开始

```bash
# 启动 OpenCode
opencode
```

## 三种交互方式

| 方式 | 怎么做 | 适合 |
|------|--------|------|
| **直接说需求** | 输入任务描述，Director 自动分配 | 日常开发、改 Bug、写功能 |
| **@提及** | `@dev` `@product` `@qa` `@guardian` `@ui-ux` `@growth` `@finance` `@advisor` | 需要特定角色时 |
| **Tab 切换** | 在 Director 和 Advisor 之间切换 | 想直接和智囊聊天时 |

## Agent 速查

| Agent | 干什么 | 什么时候用 |
|-------|--------|-----------|
| Director | 调度指挥 | 所有任务的入口 |
| Dev | 写代码、改代码、部署 | 需要写/改/读代码 |
| Product | 梳理需求、写 PRD | 新想法需要澄清 |
| UI-UX | 设计界面 | 做页面设计 |
| QA | 测试、代码审查 | Dev 写完需要验证 |
| Guardian | 安全扫描、技术债 | 安全检查、巡检 |
| Growth | 内容策略、增长 | 写文章、做推广 |
| Finance | 定价、成本、ROI | 算钱 |
| Advisor | 分析、决策辅助 | 纠结时问怎么选 |

## 常用命令

```
"帮我写一个登录功能"         → Director 自动走完整流水线
"检查一下项目安全"           → 调 Guardian
"这个功能值不值得做"         → 调 Product + Advisor
"算一下服务器成本"           → 调 Finance
"自检" / "巡检"              → Director 执行每日自检
"全面审查这个项目"           → 全 Agent 深度审查
```

## 流水线

```
需求 → Product(PRD) → UI-UX(设计) → Dev(技术方案/实现) → QA(测试) → Guardian(安全) → 归档
```

Director 自动推进，遇到架构变更/P0 漏洞/3 轮 QA 不过才暂停问创始人。

## 文件结构

```
.opencode/agents/     ← Agent 定义
.opencode/skills/     ← Skill 库（200+）
.opencode/work/       ← 任务产出
scripts/              ← 自动化脚本
CLAUDE.md             ← 系统规则（Agent 读的）
README.md             ← 本文件（人读的）
```

## 故障排查

| 问题 | 解法 |
|------|------|
| Director 自己干活不调度 | 已修复（v1.6），工具全关。检查 Director 的 tools 全是 false |
| 子 Agent 不工作 | 检查 OpenCode 是否加载了该 Agent 文件 |
| 产出文件在哪 | `.opencode/work/{任务名}/` |
| Skill 报错 | 检查 `.opencode/skills/` 下该 skill 是否存在 |
| 中断恢复 | 新会话启动后说 "继续上次的" |
| 会话记录 | `.opencode/work/session-notes.md` — 自动记录踩过的坑 |
