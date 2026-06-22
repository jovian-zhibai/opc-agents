# OPC Agents

一人公司（One Person Company）AI Agent 团队系统。

Director + 9 个子 Agent 的调度式协作架构。同时支持 **OpenCode** 和 **Claude Code** 两种运行环境。

## 快速开始

### 使用 Claude Code

```bash
cd opc-agents
# Claude Code 自动加载 CLAUDE.md，Director 开始工作
# 直接说需求即可
```

### 使用 OpenCode

```bash
cd opc-agents
opencode
# Director 自动运行，支持 Tab 切换和 @提及 调度子 Agent
```

## Agent 团队

| 角色 | 文件 | 中文名 | 职责 |
|------|------|--------|------|
| **Director** | `prompts/director.md` | 总指挥 | 调度决策、信息汇总、质量把关 |
| **Advisor** | `prompts/advisor.md` | 智囊 | 分析质疑、决策辅助 |
| **Dev** | `prompts/dev.md` | 工程师 | 代码实现、技术方案、部署运维 |
| **Product** | `prompts/product.md` | 产品经理 | 需求澄清、PRD 输出、竞品分析 |
| **UI-UX** | `prompts/ui-ux.md` | 设计师 | 界面设计、用户体验、设计系统 |
| **Guardian** | `prompts/guardian.md` | 哨兵 | 安全审查、技术债识别、风险巡检 |
| **Growth** | `prompts/growth.md` | 增长 | 增长运营、内容策略、市场调研 |
| **QA** | `prompts/qa.md` | 测试 | 测试验证、质量把关、Bug 管理 |
| **Finance** | `prompts/finance.md` | 财务 | 记账合规、定价、成本控制 |
| **AgentManager** | `prompts/agent-manager.md` | 管理者 | Agent 生命周期管理、质量评估 |

## 工作方式

1. 创始人发布任务 → **Director (总指挥)** 自动接收
2. Director 查归属表 → 读取 `prompts/{role}.md` 获取子 Agent 提示词
3. Director 调度子 Agent 执行任务
4. 子 Agent 完成任务 → Director 审查产出 → 汇总报告给创始人

**你只需要说需求，Director 自动调度。**

## 双运行时支持

| | Claude Code | OpenCode |
|---|---|---|
| 入口文件 | `CLAUDE.md` | `opencode.json` + `.opencode/agents/` |
| Agent 调度 | task tool | Tab / @提及 |
| 提示词目录 | `prompts/`（共享） | `prompts/`（共享） + `.opencode/agents/`（front matter） |

两种方式共享同一套 Agent 提示词（`prompts/`），行为一致。

## 任务分级

| 级别 | 场景 | 调用谁 |
|------|------|--------|
| L0 | 格式调整、简单问答 | Director 自己搞定 |
| L1 | 代码小改、需求分析 | 调 1 个子 Agent |
| L2 | 功能开发、技术方案 | 调 2-3 个，走流水线 |
| L3 | 架构决策、产品方向 | 全员 + 创始人确认 |

## 开发流水线

需求澄清(Product) → 设计(UI-UX) → 技术方案(Dev+Advisor) → 实现(Dev) → 验证(QA) → 安全(Guardian) → 归档(Director)

## 项目结构

```
CLAUDE.md                  Claude Code 入口（Director 系统 prompt）
opencode.json              OpenCode 入口
prompts/                   共享 Agent 提示词（10 个文件）
├── director.md
├── advisor.md
├── dev.md
├── product.md
├── ui-ux.md
├── qa.md
├── guardian.md
├── growth.md
├── finance.md
└── agent-manager.md
.opencode/                 OpenCode 运行时配置
├── agents/                10 个 Agent 定义（含 front matter）
└── skills/                200+ 通用 Skill 库
scripts/                   自动化脚本
├── auto-check.sh          每日自检
├── quality-gate.sh        质量门禁
└── state-manager.py       状态管理（含中断恢复）
templates/                 项目模板
```

## 环境变量

```bash
# 必填：SenseNova API Key（从 https://token.sensenova.cn 获取）
export SENSENOVA_API_KEY="sk-..."

# 可选：知识库路径（默认 ~/code/opc/opc-knowledge）
export OPC_KNOWLEDGE_PATH="/path/to/opc-knowledge"
```

## 中断恢复

长任务中断后，新会话启动时 Director 自动检测未完成的任务并从中断点继续。

## 常用命令

```
"帮我写一个登录功能"         → Director 自动走完整流水线
"检查一下项目安全"           → 调 Guardian
"这个功能值不值得做"         → 调 Product + Advisor
"算一下服务器成本"           → 调 Finance
"自检" / "巡检"              → Director 执行每日自检
"全面审查这个项目"           → 全 Agent 深度审查
```

## 原则

- Director 负责调度决策，子 Agent 负责执行
- QA 和 Guardian 的首要职责是质疑，不是配合
- 文档是交付物的一部分
- 不读取上下文就开工 = 返工
- 知识有保质期，超过 180 天需复审
