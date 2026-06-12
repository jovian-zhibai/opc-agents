# OPC Agents

一人公司（One Person Company）的 AI Agent 团队系统。

基于 OpenCode 原生 Agent 系统构建，配置驱动 + 智能 Prompt + 自动化。

## 架构

1 个主 Agent + 9 个子 Agent：

| Agent | 中文名 | 模型 | 模式 | 角色 |
|-------|--------|------|------|------|
| **Director** | 总指挥 | deepseek-v4-flash | primary | 调度决策 |
| **Advisor** | 智囊 | deepseek-v4-flash | all | 分析质疑、决策辅助 |
| **Dev** | 工程师 | deepseek-v4-flash | subagent | 代码实现 |
| **Product** | 产品经理 | deepseek-v4-flash | subagent | 需求澄清（苏格拉底式） |
| **UI-UX** | 设计师 | deepseek-v4-flash | subagent | 设计体验 |
| **Guardian** | 哨兵 | deepseek-v4-flash | subagent | 安全审查 |
| **Growth** | 增长 | deepseek-v4-flash | subagent | 内容运营 |
| **QA** | 测试 | deepseek-v4-flash | subagent | 测试验证 |
| **AgentManager** | 管理者 | deepseek-v4-flash | subagent | Agent 生命周期管理 |
| **Finance** | 财务 | deepseek-v4-flash | subagent | 记账合规 |

## 模型分配原则

- **deepseek-v4-flash**（全部 Agent）：1M 上下文

## 快速开始

1. Clone 本仓库
2. 在目录下启动 OpenCode
3. Director 会自动启动，执行每日自检

## 交互方式

- **Tab 切换**：在 Director 和 Advisor 之间切换
- **@提及**：直接调用某个 Agent（如 `@dev 帮我看这个报错`）
- **自动调度**：描述任务，Director 自动分配给合适的 Agent

## 任务分级

| 级别 | 场景 | 调用谁 |
|------|------|--------|
| L0 | 格式调整、简单问答 | Director 自己搞定 |
| L1 | 代码小改、需求分析 | 调 1 个 agent |
| L2 | 功能开发、技术方案 | 调 2-3 个，走流水线 |
| L3 | 架构决策、产品方向 | 全员会议，等确认 |

## 开发流水线

需求澄清(Product) → 设计(UI-UX) → 技术方案(Dev+Advisor) → 实现(Dev) → 验证(QA) → 归档(Director)

## 文件结构

```
opencode.json               MiMo provider + 模型配置（可提交版本管理）
.opencode/
├── agents/                 10 个 Agent 定义
├── skills/                 275 个技能（社区 + OPC 专属）
└── work/                   长任务工作区（运行时产出，不提交）
scripts/
├── auto-check.sh           每日自检
├── quality-gate.sh         质量门禁
└── state-manager.py        状态管理（含中断恢复）
CLAUDE.md                   系统规则
templates/                  项目模板
```

## 环境变量

```bash
# 必填
export MIMO_API_KEY="your_key"

# 可选（默认 ~/code/opc/opc-knowledge）
export OPC_KNOWLEDGE_PATH="/path/to/opc-knowledge"
```

## 中断恢复

长任务中断后，新会话启动时 Director 会自动检测未完成的任务并从中断点继续。

## 知识库

通过 MCP 接入 Obsidian，详见 CLAUDE.md 中的知识库配置。

## 原则

- Agent 负责执行层，创始人负责决策层
- QA 和 Guardian 的首要职责是质疑，不是配合
- 文档是交付物的一部分
- 不读取上下文就开工 = 返工
- 知识有保质期，超过 180 天需复审
- 需要"判断力"的用 Pro，需要"执行力"的用 Lite
