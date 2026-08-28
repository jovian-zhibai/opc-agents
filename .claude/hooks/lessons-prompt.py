#!/usr/bin/env python3
"""Claude Code hook: 会话启动自动检查 + 任务前查教训。

   支持两种事件（通过 --mode 参数区分）：
     --mode user_prompt   UserPromptSubmit 事件：每次用户提交 prompt 时触发，
                           注入流程提醒 + 任务前查教训
     --mode session_start  SessionStart 事件：会话启动/恢复时触发，
                           注入中断恢复（未完成任务）+ 会话引导 + 流程提醒

   核心逻辑委托给 scripts/opc-session-hook.py（五运行时共享核心），
   本脚本只做 Claude Code hook 协议适配（stdin 读 JSON → 调用核心 → stdout 输出 hookSpecificOutput）。

   降级：任何一步失败都静默跳过，不影响正常流程。
"""
import argparse
import json
import os
import sys
from pathlib import Path

# 把 scripts/ 加入 sys.path，导入共享核心
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent  # .claude/hooks/ → .claude/ → 项目根
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

try:
    from opc_session_hook import generate_context
except ImportError:
    # 共享核心不可用时静默降级（不注入任何内容）
    generate_context = lambda prompt="", mode="auto": ""


def main():
    parser = argparse.ArgumentParser(description="Claude Code OPC session hook")
    parser.add_argument(
        "--mode",
        choices=["user_prompt", "session_start", "auto"],
        default="auto",
        help="hook 事件模式",
    )
    args = parser.parse_args()

    # Claude Code hook 协议：stdin 读 JSON
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # 无法解析则静默

    prompt = str(payload.get("prompt", "") or "")
    mode = args.mode

    # 调用共享核心生成注入上下文
    context = generate_context(prompt, mode)

    if not context:
        return  # 无需注入

    # 输出 Claude Code hook 格式：hookSpecificOutput.additionalContext
    result = {"hookSpecificOutput": {"additionalContext": context}}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
