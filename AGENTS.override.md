# OPC — Pi 运行时上下文覆盖

本文件（仓库根目录的 `AGENTS.override.md`）优先于同目录的 `AGENTS.md` / `CLAUDE.md`——
Pi 按候选顺序取第一个命中文件，因此**不会**把 Claude Code 措辞
的 CLAUDE.md（task tool、`.claude/agents/` 等）注入 Pi 的系统提示。

注意：本文件会被所有读 AGENTS.override.md 的运行时加载（Pi 等）。若某运行时的
入口另有其文件（如 Claude Code 读 CLAUDE.md），互不影响。

- 你的完整角色指令在 `.pi/SYSTEM.md`（已作为系统提示加载），那是唯一权威入口。
- 可用子 Agent 定义在 `.pi/agents/*.md`，调度一律用 `subagent` 工具。
- 确定性路由规则见 `routing.yaml`（相对仓库根目录）。
- 若要修改规则：只改 `prompts/`，然后跑 `python3 scripts/generate-agents.py --runtime=pi --all --write`。

不要尝试读取或遵循 `CLAUDE.md` / `.claude/` 下的内容——那是另一运行时的产物。
