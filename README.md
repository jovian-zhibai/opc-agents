# OPC Agents

一人公司（One Person Company）AI Agent 团队系统。

Director + 9 个子 Agent 的调度式协作架构。同时支持 **OpenCode** 和 **Claude Code** 两种运行环境。

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/jovian-zhibai/opc-agents.git
cd opc-agents

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 JENSEN003_API_KEY 与 SOULJIAN03_API_KEY
# （两个 key 被 opencode.json 的 provider 使用，从 https://token.sensenova.cn 获取）

# 3. 设置环境变量
export OPC_WORK_PATH=~/code/opc/opc-agents/work
export OPC_KNOWLEDGE_PATH=~/code/opc/opc-knowledge
mkdir -p $OPC_WORK_PATH $OPC_KNOWLEDGE_PATH

# 4. 说第一句话
#    创始人直接描述需求即可，Director 自动调度。例如：
#    "帮我写一个登录功能" → Director 走完整流水线
#    "检查一下项目安全" → 调 Guardian
```

### Claude Code

```bash
cd opc-agents
# CLAUDE.md 自动加载为 Director 系统 prompt，直接说需求
```

### OpenCode

```bash
cd opc-agents
opencode
# Director 自动运行，支持 Tab 切换和 @提及 调度子 Agent
```

## Agent 团队

| 角色 | 文件 | 中文名 | 职责 |
| ------ | ------ | -------- | ------ |
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

Director（总指挥）是唯一入口。创始人说需求 → Director 查归属表（`routing.yaml`）→ 读取对应子 Agent 的 prompt → 调度执行 → 审查产出 → 汇总报告。

**核心协作链路**：需求澄清(Product) → 设计(UI-UX) → 技术方案(Dev+Advisor) → 实现(Dev) → 验证(QA) → 安全审查(Guardian) → 归档(Director)。

Advisor 在关键决策点介入质疑，QA 和 Guardian 的首要职责是"找问题"而非"配合"。全部路由规则在 `routing.yaml` 单一真相源中定义。

**创始人只需要说需求，Director 自动调度。**

## 双运行时支持

| | Claude Code | OpenCode |
| --- | --- | --- |
| 入口文件 | `CLAUDE.md` | `opencode.json` + `.opencode/agents/` |
| Agent 调度 | task tool | Tab / @提及 |
| 提示词目录 | `prompts/`（共享） | `prompts/`（共享） + `.opencode/agents/`（front matter） |

两种运行时共享同一套归属表（`routing.yaml`）和 Agent 核心约束（`prompts/`）。9 个子 Agent 两版已收敛为同款精简版，核心章节（红线、职责边界、质量门禁、协作接口）保持一致。但各有运行时特定的头部（front matter）、产出路径（`$OPC_WORK_PATH/` vs `.opencode/work/`）和段落差异（如 director 的调度机制描述），并非逐字相同。改规则时须同步两份核心章节并跑 `bash scripts/quality-gate.sh` 确认（0 errors = 无漂移）。

> **已知的有意差异**：`prompts/` 版的「能力边界」章节（如 qa.md:76、agent-manager.md）在 `.opencode/agents/` 版中由 front matter 的 `skills:` 字段替代——OpenCode 用 front matter 机制声明 skill 依赖，Claude Code 用正文段落。此为设计而非漂移，不要"修复"。

### OpenCode Skill 说明

OpenCode 的 agent front matter 声明了若干 skill（如 anysearch、multi-search-engine 等），目录 `.opencode/skills/` 下需自行准备。若 skill 缺失，系统按 Director prompt 中的降级规则处理：搜索类走 webfetch 替代，流程编排类走 prompt 内置逻辑，不会中断。Claude Code 侧无 skill 机制，可忽略。

## 任务分级

| 级别 | 场景 | 调用谁 |
| ------ | ------ | -------- |
| L0 | 格式调整、简单问答 | Director 自己搞定 |
| L1 | 代码小改、需求分析 | 调 1 个子 Agent |
| L2 | 功能开发、技术方案 | 调 2-3 个，走流水线 |
| L3 | 架构决策、产品方向 | 全员 + 创始人确认 |

## 开发流水线

需求澄清(Product) → 设计(UI-UX) → 技术方案(Dev+Advisor) → 实现(Dev) → 验证(QA) → 安全(Guardian) → 归档(Director)

## 项目结构

```
CLAUDE.md                  Claude Code 入口（Director 系统 prompt）
routing.yaml               操作归属路由表（单一真相源）
feedback.schema.json       反馈信号格式定义
opencode.json              OpenCode 入口
prompts/                   共享 Agent 提示词（10 个文件，与 .opencode/agents/ 行为一致）
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
└── skills/                通用 Skill 库
scripts/                   自动化脚本
├── auto-check.sh          每日自检
├── quality-gate.sh        一致性检查（跑这个确认两版未漂移）
├── sync-opencode.sh       双环境核心章节单向同步（prompts/ → .opencode/agents/）
└── state-manager.py       状态管理（含中断恢复）
work/                      运行时产出目录
```

## 环境变量

```bash
# 必填：SenseNova API Key（从 https://token.sensenova.cn 获取）

# 必填：运行时产出路径和知识库路径
export OPC_WORK_PATH=~/code/opc/opc-agents/work
export OPC_KNOWLEDGE_PATH=~/code/opc/opc-knowledge
mkdir -p $OPC_WORK_PATH $OPC_KNOWLEDGE_PATH
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

## 已知决策

以下为有意不做的工程化项，非遗漏：

| 决策 | 理由 | 日期 |
| ------ | ------ | ------ |
| ~~不引入 CI 门禁~~（已废弃） | 原以为一人公司无 PR 流程、本地跑脚本即可；后规则文件多次漂移，改为 CI + pre-commit 双保险 | 2026-07-04 定，2026-08 废弃 |
| 引入 CI 门禁（GitHub Actions） | `.github/workflows/quality-gate.yml`（push/PR 到 main 自动跑 quality-gate.sh）+ `.github/workflows/ci.yml`（prompts 完整性、ShellCheck、secret 扫描） | 2026-08 |
| 引入 pre-commit 门禁 | `.git/hooks/pre-commit`：规则文件（CLAUDE.md/prompts/.opencode/routing.yaml/scripts）改动时强制跑 quality-gate，未通过即拦截提交 | 2026-08 |

### 双运行时文件保护（预期设计，勿“修复”）

Director 红线要求不直接改系统文件。两个运行时的物理拦截力度已对齐：

| 运行时 | 拦截方式 |
|--------|----------|
| Claude Code | `.claude/settings.json` PreToolUse hook（protect-prompts.py）对 `prompts/`、`.opencode/agents/`、`CLAUDE.md`、`routing.yaml`、`feedback.schema.json`、`opencode.json` 的 Write/Edit 硬拦截（exit 1） |
| OpenCode | `opencode.json` permission.edit 对相同路径设为 `deny`（不允许、不询问） |

这是**预期设计**：Director 改系统文件的通道在两个运行时都被物理切断，不走“LLM 自觉”或“弹窗询问”。
受保护文件的修改一律由创始人手动进行，或经正式流程（调度 AgentManager/Dev 通过其它方式执行）。
