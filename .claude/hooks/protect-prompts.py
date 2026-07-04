#!/usr/bin/env python3
"""PreToolUse hook: 拦截对 prompts/、.opencode/agents/ 及系统文件的 Write/Edit。
   Director 红线："不直接写代码、改配置、改 prompt——系统文件一个标点也不自己改"。
   这条线不再靠 LLM 自觉，由 hook 物理拦截。
"""
import json
import sys
import os

# 保护目标：相对仓库根的路径/前缀
PROTECTED_PREFIXES = [
    "prompts/",
    ".opencode/agents/",
]
PROTECTED_EXACT = [
    "CLAUDE.md",
    "routing.yaml",
    "feedback.schema.json",
]
# 允许 .opencode/skills/ 下的修改（skill 安装/更新，不是 agent prompt）
ALLOWED_PREFIXES = [".opencode/skills/"]

def get_repo_root():
    """从脚本位置推导仓库根（.claude/hooks/../../）"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def is_protected(file_path):
    """检查路径是否在保护范围内"""
    repo_root = get_repo_root()

    # 规范化为相对路径
    try:
        rel = os.path.relpath(file_path, repo_root)
    except ValueError:
        # 跨盘或无法计算相对路径，放行
        return False

    # 精确匹配
    for exact in PROTECTED_EXACT:
        if rel == exact:
            return True

    # 白名单优先
    for prefix in ALLOWED_PREFIXES:
        if rel.startswith(prefix):
            return False

    # 黑名单（前缀匹配）
    for prefix in PROTECTED_PREFIXES:
        if rel.startswith(prefix):
            return True

    return False

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

    if not file_path:
        sys.exit(0)

    if is_protected(file_path):
        print(
            f"🚫 PreToolUse Hook: 禁止直接修改受保护文件\n"
            f"   目标: {file_path}\n"
            f"   原因: Director 不得直接编辑 Agent prompt 或系统文件。\n"
            f"   正确做法: 调度 AgentManager 或 Dev 执行修改，走正式流程。",
            file=sys.stderr
        )
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
