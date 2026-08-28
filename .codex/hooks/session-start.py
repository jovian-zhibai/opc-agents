#!/usr/bin/env python3
"""Codex CLI SessionStart hook: 会话启动自动检查（五运行时共享核心适配）。

   Codex CLI 在会话启动时触发本 hook（hooks 已 Stable，默认启用）。
   hook 从 stdin 读 JSON（Codex CLI hook 输入，含 session_id/cwd/model 等），
   输出 {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
   注入给模型——与 Claude Code/Gemini 的 additionalContext 等价。

   核心逻辑委托给 scripts/opc_session_hook.py（五运行时共享核心）：
     session_start 模式：中断恢复 + 会话引导 + 高危流程提醒
     （SessionStart 时通常还没有用户 prompt，所以用 session_start 模式）

   降级：任何一步失败都静默跳过，不影响正常流程。
   Debug 输出到 stderr，不污染 stdout 的 JSON。

   官方文档：https://developers.openai.com/codex/hooks
"""
import json
import os
import subprocess
import sys
from pathlib import Path

# 项目路径（优先用环境变量，否则用脚本相对路径）
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(
    os.environ.get("OPC_AGENTS_PATH", SCRIPT_DIR.parent.parent)
)
HOOK_SCRIPT = PROJECT_DIR / "scripts" / "opc_session_hook.py"


def main():
    # Codex CLI hook 协议：stdin 读 JSON（可能为空或不完整）
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    # SessionStart 时通常没有 prompt，用 session_start 模式
    prompt = str(payload.get("prompt", "") or payload.get("userPrompt", "") or "")
    mode = "user_prompt" if prompt and len(prompt.strip()) >= 4 else "session_start"

    # 检查共享核心是否存在
    if not HOOK_SCRIPT.exists():
        print(f"[opc-session-hook] 共享核心不存在: {HOOK_SCRIPT}", file=sys.stderr)
        return

    # 调用共享核心
    try:
        input_data = json.dumps({"prompt": prompt, "mode": mode})
        result = subprocess.run(
            ["python3", str(HOOK_SCRIPT)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            print(f"[opc-session-hook] 共享核心执行失败: {result.stderr}", file=sys.stderr)
            return

        output = json.loads(result.stdout)
        context = output.get("context", "")

        if not context:
            return  # 无需注入

        # 输出 Codex CLI hook 格式
        # 纯文本也可作为 developer context，但用 JSON 更规范
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": context,
                    }
                },
                ensure_ascii=False,
            )
        )
        sys.stdout.flush()
    except Exception as e:
        print(f"[opc-session-hook] 错误: {e}", file=sys.stderr)
        # 静默失败，不影响正常流程


if __name__ == "__main__":
    main()
