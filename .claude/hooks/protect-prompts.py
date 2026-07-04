#!/usr/bin/env python3
"""PreToolUse hook: 拦截对 prompts/ 和 .opencode/agents/ 的 Write/Edit。
   Director 红线："不直接写代码、改配置、改 prompt——系统文件一个标点也不自己改"。
   这条线不再靠 LLM 自觉，由 hook 物理拦截。
"""
import json
import sys
import os

PROTECTED_PREFIXES = ["prompts/", ".opencode/agents/"]
# 允许 .opencode/skills/ 下的修改（skill 安装/更新，不是 agent prompt）
ALLOWED_PREFIXES = [".opencode/skills/"]

def is_protected(path):
    """检查路径是否在保护范围内"""
    for prefix in ALLOWED_PREFIXES:
        if path.startswith(prefix):
            return False
    for prefix in PROTECTED_PREFIXES:
        if path.startswith(prefix):
            return True
    return False

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # 无法解析输入，放行（安全侧：只拦能确认的）
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)  # 非写操作，放行

    tool_input = data.get("tool_input", {})
    # Write/Edit 的文件路径字段可能是 file_path 或 path
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

    if not file_path:
        sys.exit(0)  # 无法确定路径，放行

    if is_protected(file_path):
        print(
            f"🚫 PreToolUse Hook: 禁止直接修改受保护文件\n"
            f"   目标: {file_path}\n"
            f"   原因: Director 不得直接编辑 prompts/ 或 .opencode/agents/ 下的 Agent prompt。\n"
            f"   正确做法: 调度 AgentManager 或 Dev 执行修改，走正式流程。",
            file=sys.stderr
        )
        sys.exit(1)  # 非零退出 = 拦截

    sys.exit(0)  # 放行

if __name__ == "__main__":
    main()
