# 规则变更日志（RULES CHANGELOG）

记录 CLAUDE.md / prompts/ / .opencode/ / routing.yaml / scripts/ 等规则文件的变更。改动规则后在此追加一条，便于追溯"为什么这条规则长这样"。

格式：`{日期} {文件} — {变更}（{原因}）`

## 2026-08-28

- README.md — 已知决策表更新：废弃「不引入 CI」三条旧决策，改为记录已落地的 GitHub Actions CI（quality-gate.yml/ci.yml）+ pre-commit 门禁（文档与仓库实际状态脱节，核对时发现）
- README.md — 项目结构 scripts/ 补 sync-opencode.sh 条目（漏列）
- scripts/quality-gate.sh — 归一化 sed 正则改双引号转义 \\\$（规避 CI ShellCheck SC2016，行为不变）
- scripts/sync-opencode.sh — local tmp 声明与赋值拆行（修复 CI ShellCheck SC2155）
- scripts/quality-gate.sh — 门禁清零：prompts/ 无 front matter 由警告降级为 ℹ️（Claude Code 共享版按设计不含 front matter，原检查与设计矛盾）；skill 缺失降级为 ℹ️（routing.yaml 已声明预期、按降级规则处理不阻塞）。结果 0 errors 0 warnings
- git — 删除两个已合并 stale 分支：docs/annotate-cc-skill-deadlinks、feat/memory-cmd-log
- tests/ — 新增 pytest 单元测试：state-manager.py 全覆盖（状态读写/备份恢复/文件锁/检查点/任务归档/CLI，33 用例）+ routing.yaml schema 校验（结构/agent 引用/ID 唯一/全 Agent 可达，9 用例），共 42 用例
- .github/workflows/ci.yml — 新增 Run unit tests 步骤（pip install pytest pyyaml + pytest tests/）
- .gitignore — 排除 tests/__pycache__ 与 .pytest_cache
- scripts/gen-opencode-agent.sh — 删除：已被 scripts/generate-agents.py --runtime=opencode 完全替代（经逐行 diff 确认等价，且旧脚本因不认识 {{WORK_PATH}} 占位符已产出坏文件），且触发 ShellCheck SC2016 导致 CI 失败
- scripts/generate-agents.py — TOML 序列化重构：废弃手写 f-string + 错误 literal string 转义（body.replace("'''", "\\'\\'\\'")，literal string 不支持转义，会静默篡改含 ''' 的正文），改用 tomli-w 库做健壮序列化；抽 serialize_toml_agent() 独立函数便于单元测试
- 依赖 — 新增 tomli-w（TOML 序列化库，轻量只写）；ci.yml 三处 pip install 同步添加
- tests/test_toml_serialization.py — 新增 12 用例：11 个对抗性正文 round-trip（含 '''/\\/\"/end'''/空正文/Unicode 等，断言 tomllib 解析后与原文逐字一致）+ 全量 .codex/agents/*.toml 可解析校验
- adapters/codex.yaml + scripts/generate-agents.py — 删除 codex agent 级 model / model_reasoning_effort 硬编码（原写死 gpt-4o / medium）。模型属环境关切，由用户自己的 ~/.codex/config.toml 全局配置决定（ConfigToml.model 是 Option，缺省回落全局）；硬编码会把私有模型名/本地代理语义泄进公开仓库。经 codex 官方源码核查：.codex/agents/*.toml 格式正确（name/description/developer_instructions 必需，model 可选），developer_instructions 对 standalone 文件是必需字段缺了会报错被忽略。生成的 10 个 .toml 仅移除这两行，其余不变
- prompts/*.md + scripts/generate-agents.py — description 单源化：给 10 个 prompts/ 文件加 front matter（只含 description），codex 的 description 改为从 prompts/ front matter 提取，不再从 .opencode/agents/ 捞，消除跨运行时耦合。opencode 继续从现有文件提取完整 front matter（含 mode/temperature/tools 等），其他运行时 strip front matter 后正文不变 → 5 运行时 × 10 角色 0-diff 保持
- tests/test_adapter_schema.py — 新增 23 用例：adapters/*.yaml 结构校验（生成器命脉，字段拼错会静默生成错产物）。正向：5 个现有 adapter 全部通过 + runtime 字段与文件名一致；反向：缺必需键/未知顶层键/类型错误/agent_format 缺键/非法 type/front_matter 缺 enabled 均被拒。纯 Python 实现，不引 jsonschema 依赖，参照 routing.yaml schema 校验写法
- README.md — 全面同步为五运行时单源架构现状：标题改为"五运行时单源架构"，快速开始补五运行时表格，新增"五运行时单源架构"章节（核心原则/生成流程/各运行时格式/CLAUDE.md 标记块机制），项目结构补 adapters/、tests/、五运行时目录、generate-agents.py、.githooks/，已知决策表加五运行时单源架构/Director 单源化/description 单源化三条，"双运行时文件保护"改为"多运行时文件保护"。删掉所有"双运行时/两版"旧措辞

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
