# 规则变更日志（RULES CHANGELOG）

记录 CLAUDE.md / prompts/ / .opencode/ / routing.yaml / scripts/ 等规则文件的变更。改动规则后在此追加一条，便于追溯"为什么这条规则长这样"。

格式：`{日期} {文件} — {变更}（{原因}）`

## 2026-08-28

- README.md — 已知决策表更新：废弃「不引入 CI」三条旧决策，改为记录已落地的 GitHub Actions CI（quality-gate.yml/ci.yml）+ pre-commit 门禁（文档与仓库实际状态脱节，核对时发现）
- README.md — 项目结构 scripts/ 补 sync-opencode.sh 条目（漏列）

## 2026-08-16

- CLAUDE.md — 瘦身 357→303 行（任务分级/流水线/Advisor 介入/中断恢复/汇报格式/成本意识压缩为一行+指向 director.md）
- CLAUDE.md — 触发词摘要与 routing.yaml bug-triage 对齐（bug→QA 排查→Dev 修复）
- CLAUDE.md — 知识库目录表补全 12-小红书/13-推广素材/14-项目归档/15-草稿箱
- CLAUDE.md — 打回自动沉淀教训节补充（与 opencode 版同步）
- prompts/director.md — 反馈信号节补全、打回沉淀节同步（双环境一致性修复）
- .opencode/agents/director.md — 反馈信号节补上、任务前查教训改为委托 Dev
- routing.yaml — ui-ux-designer→ux-designer、edit-prompt 注释改章节名引用、新增 edit-config 路由
- routing.yaml — 全局 skill 依赖注释（anysearch 等）
- scripts/quality-gate.sh — secret 扫描改 git tracked 口径（修 .env 误报）
- scripts/quality-gate.sh — 4.8 内容级漂移检查（锚点 grep→内容级 diff+红线专项）
- scripts/quality-gate.sh — 4.8 front matter 边界修复（只认首行 ---）
- scripts/quality-gate.sh — 4b AgentManager 驼峰匹配（awk 转换）
- scripts/sync-opencode.sh — 新增：双环境核心章节单向同步（CORE_SECTIONS 驱动）
- scripts/sync-opencode.sh — agent-manager 补上缺失红线（不把 Agent prompt 改到无法运行）
- .opencode/skills/lessons-index/search.sh — 状态过滤（draft 草稿不参与检索）
- .opencode/agents/dev.md / guardian.md — 移除 health skill 死引用
- .opencode/agents/agent-manager.md — 红线同步（sync 脚本自动）
- .gitignore — work/ 产出目录、scripts/state.json.bak、pnpm 误建
- README.md — 环境变量引导修正（SENSENOVA→JENSEN003/SOULJIAN03）、能力边界有意差异说明
- .env.example — 补两个必填 key 占位、SENSENOVA 标注历史遗留
- .github/workflows/ci.yml — secret 扫描扩展为全仓库 git tracked 文件
- .claude/settings.json — 无改动（既有 PreToolUse 保护保留）
- .git/hooks/pre-commit — 新增：规则文件改动自动跑 quality-gate（缺口2）
- ~/.pi/agent/extensions/opc-lessons-hook.ts — 新增：任务前查教训 + 高危流程提醒（hook）
