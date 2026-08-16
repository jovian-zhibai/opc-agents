#!/usr/bin/env python3
"""UserPromptSubmit hook: 任务前查教训 + 流程提醒 + 会话引导（Claude Code 版）。

   Claude Code 在用户提交 prompt 后、AI 开始处理前调用本 hook。
   hook 从 stdin 读 JSON（含 prompt），返回 hookSpecificOutput.additionalContext
   注入给模型——等价于 pi 扩展的 before_agent_start 注入。

   注入内容（克制原则，只加高频高危）：
     1. 流程提醒：涉及钱/用户可见变化需问创始人、QA 3次失败上报
     2. session-notes 最后 20 行（新会话引导）
     3. lessons-index 检索命中教训（任务前查教训）

   降级：任何一步失败都静默跳过，不影响正常流程。
"""
import json
import subprocess
import sys
import os
import re
from pathlib import Path

# 路径（支持环境变量覆盖）
HOME = str(Path.home())
KNOWLEDGE = os.environ.get("OPC_KNOWLEDGE_PATH", f"{HOME}/code/opc/opc-knowledge")
SEARCH_SCRIPT = f"{HOME}/code/opc/opc-agents/.opencode/skills/lessons-index/search.sh"
SESSION_NOTES = f"{HOME}/code/opc/opc-agents/work/session-notes.md"

# 无条件注入的高危流程提醒
FLOW_REMINDER = (
    "【流程提醒】本任务开始前请留意：\n"
    "1. 涉及金钱/定价/预算 → 必须先问创始人，不自行决策\n"
    "2. 涉及用户可见的界面/文案/交互变化 → 先问创始人确认方向\n"
    "3. 若需 QA 验证且连续 3 次失败 → 停止并上报创始人，不无限重试\n"
    "（其余流程规则遵循系统提示，此处仅提醒最高危三条）"
)

# 停用词（同 pi 版，避免虚词误命中）
STOPWORDS = (
    "帮我|请|一下|一个|这个|那个|需要|要|我|你|的|了|吗|呢|写一篇|写个|帮我写|"
    "帮我改|帮我修|帮我做|写|做|改|修|修复|开发|实现|处理|检查|看看|优化|升级|"
    "创建|新增|删除|移除|已经|还没|还没有|都|就|还|才|刚|刚刚|已|也|再|又|然后|现在|先"
)


def extract_keywords(prompt: str):
    """提取检索关键词：去停用词后取连续汉字片段，最多 2 个。"""
    cleaned = re.sub(STOPWORDS, " ", prompt)
    cleaned = re.sub(r"[\s,，。！？、;；:：\"'（）()a-zA-Z0-9]+", " ", cleaned)
    chars = re.sub(r"\s+", "", cleaned)
    queries = []
    if len(chars) >= 4:
        queries.append(chars[:4])
        if len(chars) >= 8:
            queries.append(chars[len(chars) // 2 : len(chars) // 2 + 4])
    elif len(chars) >= 2:
        queries.append(chars[:2])
    return queries[:2]


def search_lessons(keywords):
    """运行 search.sh 检索教训。"""
    if not os.path.exists(SEARCH_SCRIPT) or not keywords:
        return ""
    results = []
    for kw in keywords:
        try:
            env = dict(os.environ, OPC_KNOWLEDGE_PATH=KNOWLEDGE)
            out = subprocess.run(
                ["bash", SEARCH_SCRIPT, kw],
                capture_output=True, text=True, timeout=10, env=env,
            ).stdout.strip()
            if out:
                results.append(f"【检索词：{kw}】\n{out}")
        except Exception:
            pass
    return "\n\n---\n\n".join(results[:2])


def read_session_notes():
    """读 session-notes 最后 20 行。"""
    try:
        if not os.path.exists(SESSION_NOTES):
            return ""
        lines = Path(SESSION_NOTES).read_text(encoding="utf-8").splitlines()
        meaningful = [l for l in lines if l.strip() and not l.startswith("#")]
        if not meaningful:
            return ""
        return "\n".join(meaningful[-20:])
    except Exception:
        return ""


def main():
    # Claude Code hook 协议：stdin 读 JSON，stdout 输出 JSON
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # 无法解析则静默

    prompt = str(payload.get("prompt", "") or "").strip()
    if len(prompt) < 4:
        return  # 纯问候/闲聊不注入

    parts = [FLOW_REMINDER]

    session_notes = read_session_notes()
    if session_notes:
        parts.append(f"【会话上下文】上次会话记录（最后 20 行，新会话引导）：\n{session_notes}")

    lessons = search_lessons(extract_keywords(prompt))
    if lessons:
        parts.append(
            "【任务前查教训】根据本次任务检索到以下历史教训，请先阅读再开始干活"
            "（如无相关则不适用）：\n\n" + lessons
        )

    # 输出 hookSpecificOutput.additionalContext
    result = {"hookSpecificOutput": {"additionalContext": "\n\n".join(parts)}}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
