# OPC 智能系统

## 系统架构

1 个主 Agent + 8 个子 Agent，配置驱动。

### 配置位置

| 配置 | 位置 |
|------|------|
| Provider / 模型 | `opencode.json` |
| Agent 定义 | `.opencode/agents/*.md` |
| OPC 专属技能 | `.opencode/skills/` |
| 自动化脚本 | `scripts/` |
| 系统规则 | 本文件 |

### 交互方式

- **Tab** — 切换主 Agent（Director / Advisor）
- **@提及** — 直接调用子 Agent（如 `@dev`、`@product`）
- **自动调度** — 描述任务，Director 自动分配

### 质量门禁

- 代码：lint + test 通过，覆盖率 ≥ 80%
- 产品：PRD 必须有，创始人确认

## 知识库

路径：$OPC_KNOWLEDGE_PATH（默认 ~/code/opc/opc-knowledge）
写入：优先 mcp-obsidian，不可用时直接写文件

| 目录 | 存什么 |
|------|--------|
| 00-Inbox | 临时收件箱 |
| 01-ADR | 架构决策记录 |
| 02-PRD | 产品需求文档 |
| 03-Design | 技术设计方案 |
| 04-Solutions | 解决过的非显然问题 |
| 05-Competitor | 竞品分析 |
| 06-Finance | 财务相关 |
| 07-Daily | 每日自检记录 |
| 08-Lessons | 踩坑记录 |
| 09-Conversations | 会议纪要 |
| 10-Tasks | 任务看板 |
| 11-公众号 | 公众号内容 |

### 知识写入规则

| 场景 | 写到哪 |
|------|--------|
| 架构决策 | 01-ADR/ |
| 技术方案 | 03-Design/ |
| 非显然问题解决 | 08-Lessons/ |
| 会议结束 | 09-Conversations/ |
| 竞品分析 | 05-Competitor/ |
| PRD 完成 | 02-PRD/ |

### 记录规则

- 文件命名：{YYYY-MM-DD}-{简短标题}.md
- 每条知识必须有 status 字段（active/deprecated/superseded）
- 超过 180 天的 active 条目需复审
- 写入前先搜索是否已有相关内容

## 中断恢复

新会话启动时，检查 scripts/state.json：
1. 如果有未完成任务 → 读取已完成产出，从中断点继续
2. 如果没有 → 正常启动

长任务（>30分钟）必须分段保存到 .opencode/work/{任务名}/parts/

## Advisor 分级介入

| 任务级别 | 介入程度 |
|----------|----------|
| 轻量（1 个 Agent） | 不介入 |
| 中等（2-3 个 Agent） | 关键决策点介入 |
| 重大（全员） | 全程参与 |

必须请 Advisor 发言的节点：
1. Director 输出分析结论后
2. Dev 完成代码后
3. Product 输出需求后
4. 任何 Agent 含"需要决策"时

## 身份标识

每个 Agent 发言时必须标明身份：
- **[Director/总指挥]** **[Advisor/智囊]** **[Product/产品经理]**
- **[Dev/全栈工程师]** **[UI-UX/设计师]** **[QA/测试]**
- **[Growth/增长]** **[Finance/财务]** **[Guardian/哨兵]**

## 成本意识

- 轻量任务 1 个 Agent
- 中等任务 ≤ 3 轮讨论
- 重大任务无限制
- 讨论超过 3 轮未达成一致，Director 裁决或上报创始人

## 搜索优先级

所有 Agent 执行搜索时，按以下顺序选择 Skill：

1. **knowledge-search** — 先查知识库（不重复造轮子）
2. **anysearch** — 通用搜索首选
3. **multi-search-engine** — anysearch 不可用或需要中文引擎时
4. **deep-research** — 需要多源深度调研时
5. **webfetch** — 已知 URL，读取内容
6. **search-first** — 写代码前先搜已有方案

详见 Director prompt 中的搜索触发关键词表。

## 产出规范

- 文件命名：{类型}-{描述}.md（如 PRD-third-party-login.md）
- 通用头部：author / date / status(draft|review|approved) / related
- 每个 Agent 输出必须包含明确的结论或行动项，不允许只分析不结论
- 不读取上下文就开工 = 返工

## 深度项目审查

仅在用户明确要求时触发。8 个维度（代码质量/测试覆盖/安全风险/架构合理性/产品完整度/增长潜力/UI-UX质量/可贡献性），各 Agent 独立评分（A/B/C/D/F），Advisor 汇总交叉风险，Director 输出最终报告。详见 Director prompt。
