# OPC Agents 合并计划 — 对比分析报告

> author: Director + Dev
> date: 2025-06-22
> status: draft
> related: opc-agents (OpenCode), opc-agents-claude (Claude Code)

---

## 一、项目概览

| 维度 | opc-agents (OpenCode) | opc-agents-claude (Claude Code) |
|------|----------------------|-------------------------------|
| Agent 文件位置 | `.opencode/agents/` (9个) | `prompts/` (9个，无 director) |
| Agent 文件总大小 | 109 KB | 153 KB (**+40%**) |
| CLAUDE.md 性质 | 系统参考文档 (4KB) | Director 系统 prompt (9KB) |
| Director prompt | `director.md` (22KB，含 YAML front matter) | 直接内嵌在 CLAUDE.md 中 |
| 独有 Agent | 无 | `agent-manager.md` (16KB) |
| opencode.json | ✅ 有 (已修复 API key 泄露) | ❌ 无 |
| Skills 目录 | `.opencode/skills/` (200+) | `.opencode/skills/` (200+) — 几乎相同 |

---

## 二、Agent Prompt 逐文件对比

### 结论：**Claude Code 版 (B) 普遍更详细，且不含任何运行时特定引用**

| Agent | A大小 (OpenCode) | B大小 (Claude) | 判定 | 备注 |
|-------|-----------------|---------------|------|------|
| advisor | 14.4 KB | 16.4 KB | **保留 B** | B 有完整认知偏差表+决策日志模板 |
| dev | 12.7 KB | 23.4 KB | **保留 B** | B 有完整的 API/DB/前端/重构方法论；A 有"自用模式"章节应合并 |
| finance | 6.3 KB | 13.8 KB | **保留 B** | B 有完整定价模型/ROI/财务指标体系/三大报告模板 |
| growth | 13.2 KB | 19.8 KB | **保留 B** | B 有完整 SEO/社交媒体/A-B测试/漏斗分析/指标仪表盘 |
| guardian | 10.4 KB | 19.8 KB | **保留 B** | B 有 OWASP Top 10/STRIDE/技术债分类/性能分析；A 有"自用模式"应合并 |
| product | 11.5 KB | 10.9 KB | **A≈B** | 核心内容几乎一致，差异仅 front matter 和路径前缀 |
| qa | 7.9 KB | 19.5 KB | **保留 B** | B 有完整测试金字塔/测试设计技术/自动化框架/质量度量/门禁设计 |
| ui-ux | 10.6 KB | 14.0 KB | **保留 B + A 边界** | B 有完整设计令牌/颜色/字体/WCAG；A 有更强的 Dev 边界（"不写任何代码"） |

### 关键发现

1. **B 版本所有 prompt 均无运行时特定引用** — 未找到 "Claude Code"、"Agent tool"、"subagent_type" 等词。B 版本使用 `work/` 路径，比 A 的 `.opencode/work/` 更通用。

2. **A 版本被主动裁剪过** — 优化日志显示 finance 删减 66+93+65+115 行，qa 删减 116+100+150+30 行。B 保留了完整的参考章节。

3. **A 版本有 YAML front matter**（mode/temperature/steps/tools/permission/skills）— 这是 OpenCode 加载 Agent 所需的运行时配置。

4. **应从 A 合并入 B 的内容**：
   - dev 的 `## 自用模式` 部分
   - guardian 的 `## 自用模式` 部分
   - ui-ux 的 Dev 边界部分（"不写任何代码"）和"自用设计原则"
   - advisor 的 `## 克制原则` 部分

### 独有 Agent

| Agent | 所属 | 大小 | 处理方式 |
|-------|------|------|----------|
| director.md | A (OpenCode) | 22.4 KB | 提取核心职责到 `prompts/director.md`；运行时配置保留在 `.opencode/agents/director.md` |
| agent-manager.md | B (Claude) | 15.7 KB | 直接加入 `prompts/agent-manager.md` |

---

## 三、CLAUDE.md 对比

| 方面 | A (OpenCode) | B (Claude Code) |
|------|-------------|-----------------|
| 大小 | 4.1 KB / 123 行 | 9.1 KB / 226 行 |
| 角色 | 系统参考文档 | Director 的 system prompt |
| 独有内容 | Tab/@提及交互方式、质量门禁 | 调度铁律、操作归属表、自检清单、决策权限、汇报格式 |

**合并策略**：CLAUDE.md = B 版本（Director system prompt），吸收 A 中的系统规则（知识库、搜索优先级、中断恢复、产出规范等）。

---

## 四、Scripts 对比

### quality-gate.sh
| 方面 | A (OpenCode) | B (Claude Code) |
|------|-------------|-----------------|
| 目标目录 | `.opencode/agents/` | `prompts/` |
| Front matter 检查 | ✅ 验证 description/mode/model/temperature/steps | ❌ 改为检查关键章节 |
| Agent 引用检查 | 对照 `director.md` | 对照 `CLAUDE.md` |
| Skill 引用检查 | ✅ 验证 `.opencode/skills/` | ❌ 无 |

**合并策略**：以 A 为基础，统一路径指向 `prompts/`，同时保留对 `.opencode/agents/` 的检查。

### state-manager.py
两版本 **完全相同** (7874 bytes)。保留。

### auto-check.sh
两版本 **完全相同** (1154 bytes)。保留。

---

## 五、Templates 对比

两边的 `templates/project-context-template.md` 完全相同 (699 bytes)。保留。

---

## 六、.env.example 对比

| 变量 | A | B |
|------|---|---|
| SENSENOVA_API_KEY | ✅ | ❌ |
| OPC_KNOWLEDGE_PATH | ✅ | ✅ |

已合并为 A 版本 + 双运行时说明。

---

## 七、执行步骤摘要

1. ✅ **安全修复** — opencode.json API key 已移除
2. 📋 **统一 prompts/** — 以 B 为主体，合并 A 精华 → 10 个文件
3. 📋 **双入口** — CLAUDE.md (Director prompt) + opencode.json + .opencode/agents/
4. 📋 **合并 scripts** — 统一路径引用
5. 📋 **更新 README** — 双运行时
6. 📋 **CI + 元数据**
7. 📋 **Archive 旧仓库**
