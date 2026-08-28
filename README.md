# OPC Agents

一人公司（One Person Company）AI Agent 团队系统。

Director + 9 个子 Agent 的调度式协作架构。**五运行时单源架构**：`prompts/` 是唯一真相源，通过 `adapters/<runtime>.yaml` 声明式转换规则 + `scripts/generate-agents.py` 生成器，支持 **OpenCode / Claude Code / Pi / Gemini / Codex** 五种运行时。

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

### 五运行时

| 运行时 | 入口 | 启动方式 |
|--------|------|----------|
| **Claude Code** | `CLAUDE.md`（标记块注入红线） | `cd opc-agents && claude` |
| **OpenCode** | `opencode.json` + `.opencode/agents/` | `cd opc-agents && opencode` |
| **Pi** | `.pi/agents/` | 按 Pi 运行时规范启动 |
| **Gemini** | `.gemini/agents/` | 按 Gemini CLI 规范启动 |
| **Codex** | `.codex/agents/*.toml` | 按 Codex CLI 规范启动 |

> **模型配置**：各运行时的模型由用户自己的全局配置决定（如 Codex 的 `~/.codex/config.toml`），生成的 agent 文件不硬编码 model 字段。

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

## 五运行时单源架构

### 核心原则

- **唯一真相源**：`prompts/` 目录下的 10 个角色定义是唯一真相源，包含 front matter（description）+ 正文
- **声明式转换**：`adapters/<runtime>.yaml` 定义每个运行时的转换规则（路径替换、章节处理、front matter、输出格式等）
- **生成器**：`scripts/generate-agents.py` 从 `prompts/` + adapter 生成各运行时的 agent 定义文件
- **生成产物入库**：各运行时的 agent 文件（`.opencode/agents/`、`.claude/agents/`、`.pi/agents/`、`.gemini/agents/`、`.codex/agents/`）提交入库，靠 CI 同步校验保证不漂移

### 生成流程

```bash
# 生成单个运行时的所有角色（dry-run，显示差异）
python3 scripts/generate-agents.py --runtime=opencode --all

# 写入文件
python3 scripts/generate-agents.py --runtime=opencode --all --write

# 生成单个角色
python3 scripts/generate-agents.py --runtime=codex --role=director --write

# CLAUDE.md 标记块注入（红线节从 prompts/director.md 同步）
python3 scripts/generate-agents.py --entry-block CLAUDE.md --section 红线 --write

# 列出可用运行时
python3 scripts/generate-agents.py --list
```

### 各运行时格式

| 运行时 | 输出格式 | 目录 | 说明 |
|--------|----------|------|------|
| OpenCode | markdown + YAML front matter | `.opencode/agents/*.md` | front matter 从现有文件提取（含 mode/temperature/tools/permission/skills），正文从 prompts/ 生成 |
| Claude Code | markdown（无 front matter） | `.claude/agents/*.md` | 正文从 prompts/ 生成，strip front matter |
| Pi | markdown（无 front matter） | `.pi/agents/*.md` | 同上 |
| Gemini | markdown（无 front matter） | `.gemini/agents/*.md` | 同上 |
| Codex | TOML | `.codex/agents/*.toml` | name/description/developer_instructions，model 由用户全局配置决定 |

### CLAUDE.md 标记块机制

`CLAUDE.md` 是 Claude Code 的入口文件，其中"红线"节使用标记块注入：

```markdown
<!-- OPC:GENERATED:START -->
## 红线
...（从 prompts/director.md 红线节生成）
<!-- OPC:GENERATED:END -->
```

生成器只替换标记块内内容，块外手工内容（调度机制、知识库目录、搜索工具映射等）保持不动。CI 校验标记块与 prompts/ 同步，防止静默漂移。

### OpenCode Skill 说明

OpenCode 的 agent front matter 声明了若干 skill（如 anysearch、multi-search-engine 等），目录 `.opencode/skills/` 下需自行准备。**系统以运行环境为准**：Director 会先调 `skill-index` 探测本机实际可用的 skill，按意图选最适合的（本机装了什么就用什么，他人 clone 后技能不同也能自动适配），探测不到才回退 routing.yaml 的参考实现；仍无匹配才按降级规则处理（搜索类走 webfetch 替代，流程编排类走 prompt 内置逻辑），不会中断。其他运行时无 skill 机制，可忽略。

## 任务分级

| 级别 | 场景 | 调用谁 |
| ------ | ------ | -------- |
| L0 | 格式调整、简单问答 | Director 自己搞定 |
| L1 | 代码小改、需求分析 | 调 1 个子 Agent |
| L2 | 功能开发、技术方案 | 调 2-3 个，走流水线 |
| L3 | 架构决策、产品方向 | 全员 + 创始人确认 |

## 开发流水线

需求澄清(Product) → 设计(UI-UX) → 技术方案(Dev+Advisor) → 实现(Dev) → 验证(QA) → 安全(Guardian) → 归档(Director)

## 五运行时会话启动自动检查

五个运行时统一实现"会话启动时自动跑一次检查"，通过各运行时的原生 hook/插件机制触发，不依赖模型自愿遵守。

### 统一行为规格

会话启动时注入以下内容（克制原则，只加高频高危）：
1. **中断恢复**：检查未完成任务（`scripts/state.json`），提醒是否继续
2. **会话引导**：读 `work/session-notes.md` 最后 20 行，了解上次干到哪
3. **高危流程提醒**：涉及钱/用户可见变化需问创始人、QA 3 次失败上报
4. **任务前查教训**（仅用户提交 prompt 时）：提取关键词检索 lessons-index

### 共享核心

`scripts/opc_session_hook.py` 是五运行时通用的核心逻辑，各运行时的 hook 脚本都是薄封装，调用这个核心后按各运行时的格式输出。

两种使用方式：
- 命令行：`echo '{"mode": "session_start"}' | python3 scripts/opc_session_hook.py`
- 模块导入：`from opc_session_hook import generate_context`

### 各运行时实现

| 运行时 | 机制 | 事件 | 配置位置 | hook 脚本 | 类型 |
|---|---|---|---|---|---|
| **Claude Code** | 原生 hooks | SessionStart + UserPromptSubmit | `.claude/settings.json` | `.claude/hooks/lessons-prompt.py` | (a) 真 hook |
| **OpenCode** | 插件系统 | session.created | `.opencode/plugins/opc-session-hook.ts` | 同左（TypeScript 插件） | (b) 插件间接实现 |
| **Pi** | extension API | before_agent_start | 模板 `.pi/hooks/opc-session-hook.ts.template` | 复制到 `~/.pi/agent/extensions/` | (a) 真 hook |
| **Gemini CLI** | 原生 hooks | SessionStart | `.gemini/settings.json` | `.gemini/hooks/session-start.py` | (a) 真 hook |
| **Codex CLI** | 原生 hooks | SessionStart | `.codex/hooks.json` | `.codex/hooks/session-start.py` | (a) 真 hook |

> **降级原则**：任何 hook 执行失败都静默跳过，不影响正常流程。共享核心的任何一步（读文件/检索/解析）失败也静默跳过。

## 项目结构

```
CLAUDE.md                  Claude Code 入口（Director 系统 prompt，红线节标记块注入）
routing.yaml               操作归属路由表（单一真相源）
feedback.schema.json       反馈信号格式定义
opencode.json              OpenCode 入口
prompts/                   唯一真相源：10 个角色定义（front matter + 正文）
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
adapters/                  运行时适配配置（声明式转换规则）
├── opencode.yaml
├── claude-code.yaml
├── pi.yaml
├── gemini.yaml
└── codex.yaml
.opencode/                 OpenCode 运行时产物
├── agents/                10 个 Agent 定义（含 front matter，生成器生成）
├── plugins/               OpenCode 插件（opc-session-hook.ts 会话启动自动检查）
└── skills/                通用 Skill 库
.claude/                   Claude Code 运行时产物
├── agents/                10 个 Agent 定义（生成器生成）
├── hooks/                 Claude Code hooks（lessons-prompt.py 会话启动自动检查 + protect-prompts.py 受保护文件硬拦截）
└── settings.json          hook 配置（SessionStart/UserPromptSubmit/PreToolUse）
.pi/                       Pi 运行时产物
├── agents/                10 个 Agent 定义（生成器生成）
└── hooks/                 Pi extension 模板（opc-session-hook.ts.template，复制到 ~/.pi/agent/extensions/）
.gemini/                   Gemini 运行时产物
├── agents/                10 个 Agent 定义（生成器生成）
├── hooks/                 Gemini hooks（session-start.py 会话启动自动检查）
└── settings.json          hook 配置（SessionStart）
.codex/                    Codex 运行时产物
├── agents/                10 个 Agent 定义（生成器生成，TOML 格式）
├── hooks/                 Codex hooks（session-start.py 会话启动自动检查）
└── hooks.json             hook 配置（SessionStart）
scripts/                   自动化脚本
├── auto-check.sh          每日运维自检（知识库 Inbox、活跃任务、Git 状态、过期知识）
├── generate-agents.py     多运行时 Agent 生成器（prompts/ + adapter → 各运行时产物）
├── opc_session_hook.py    五运行时会话启动自动检查共享核心（中断恢复+会话引导+流程提醒+教训检索）
├── quality-gate.sh        一致性检查（跑这个确认生成产物与 prompts/ 未漂移）
└── state-manager.py       状态管理（含中断恢复）
tests/                     pytest 测试
├── test_adapter_schema.py     adapters/*.yaml 结构校验（23 用例）
├── test_toml_serialization.py TOML 序列化健壮性 + 对抗测试（12 用例）
├── test_routing_schema.py     routing.yaml 结构校验（9 用例）
├── test_quality_gate_drift.py quality-gate 漂移检测
├── test_state_manager.py      state-manager 全覆盖（33 用例）
└── ...
.github/workflows/         CI 流水线
├── ci.yml                 OPC Agents CI（pytest/ShellCheck/生成同步校验/CLAUDE.md 标记块校验/secret 扫描）
└── quality-gate.yml       quality-gate.sh 自动运行
.githooks/                 Git hooks（pre-commit 自动跑生成器 + quality-gate）
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
| 引入 CI 门禁（GitHub Actions） | `.github/workflows/quality-gate.yml`（push/PR 到 main 自动跑 quality-gate.sh）+ `.github/workflows/ci.yml`（pytest/ShellCheck/生成同步校验/CLAUDE.md 标记块校验/secret 扫描） | 2026-08 |
| 引入 pre-commit 门禁 | `.githooks/pre-commit`：规则文件改动时自动跑生成器 + quality-gate，未通过即拦截提交 | 2026-08 |
| 五运行时单源架构 | `prompts/` 唯一真相源 + `adapters/*.yaml` 声明式转换 + `scripts/generate-agents.py` 生成器，支持 opencode/claude-code/pi/gemini/codex。生成产物入库，CI 同步校验防漂移 | 2026-08 |
| Director 单源化 | Director 纳入生成器（去掉 SKIP_ROLES），5 运行时 director 文件从 prompts/ 生成；CLAUDE.md 红线节用标记块注入，块外手工内容保持不动 | 2026-08 |
| Codex agent 不硬编码 model | `.codex/agents/*.toml` 只含 name/description/developer_instructions，model 由用户自己的 `~/.codex/config.toml` 全局配置决定（ConfigToml.model 是 Option，缺省回落全局）。硬编码会把私有模型名/本地代理语义泄进公开仓库，且模型属环境关切不该焊进入库产物 | 2026-08 |
| description 单源化 | `prompts/*.md` 加 front matter（只含 description），codex 的 description 从 prompts/ 提取，不再从 .opencode/ 捞，消除跨运行时耦合 | 2026-08 |

### 多运行时文件保护（预期设计，勿"修复"）

Director 红线要求不直接改系统文件。各运行时的物理拦截力度已对齐：

| 运行时 | 拦截方式 |
|--------|----------|
| Claude Code | `.claude/settings.json` PreToolUse hook（protect-prompts.py）对 `prompts/`、`.opencode/agents/`、`CLAUDE.md`、`routing.yaml`、`feedback.schema.json`、`opencode.json` 的 Write/Edit 硬拦截（exit 1） |
| OpenCode | `opencode.json` permission.edit 对相同路径设为 `deny`（不允许、不询问） |

这是**预期设计**：Director 改系统文件的通道在各运行时都被物理切断，不走"LLM 自觉"或"弹窗询问"。
受保护文件的修改一律由创始人手动进行，或经正式流程（调度 AgentManager/Dev 通过其它方式执行）。
