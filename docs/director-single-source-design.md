# Director 单源生成架构设计（P1 阶段 A）

> 状态：设计稿，待 review。本文档只出设计，不改代码。
> 日期：2026-08-28

## 1. 背景与现状

### 1.1 当前架构

- `prompts/` 是 10 个角色的唯一真相源，9 个子角色已完成去运行时化（`{{WORK_PATH}}/` 占位符），由 `scripts/generate-agents.py` 从 `adapters/<runtime>.yaml` 读取规则生成 5 个运行时的 Agent 定义。
- `generate-agents.py` 中 `SKIP_ROLES = ['director']` 硬编码排除 Director，Director 在 5 个运行时全靠手工维护，漂移风险最高。

### 1.2 Director 为什么特殊

**两点必须解决：**

1. **路径前缀不统一**：Director 正文里引用的路径不止 `{{WORK_PATH}}/` 一种，还有 `$OPC_KNOWLEDGE_PATH/`（环境变量，带默认回退）。
2. **运行时专属行为**：Director 有"会话启动自动检查/中断恢复"这类生命周期事件触发的逻辑，opencode 有专属实现（prompt 正文顶部的"会话启动自动检查"节），其它运行时没有或不同。这不是纯文本，不能靠生成 md/toml 解决。

### 1.3 当前 5 个入口文件现状

| 运行时 | Director 入口文件 | 状态 | hook 机制 |
|---|---|---|---|
| opencode | `.opencode/agents/director.md`（mode: primary） | 存在，手工维护 | 无原生 hook，靠 prompt 正文"会话启动自动检查"节强制 |
| claude-code | `CLAUDE.md` | 存在，手工维护 | `UserPromptSubmit` hook（`.claude/hooks/lessons-prompt.py`）+ `PreToolUse` hook |
| pi | `.pi/SYSTEM.md` | **不存在**（adapter 声明了但文件未建） | 用户本地 `~/.pi/agent/extensions/opc-lessons-hook.ts`（不在仓库） |
| gemini | `.gemini/settings.json` | **不存在** | 无 |
| codex | `.codex/config.toml` | **不存在** | 无 |

### 1.4 prompts/director.md 路径引用清单

| 路径模式 | 出现次数 | 行号 | 处理方式 |
|---|---|---|---|
| `{{WORK_PATH}}/` | 5 | 225, 232, 241, 500, 512 | 走 adapter `path_replace` 替换为各运行时工作目录 |
| `$OPC_KNOWLEDGE_PATH/` | 3 | 250, 265, 407 | **保持原样**——环境变量引用，所有运行时通用，带默认回退 `~/code/opc/opc-knowledge/` |

### 1.5 .opencode/agents/director.md 专属内容（不在 prompts/director.md 中）

1. **front matter**：`mode: primary`、`temperature: 0.3`、`steps: 30`、`tools`（read/edit/write/bash 全 deny，webfetch allow）、`permission`（bash/edit deny，webfetch allow，task 各角色 allow）、`skills` 列表（9 个 skill）、`version`、`last_optimized`、`optimization_log`。
2. **"会话启动自动检查"节**（第 41-52 行）：任务前查教训 + 会话引导（session-notes）+ 高危流程提醒——这是 opencode 专属的生命周期钩子逻辑，靠 prompt 正文顶部强制注入。

---

## 2. Director 去运行时化方案

### 2.1 核心原则

- **prompts/director.md 是唯一真相源**，包含 Director 的全部业务逻辑（定位、调度铁律、核心职责、流水线、决策权限等）。
- **运行时专属配置留在入口壳**（front matter / provider / permission / hook 声明），不进 prompts/。
- **生命周期钩子从 prompt 正文迁出**，走各运行时自己的 hook 机制；无 hook 机制的运行时用 prompt 顶部注入作为降级。

### 2.2 逐项映射表

| 内容项 | 当前位置 | 目标位置 | 处理方式 |
|---|---|---|---|
| Director 业务逻辑（定位/调度/职责/流水线/决策权限/红线等） | prompts/director.md + 各运行时手工副本 | prompts/director.md（唯一真相源） | 生成器从 prompts/ 生成到各运行时 agents/ 目录 |
| `{{WORK_PATH}}/` 路径 | prompts/director.md（5 处） | 各运行时工作目录 | adapter `path_replace.default` 替换（与其他 9 个角色一致） |
| `$OPC_KNOWLEDGE_PATH/` 路径 | prompts/director.md（3 处） | 保持原样 | 环境变量引用，所有运行时通用，不替换 |
| opencode front matter（mode/temperature/steps/tools/permission/skills） | .opencode/agents/director.md | .opencode/agents/director.md（入口壳） | 生成器保留现有 front matter（`front_matter.source: existing`），只替换正文 |
| opencode "会话启动自动检查"节 | .opencode/agents/director.md 正文顶部 | opencode hook 机制（或 prompt 顶部注入降级） | 从正文迁出，走 hook；详见第 3 节 |
| claude-code 调度机制说明（task tool 用法） | CLAUDE.md | CLAUDE.md 标记块外（手工维护） | 运行时专属调度说明，不进 prompts/ |
| claude-code 知识库目录表 | CLAUDE.md | CLAUDE.md 标记块外（手工维护） | 运行时专属配置 |
| claude-code 搜索工具映射表 | CLAUDE.md | CLAUDE.md 标记块外（手工维护） | 运行时专属配置 |
| pi/gemini/codex 入口文件 | 不存在 | 新建（标记块注入） | 从 prompts/director.md 生成核心内容块，运行时配置手工补 |

### 2.3 生成器行为变更

- 去掉 `SKIP_ROLES = ['director']`，Director 参与 `--all` 生成。
- Director 的生成路径：`prompts/director.md` → 路径替换 → 章节处理 → 注入 mirror 声明 → 输出到各运行时 `agents/director.md`（或 `.toml`）。
- front matter 保留现有（`source: existing`），只替换正文部分。
- opencode 的"会话启动自动检查"节从正文移除（迁到 hook），生成器不生成这一节。

---

## 3. Hook 机制设计（未来工作，不在 P1 范围内）

> **范围说明**：本节描述的 hook 机制设计是**未来独立工作（建议归入 P2）**，不在 P1（Director 单源化）范围内。P1 阶段 B 维持各运行时当前的会话自检机制不变（opencode 保留正文那节，claude-code 保留现有 UserPromptSubmit hook），不开发新 hook、不迁移现有 hook。本节仅作为未来 hook 统一化的设计参考，不阻塞 P1 收口。

### 3.1 统一生命周期钩子概念

定义一个统一的钩子概念：**`session-start`**（会话启动时触发，在 AI 开始处理第一个用户消息前执行）。

钩子内容统一为三项（克制原则，只加高频高危）：
1. **任务前查教训**：提取任务关键词，检索 lessons-index，命中则注入。
2. **会话引导**：读 session-notes.md 最后 20 行，了解上次干到哪、有什么坑。
3. **高危流程提醒**：涉及钱/用户可见变化需问创始人、QA 3 次失败上报。

### 3.2 各运行时挂载方式

| 运行时 | 原生 hook 机制 | 挂载方式 | 实现文件 | 类型 |
|---|---|---|---|---|
| **claude-code** | `UserPromptSubmit` hook（用户提交 prompt 后、AI 处理前调用） | `.claude/settings.json` 的 `hooks.UserPromptSubmit` 注册命令 | `.claude/hooks/lessons-prompt.py`（**已存在，作为参考样板**） | (a) 真 hook |
| **pi** | `before_agent_start` 扩展 hook（subagent 扩展提供） | pi 扩展系统注册，用户本地安装 | `~/.pi/agent/extensions/opc-lessons-hook.ts`（用户本地；仓库提供模板 `.pi/hooks/`） | (a) 真 hook |
| **opencode** | 插件系统生命周期事件（`session.created` 等） | 写一个 opencode 插件订阅 `session.created` 事件，注入上下文 | `.opencode/plugins/opc-session-hook.ts`（阶段 C 开发） | (b) 插件间接实现 |
| **gemini** | 原生 `SessionStart` hook（v0.26.0+ 默认启用） | `.gemini/settings.json` 的 `"hooks.SessionStart"` 注册命令 | `.gemini/hooks/session-start.js`（阶段 C 开发） | (a) 真 hook |
| **codex** | 原生 `SessionStart` hook（hooks 已 Stable，默认启用） | `.codex/config.toml` 的 `[[hooks.SessionStart]]` 内联配置，或 `hooks.json` | `.codex/hooks/session-start.py`（阶段 C 开发） | (a) 真 hook |

> **软兜底名单**：无。所有 5 个运行时都有真 hook 或插件机制，不需要 prompt 顶部注入软兜底。opencode 用插件系统间接实现真 hook（阶段 C 开发插件），开发完成前可临时保留 prompt 顶部注入作为过渡。

### 3.3 Claude Code 侧实现（已有参考）

`.claude/hooks/lessons-prompt.py` 已实现完整的 UserPromptSubmit hook：
- 从 stdin 读 JSON（含 prompt），返回 `hookSpecificOutput.additionalContext` 注入给模型。
- 内容：流程提醒 + session-notes 最后 20 行 + lessons-index 检索结果。
- 降级：任何一步失败都静默跳过，不影响正常流程。

**结论**：Claude Code 侧的 hook 已就绪，不需要额外开发。Director 纳入单源生成后，CLAUDE.md 中的"任务前查教训"等重复内容可以精简（因为 hook 已注入），但这是可选优化，不阻塞 P1。

### 3.4 opencode 侧实现（插件系统实现真 hook）

opencode 有官方插件系统（https://opencode.ai/docs/plugins/），支持订阅生命周期事件，包括 `session.created`（会话创建时触发）、`session.updated`、`session.deleted`、`session.idle` 等。

**方案**：写一个 opencode 插件 `.opencode/plugins/opc-session-hook.ts`，订阅 `session.created` 事件，在会话启动时执行：
1. 提取任务关键词，运行 lessons-index 检索
2. 读 session-notes.md 最后 20 行
3. 注入上下文给 Director

**过渡方案**：插件开发完成前，临时保留 prompt 顶部注入"会话启动自动检查"节（与当前行为一致），作为软兜底。插件开发完成后移除 prompt 注入，改用插件真 hook。

**插件开发在阶段 C 执行**，阶段 B 不阻塞。

### 3.5 pi/gemini/codex 侧实现

- **pi**：用户本地已有 `opc-lessons-hook.ts`，仓库提供模板文件 `.pi/hooks/opc-lessons-hook.ts.template`，用户安装时复制到本地扩展目录。
- **gemini**：原生 `SessionStart` hook（v0.26.0+ 默认启用），配置在 `.gemini/settings.json` 的 `"hooks.SessionStart"` 段。阶段 C 开发 `.gemini/hooks/session-start.js`，实现任务前查教训 + 会话引导 + 高危流程提醒，通过 `hookSpecificOutput.additionalContext` 注入。
- **codex**：原生 `SessionStart` hook（hooks 已 Stable，默认启用，无需 feature flag），配置在 `.codex/config.toml` 的 `[[hooks.SessionStart]]` 内联段（或 `hooks.json`）。阶段 C 开发 `.codex/hooks/session-start.py`，实现相同逻辑。

---

## 4. 入口文件"标记块注入"规范

### 4.1 标记语法

| 文件类型 | 开始标记 | 结束标记 |
|---|---|---|
| Markdown (`.md`) | `<!-- OPC:GENERATED:START -->` | `<!-- OPC:GENERATED:END -->` |
| TOML (`.toml`) | `# OPC:GENERATED:START` | `# OPC:GENERATED:END` |
| JSON (`.json`) | **不适用**（JSON 不支持注释） | — |

### 4.2 生成器行为

- 生成器读取入口文件，查找标记块。
- 如果标记块存在：只替换块内内容，块外内容保持不动。
- 如果标记块不存在：在文件末尾追加标记块（含生成内容），并警告用户"首次注入，请检查块位置是否合理"。
- 标记块内的内容从 `prompts/director.md` 生成（经过路径替换、章节处理等转换规则）。

### 4.3 JSON 文件的特殊处理

`opencode.json`、`.gemini/settings.json` 等 JSON 文件不支持注释，无法用标记块。

**方案**：
- opencode 的 Director 定义不在 opencode.json 里，而在 `.opencode/agents/director.md`（markdown，支持标记块）。opencode.json 只包含 provider 和 permission 配置，不需要标记块注入。
- gemini/codex 的配置文件如果是 JSON，且需要注入 Director 核心内容，则改用单独的生成文件（如 `.gemini/agents/director.md`），不修改 settings.json。

### 4.4 各运行时入口文件标记块规划

| 运行时 | 入口文件 | 类型 | 标记块内容 | 块外手工内容 |
|---|---|---|---|---|
| opencode | `.opencode/agents/director.md` | markdown | Director 核心业务逻辑（从 prompts/ 生成） | front matter（mode/temperature/tools/permission/skills）、"会话启动自动检查"节（生成器注入） |
| claude-code | `CLAUDE.md` | markdown | Director 核心业务逻辑摘要（从 prompts/ 生成，精简版） | 调度机制说明、知识库目录表、搜索工具映射表、成本意识 |
| pi | `.pi/SYSTEM.md` | markdown | Director 核心业务逻辑（从 prompts/ 生成） | pi 专属配置（dispatch_agent 用法、模型配置） |
| gemini | `.gemini/agents/director.md` | markdown | Director 核心业务逻辑（从 prompts/ 生成） | gemini 专属配置（subagents 用法、模型配置） |
| codex | `.codex/agents/director.toml` | toml | Director 核心业务逻辑（developer_instructions，从 prompts/ 生成） | model、model_reasoning_effort、approval_policy |

**注意**：opencode 的 Director 入口是 `.opencode/agents/director.md`（与其他子角色同目录），不是单独的入口文件。它的 front matter 是 opencode 专属配置，正文是 Director 业务逻辑。生成器只替换正文（标记块内），front matter 保持不动。

---

## 5. Adapter 配置扩展

### 5.1 director_entry 字段扩展

当前 `director_entry` 字段：
```yaml
director_entry:
  file: CLAUDE.md
  type: markdown
  source: manual
```

扩展为：
```yaml
director_entry:
  file: CLAUDE.md              # 入口文件路径
  type: markdown                # markdown / toml / json
  source: generated             # generated / manual
  managed_block: true           # 是否使用标记块注入
  template: |                   # 当 source=generated 时，标记块内的内容模板（可选，默认从 prompts/director.md 生成）
    {{director_body}}
```

### 5.2 各 adapter 具体值

#### opencode.yaml
```yaml
director_entry:
  file: .opencode/agents/director.md
  type: markdown
  source: generated
  managed_block: true
  # front matter 保留现有（source: existing），正文用标记块注入
  # "会话启动自动检查"节通过 sections.inject 自动注入（after_front_matter）
```

#### claude-code.yaml
```yaml
director_entry:
  file: CLAUDE.md
  type: markdown
  source: generated
  managed_block: true
  # CLAUDE.md 中 Director 核心逻辑用标记块注入
  # 块外保留：调度机制说明、知识库目录表、搜索工具映射表
```

#### pi.yaml
```yaml
director_entry:
  file: .pi/SYSTEM.md
  type: markdown
  source: generated
  managed_block: true
  # 新建 .pi/SYSTEM.md，标记块内为 Director 核心逻辑
  # 块外保留：pi 专属 dispatch_agent 用法、模型配置
```

#### gemini.yaml
```yaml
director_entry:
  file: .gemini/agents/director.md
  type: markdown
  source: generated
  managed_block: true
  # 新建 .gemini/agents/director.md，标记块内为 Director 核心逻辑
  # 块外保留：gemini 专属 subagents 用法、模型配置
```

#### codex.yaml
```yaml
director_entry:
  file: .codex/agents/director.toml
  type: toml
  source: generated
  managed_block: true
  # 新建 .codex/agents/director.toml
  # TOML 标记块：# OPC:GENERATED:START / # OPC:GENERATED:END
  # 标记块内为 developer_instructions 字段（从 prompts/director.md 生成）
  # 块外保留：name、description、model、model_reasoning_effort、approval_policy
```

### 5.3 path_replace 配置

Director 的 `{{WORK_PATH}}/` 路径替换与其他 9 个角色一致，使用各 adapter 的 `path_replace.default` 规则：

| 运行时 | `{{WORK_PATH}}/` 替换为 |
|---|---|
| opencode | `.opencode/work/` |
| claude-code | `$OPC_WORK_PATH/` |
| pi | `.pi/work/` |
| gemini | `.gemini/work/` |
| codex | `.codex/work/` |

`$OPC_KNOWLEDGE_PATH/` 不替换（环境变量引用，所有运行时通用）。

当前 opencode.yaml 中 `path_replace.overrides.director: []`（空数组，表示不替换）需要改为删除这个 override（让 director 走 default 规则）。

---

## 6. 风险与回滚

### 6.1 风险清单

| 风险 | 影响 | 概率 | 缓解措施 | 关注等级 |
|---|---|---|---|---|
| **opencode director 生成结果语义错误**（front matter 保留 + 正文标记块 + session 节 inject 三合一，最复杂路径） | **最高**（Director 是最重要角色，opencode 是主用运行时） | 中 | 阶段 B 对 opencode 单独多核一份基准（不能只靠 0-diff）；front matter 用 `source: existing` 确保不动；首次生成后逐行人工核对 | **🔴 最高关注** |
| Director 生成结果语义错误（其他 4 个运行时） | 高 | 中 | 阶段 B 对每个运行时手工核对一份基准 | 🟡 高 |
| opencode front matter 被生成器覆盖 | 高（mode/permission/skills 丢失会导致 Director 无法调度） | 低 | `front_matter.source: existing` 确保只替换正文，不动 front matter | 🟡 高 |
| CLAUDE.md 标记块外手工内容被误改 | 中（调度机制/知识库表丢失） | 低 | 生成器只替换标记块内，块外不动；首次注入后人工检查 | 🟢 中 |
| pi/gemini/codex 新建入口文件格式错误 | 中（新运行时无法加载 Director） | 中 | 每个新文件创建后做冒烟测试（确认能被运行时加载） | 🟢 中 |
| opencode 插件开发延迟导致会话启动自检失效 | 中（任务前查教训/会话引导丢失） | 中 | 插件开发完成前临时保留 prompt 顶部注入作为过渡；插件开发在阶段 C 执行 | 🟡 高 |
| 去掉 SKIP_ROLES 后 `--all` 生成意外修改 director | 中 | 低 | 首次生成后逐文件手工核对，确认无误再提交 | 🟢 中 |

### 6.2 回滚方案

所有改动都在 git 版本控制中，回滚方式：
1. **单文件回滚**：`git checkout <commit> -- <file>` 恢复特定文件。
2. **整次提交回滚**：`git revert <commit>` 撤销整个提交。
3. **阶段 B 回滚**：如果 Director 纳入生成器后出现问题，恢复 `SKIP_ROLES = ['director']` 即可回到当前状态（Director 手工维护）。
4. **阶段 C 回滚**：如果标记块注入出现问题，删除标记块、恢复手工维护的入口文件即可。

### 6.3 分阶段提交策略

**P1 范围（Director 单源化）：**

- **阶段 B**（核心层单源化）：一次提交，包含 prompts/director.md 去运行时化确认 + adapter path_replace 修复 + 去掉 SKIP_ROLES + 生成 5 运行时 director 文件 + 逐运行时手工核对基准。**不含 hook 开发**，会话自检机制维持各运行时现状。
- **阶段 C**（入口文件标记块注入）：分多次提交，每次一个运行时的入口文件标记块注入（CLAUDE.md 红线+routing 标记块、opencode director 正文标记块等），便于逐运行时验证和回滚。**不含 hook 迁移**。

**P2 范围（hook 统一化，独立立项，不阻塞 P1）：**

- **hook 迁移**：gemini/codex 新写 SessionStart hook 脚本、opencode 写插件订阅 session.created、pi 出 hook 模板、统一行为规格。这是独立的大工程，跨 4 运行时新代码，不绑定 P1 收口。
- **Codex hooks 配置最终确认**：在真正做 hook 那一步再确认 hooks 键/Stable/项目级 .codex 是否生效（CLI 迭代快），本次单源化不依赖它。

---

## 7. 待确认问题

### P1 范围内（阶段 B/C 需要确认）

1. **opencode director 生成基准核对方式**：opencode 是最复杂路径（front matter 保留 + 正文标记块 + session 节 inject 三合一），阶段 B 需要单独多核一份基准。具体核对哪些字段？建议：front matter 完整保留、正文路径替换正确、session 节不丢失、与当前手工版语义一致。
2. **CLAUDE.md 标记块首次注入位置**：CLAUDE.md 保持精简版，只注入"红线"和"routing 指向"。标记块放在 CLAUDE.md 的哪个位置？建议放在"身份标识"之后、"调度机制说明"之前。

### P2 范围内（hook 统一化，独立立项，不阻塞 P1）

3. ~~opencode 插件开发优先级~~ → 移入 P2 hook 统一化项目。opencode 用插件系统实现真 hook，插件开发在 P2 执行。P1 阶段 B 维持 opencode 正文那节不变。
4. ~~gemini/codex hook 脚本开发~~ → 移入 P2 hook 统一化项目。gemini 和 codex 都有原生 SessionStart hook，但需要开发对应的 hook 脚本。P1 不开发。
5. ~~Codex hooks 配置最终确认~~ → 移入 P2。在真正做 hook 那一步再确认 hooks 键/Stable/项目级 .codex 是否生效（CLI 迭代快），本次单源化不依赖它。
6. ~~gemini/codex 是否有原生 session-start hook？~~ **已确认**：gemini v0.26.0+ 原生 hooks（含 SessionStart）；codex hooks 已 Stable（默认启用，含 SessionStart）。详见 §9.1。
7. ~~opencode 是否有 hook 机制？~~ **已确认**：opencode 有官方插件系统，支持 `session.created` 等生命周期事件，可写插件实现真 hook。详见 §9.1。

---

## 8. 下一步

阶段 A 设计文档完成，待 review。

**P1（Director 单源化）：**

review 通过后进入：
- **阶段 B**（核心层单源化，**不含 hook 开发**）：prompts/director.md 去运行时化确认 + adapter path_replace 修复 + 去掉 SKIP_ROLES + 生成 5 运行时 director 文件 + 逐运行时手工核对基准（opencode 单独多核）。会话自检机制维持各运行时现状（opencode 保留正文那节，claude-code 保留现有 UserPromptSubmit hook）。
- **阶段 C**（入口文件标记块注入，**不含 hook 迁移**）：CLAUDE.md 红线+routing 标记块、opencode director 正文标记块、pi/gemini/codex 入口文件标记块。

**P2（hook 统一化，独立立项，不阻塞 P1）：**

- hook 迁移：gemini/codex 新写 SessionStart hook 脚本、opencode 写插件订阅 session.created、pi 出 hook 模板、统一行为规格。
- Codex hooks 配置最终确认。

---

## 9. 补充裁定（2026-08-28 更新）

### 9.1 Q1：Gemini CLI / Codex CLI / opencode 生命周期 hook 查证

> 查证原则：以官方文档或官方仓库为准，不采信个人博客二手说法。区分三种情况：(a) 真·生命周期 hook（确定性触发）；(b) 只有 extension/plugin/自定义命令，能间接实现；(c) 只能靠 prompt/系统指令（软兜底）。

#### Gemini CLI — 更正：(a) 真·生命周期 hook

- **查证来源**：
  - Google 官方公告《Control the loop with Hooks & extend expertise with Agent Skills》（GitHub Discussions #17790，2026-01-28，v0.26.0 release）：明写 "Hooks are enabled by default in Gemini CLI as of v0.26.0+"。
  - 官方仓库 `docs/hooks/` 目录：`index.md`、`reference.md`、`writing-hooks.md`、`best-practices.md`（fetch 于 2026-08-28，之前漏看了 docs/ 子目录）。
  - 官方文档站：https://geminicli.com/docs/hooks/writing-hooks/、https://geminicli.com/docs/hooks/reference/
- **版本**：v0.26.0+（2026-01-28 起默认启用）；当前最新 0.52.0-nightly（2026-07-15）
- **结论**：**(a) 真·生命周期 hook（确定性触发）**
- **支持的事件**（官方 reference.md）：
  - `SessionStart`：会话开始时触发（startup / resume / clear），可注入 `hookSpecificOutput.additionalContext`
  - `SessionEnd`：会话结束时
  - `BeforeAgent`：用户提交 prompt 后、AI 规划前
  - `AfterAgent`：agent 循环结束时
  - `BeforeModel` / `AfterModel`：LLM 请求前后
  - `BeforeTool` / `AfterTool`：工具调用前后
  - `BeforeToolSelection`：工具选择前
- **配置方式**：`.gemini/settings.json` 的 `"hooks"` 段，按事件名注册 matcher 和 command hook。
- **处理方式**：Gemini CLI 的 Director 用原生 `SessionStart` hook 实现会话启动自检，配置在 `.gemini/settings.json`，hook 脚本 `.gemini/hooks/session-start.js`。

#### Codex CLI — 坐实配置：(a) 真·生命周期 hook

- **查证来源**：
  - 官方文档：https://developers.openai.com/codex/hooks（fetch 于 2026-08-28）
  - 官方配置文档：https://developers.openai.com/codex/config-basic、https://developers.openai.com/codex/config-reference、https://developers.openai.com/codex/config-advanced
- **版本**：0.150.1（最新 release，2026-08-27）
- **结论**：**(a) 真·生命周期 hook（确定性触发）**
- **feature flag**（坐实）：
  - 配置 key：`hooks`（**不是** `codex_hooks`）
  - 默认值：`true`（**默认已启用**，不需要手动开启）
  - Maturity：**Stable**（稳定，非实验性）
  - `codex_hooks` 是 **deprecated alias**（仍可用但已废弃）
  - 来源：官方 config-basic.md 明确写 "hooks | true | Stable | Enable lifecycle hooks from hooks.json or inline [hooks]"
- **配置位置**（坐实）：两种方式都支持
  1. **`hooks.json` 文件**：放在活动配置层旁边（如 `~/.codex/hooks.json` 或项目级 `.codex/hooks.json`）
  2. **`config.toml` 内联 `[hooks]` 段**：用 `[[hooks.SessionStart]]` 等数组语法内联配置，与 hooks.json 使用相同的事件 schema
  - 来源：官方 config-reference.md 明确写 "hooks | table | Lifecycle hooks configured inline in config.toml. Uses the same event schema as hooks.json"
- **支持的事件**（官方 config-reference.md）：`PreToolUse`、`PermissionRequest`、`PostToolUse`、`PreCompact`、`PostCompact`、`SessionStart`、`SubagentStart`、`SubagentStop`、`UserPromptSubmit`、`Stop`
- **处理方式**：Codex CLI 的 Director 用原生 `SessionStart` hook，配置在 `.codex/config.toml` 的 `[[hooks.SessionStart]]` 内联段（项目级配置），hook 脚本 `.codex/hooks/session-start.py`。不需要 feature flag（默认已启用 Stable）。

#### opencode — 查证结果：(b) 插件系统间接实现

- **查证来源**：
  - 官方文档：https://opencode.ai/docs/plugins/（fetch 于 2026-08-28）
  - 官方文档（中文版）：https://opencode.ai/docs/zh-cn/plugins/
- **版本**：当前最新版（opencode 持续更新，插件系统为官方核心功能）
- **结论**：**(b) 只有 extension/plugin/自定义命令，能间接实现**
- **依据**：
  - opencode 有官方插件系统，插件可以订阅全生命周期事件。
  - 支持的**会话事件**（官方文档）：`session.created`、`session.compacted`、`session.deleted`、`session.diff`、`session.error`、`session.idle`、`session.status`、`session.updated`
  - 其他事件：命令事件（`command.executed`）、文件事件、消息事件（`message.updated`）、权限事件（`permission.asked` / `permission.replied`）、服务器事件（`server.connected`）
  - 插件用 TypeScript 编写，通过 `definePlugin` API 订阅事件，在事件回调中执行逻辑（如注入上下文、运行脚本）。
- **与真 hook 的区别**：opencode 没有像 Claude Code/Codex/Gemini 那样的"在配置文件里声明一个 command 就自动挂载"的内置 hook 配置。需要写一个完整的 TypeScript 插件，通过插件 API 订阅事件。但效果等价（确定性触发，不依赖模型自愿遵守）。
- **处理方式**：写一个 opencode 插件 `.opencode/plugins/opc-session-hook.ts`，订阅 `session.created` 事件，在会话启动时执行任务前查教训 + 会话引导 + 高危流程提醒，通过插件 API 注入上下文。插件开发在阶段 C 执行。
- **过渡方案**：插件开发完成前，临时保留 prompt 顶部注入"会话启动自动检查"节作为软兜底；插件开发完成后移除 prompt 注入。

### 9.2 Q2：pi hook 模板纳入仓库

- **裁定**：pi hook 模板纳入仓库，放模板文件 + 版本控制，不要只留在本地 `~/.pi`。
- **实现方式**：
  - 仓库新增 `.pi/hooks/opc-lessons-hook.ts.template`（模板文件，含路径占位符和安装说明）。
  - 用户安装时复制到 `~/.pi/agent/extensions/opc-lessons-hook.ts` 并替换路径占位符。
  - adapter `pi.yaml` 的 `file_protection` 和 `detect` 配置中补充 hook 模板路径。
- **理由**：pi 的 hook 是 OPC 系统的核心组件（任务前查教训 + 会话引导），不能只依赖用户本地文件，否则新用户克隆仓库后无法获得该功能。

### 9.3 Q3：CLAUDE.md 保持精简版

- **裁定**：CLAUDE.md 保持精简版，不注入完整 Director 逻辑；只对"必须同步的部分"做标记块，其余手工。
- **必须同步的部分**（标记块内，由生成器从 prompts/director.md 生成）：
  1. **红线**（`prompts/director.md` 的"红线"节）—— 最高优先级规则，必须与 prompts/ 保持一致。
  2. **routing 指向**—— 归属表引用 `routing.yaml` 的说明和 Director 豁免项，必须与 prompts/ 保持一致。
- **其余手工维护**（标记块外）：
  - 调度机制说明（Claude Code task tool 用法）
  - 知识库目录表
  - 搜索工具映射表（Claude Code 运行时专属）
  - 成本意识
  - 身份标识
- **理由**：CLAUDE.md 是 Claude Code 的系统提示词入口，完整 Director 逻辑（~570 行）注入会导致 CLAUDE.md 过于臃肿，且 Claude Code 有 UserPromptSubmit hook 已经注入了会话启动自检，不需要在系统提示词中重复。

### 9.4 Q4：opencode 自检节 vs CC hook 统一行为规格

- **裁定**：统一"行为规格"，不统一"实现"。
- **行为规格**（收进 `prompts/director.md` 作唯一描述）：
  > **会话启动时**：Director 必须依次执行——(1) 查未完成任务（检查 scripts/state.json 和已完成阶段产出）；(2) 查教训（提取任务关键词检索 lessons-index）；(3) 读 session-notes.md 最后 20 行（会话引导）。
- **P1 阶段 B 现状**（维持不变，不开发新 hook、不迁移现有 hook）：
  - **opencode**：保留正文"会话启动自动检查"节（当前手工写在 `.opencode/agents/director.md` 里，阶段 B 纳入生成器后由生成器保留这一节）。
  - **claude-code**：保留现有 `UserPromptSubmit` hook（`.claude/hooks/lessons-prompt.py`，已存在）。
  - **pi/gemini/codex**：当前无会话自检机制（入口文件尚未建立），阶段 B 不添加。
- **P2 未来工作**（hook 统一化，独立立项，不阻塞 P1）：
  - **opencode**：插件系统订阅 `session.created` 事件（开发 `.opencode/plugins/opc-session-hook.ts`），完成后移除正文那节。
  - **pi**：出 `before_agent_start` 扩展 hook 模板。
  - **gemini**：原生 `SessionStart` hook（`.gemini/settings.json` + `.gemini/hooks/session-start.js`）。
  - **codex**：原生 `SessionStart` hook（`.codex/config.toml` + `.codex/hooks/session-start.py`）。
- **理由**：行为规格统一保证 5 个运行时的 Director 在"会话启动时做什么"上语义一致；实现方式允许不同是因为各运行时的 hook 机制不同。P1 只做单源化，不碰 hook，避免把跨 4 运行时的新代码捆进来拖住单源落地、放大风险。

### 9.5 A：prompt 顶部注入 = best-effort 软 hook（P2 参考，不在 P1 范围内）

- **明确定义**：prompt 顶部注入是 **best-effort 软 hook**，可靠性低于真 hook。
- **P1 现状**：opencode 的"会话启动自动检查"节就是 prompt 顶部注入（软 hook），P1 阶段 B 维持不变。claude-code 用真 hook（UserPromptSubmit）。pi/gemini/codex 当前无会话自检。
- **P2 未来工作**：opencode 插件开发完成后，软兜底完全移除，所有 5 个运行时统一用真 hook/插件。gemini/codex 新写 hook 脚本，pi 出模板。
- **可靠性差异**（P2 参考）：
  - **真 hook**（claude-code UserPromptSubmit、pi before_agent_start、gemini SessionStart、codex SessionStart）：由运行时确定性触发。
  - **插件间接实现**（opencode 插件订阅 `session.created`）：由 opencode 插件系统确定性触发，效果等价于真 hook。
  - **软 hook**（prompt 顶部注入）：靠模型阅读后自愿执行，可能忽略或执行不完整。
- **对"中断恢复"的影响**（P2 参考）：opencode 过渡期间用软兜底，中断恢复可靠性低于真 hook，但可接受（软兜底写在 prompt 最顶部，模型阅读概率高；中断恢复是辅助功能；这是过渡方案）。

### 9.6 B：Director 生成模型因运行时而异

- **明确定义**：Director 的生成模型因运行时分为两类，验收标准据此分两套。

#### 第一类：可生成的 Director 文件（opencode / pi / gemini / codex）

- **生成方式**：`prompts/director.md` → 生成器 → `.<runtime>/agents/director.md`（或 `.toml`）
- **运行时**：opencode（`.opencode/agents/director.md`）、pi（`.pi/agents/director.md`）、gemini（`.gemini/agents/director.md`）、codex（`.codex/agents/director.toml`）
- **验收标准**：
  1. **0-diff 生成校验**：`generate-agents.py --runtime=<runtime> --role=director` 生成后与仓库中已提交的文件 0 差异。
  2. **语义正确性核对**：Director 太关键，不能只靠 0-diff。首次纳入生成时，对每个运行时手工核对一份基准，确认生成结果语义正确（路径替换正确、front matter 保留、专属内容不丢失）。
  3. **CI 门禁**：CI 的 "Verify generated agents are in sync with prompts/" 步骤扩展到包含 director。

#### 第二类：入口文件本身（claude-code）

- **生成方式**：CLAUDE.md 是 Claude Code 的系统提示词入口，**不是生成文件**。Director 核心逻辑通过标记块注入到 CLAUDE.md 的特定位置，其余内容手工维护。
- **运行时**：claude-code（`CLAUDE.md`）
- **验收标准**：
  1. **标记块 0-diff 校验**：生成器重新生成 CLAUDE.md 标记块内内容后，与仓库中已提交的标记块内容 0 差异。
  2. **标记块外内容不动**：生成器只替换 `<!-- OPC:GENERATED:START -->` / `END` 之间的内容，块外内容（调度机制说明、知识库表、搜索工具映射等）保持不变。
  3. **CI 门禁**：CI 新增"入口文件标记块重生成 0-diff"校验步骤。
  4. **手工核对**：首次注入标记块时，人工确认标记块位置合理、块内内容与 prompts/director.md 的红线和 routing 指向一致。

#### 两套验收标准的差异

| 维度 | 第一类（opencode/pi/gemini/codex） | 第二类（claude-code） |
|---|---|---|
| 生成对象 | `.<runtime>/agents/director.md`（完整文件） | `CLAUDE.md` 标记块内内容（部分文件） |
| 0-diff 范围 | 完整文件 | 仅标记块内 |
| 标记块外 | 不适用（完整文件生成） | 必须保持不动 |
| CI 校验 | 复用现有 agents 同步校验 | 新增入口文件标记块校验 |
| front matter | 保留现有（source: existing） | 不适用（CLAUDE.md 无 front matter） |
