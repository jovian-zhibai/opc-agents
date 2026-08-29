#!/usr/bin/env python3
"""OPC 会话启动自动检查 — 共享核心逻辑（五运行时通用）。

   统一行为规格（设计文档 §3.1）：
     1. 高危流程提醒：涉及钱/用户可见变化需问创始人、QA 3次失败上报
     2. 会话引导：读 session-notes.md 最后 20 行，了解上次干到哪、有什么坑
     3. 任务前查教训：提取任务关键词，检索 lessons-index，命中则注入
        （仅当提供了 prompt 时执行，SessionStart 无 prompt 时跳过）

   降级原则：任何一步失败都静默跳过，不影响正常流程。

   两种使用方式：
     1. 命令行：echo '{"prompt": "...", "mode": "session_start"}' | python3 opc-session-hook.py
        输出：{"context": "..."}
     2. 模块导入：from opc_session_hook import generate_context
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _resolve_paths():
    """解析路径，支持环境变量覆盖。"""
    home = str(Path.home())
    agents_path = os.environ.get(
        "OPC_AGENTS_PATH", f"{home}/code/opc/opc-agents"
    )
    knowledge_path = os.environ.get(
        "OPC_KNOWLEDGE_PATH", f"{home}/code/opc/opc-knowledge"
    )
    work_path = os.environ.get(
        "OPC_WORK_PATH", f"{agents_path}/work"
    )
    search_script = f"{agents_path}/.opencode/skills/lessons-index/search.sh"
    session_notes = f"{work_path}/session-notes.md"
    state_file = f"{agents_path}/scripts/state.json"
    return agents_path, knowledge_path, work_path, search_script, session_notes, state_file


# 无条件注入的高危流程提醒
FLOW_REMINDER = (
    "【流程提醒】本任务开始前请留意：\n"
    "1. 涉及金钱/定价/预算 → 必须先问创始人，不自行决策\n"
    "2. 涉及用户可见的界面/文案/交互变化 → 先问创始人确认方向\n"
    "3. 若需 QA 验证且连续 3 次失败 → 停止并上报创始人，不无限重试\n"
    "（其余流程规则遵循系统提示，此处仅提醒最高危三条）"
)

# 停用词（避免虚词误命中教训检索）
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


def search_lessons(keywords, knowledge_path, search_script):
    """运行 search.sh 检索教训。"""
    if not os.path.exists(search_script) or not keywords:
        return ""
    results = []
    for kw in keywords:
        try:
            env = dict(os.environ, OPC_KNOWLEDGE_PATH=knowledge_path)
            out = subprocess.run(
                ["bash", search_script, kw],
                capture_output=True, text=True, timeout=10, env=env,
            ).stdout.strip()
            if out:
                results.append(f"【检索词：{kw}】\n{out}")
        except Exception:
            pass
    return "\n\n---\n\n".join(results[:2])


def read_session_notes(session_notes_path):
    """读 session-notes 最后 20 行。"""
    try:
        if not os.path.exists(session_notes_path):
            return ""
        lines = Path(session_notes_path).read_text(encoding="utf-8").splitlines()
        meaningful = [l for l in lines if l.strip() and not l.startswith("#")]
        if not meaningful:
            return ""
        return "\n".join(meaningful[-20:])
    except Exception:
        return ""


def check_unfinished_tasks(state_file_path):
    """检查未完成任务（中断恢复）。读 state.json，返回未完成任务摘要。

    state.json 真实结构（scripts/state-manager.py 写入）：
      {"events": [...], "current_task": {name, current_stage, progress, artifact, updated_at} | None, "history": [...]}
    活跃任务是单对象 current_task，无 tasks[] 数组、无 status 字段。
    """
    try:
        if not os.path.exists(state_file_path):
            return ""
        import json as _json
        with open(state_file_path, encoding="utf-8") as f:
            state = _json.load(f)
        task = state.get("current_task")
        if not task or not isinstance(task, dict):
            return ""
        name = task.get("name", "未知任务")
        stage = task.get("current_stage") or task.get("phase") or "未知阶段"
        return f"  - {name}（当前阶段：{stage}）"
    except Exception:
        return ""


def generate_context(prompt: str = "", mode: str = "auto") -> str:
    """生成会话启动/任务前的注入上下文。

    Args:
        prompt: 用户 prompt 文本（UserPromptSubmit 时提供，SessionStart 时为空）
        mode: "session_start"（会话启动，含未完成任务+会话引导+流程提醒）
              "user_prompt"（用户提交，含教训检索+流程提醒）
              "auto"（自动判断：有 prompt 则 user_prompt，无则 session_start）

    Returns:
        注入上下文文本（空字符串表示无需注入）
    """
    if mode == "auto":
        mode = "user_prompt" if prompt and len(prompt.strip()) >= 4 else "session_start"

    _, knowledge_path, _, search_script, session_notes, state_file = _resolve_paths()
    parts = []

    if mode == "session_start":
        # 1. 未完成任务（中断恢复）
        unfinished = check_unfinished_tasks(state_file)
        if unfinished:
            parts.append(f"【中断恢复】检测到未完成任务，请先确认是否继续：\n{unfinished}")

        # 2. 会话引导
        session_notes_content = read_session_notes(session_notes)
        if session_notes_content:
            parts.append(
                f"【会话上下文】上次会话记录（最后 20 行，新会话引导）：\n{session_notes_content}"
            )

        # 3. 流程提醒
        parts.append(FLOW_REMINDER)

    elif mode == "user_prompt":
        if not prompt or len(prompt.strip()) < 4:
            return ""  # 纯问候/闲聊不注入

        # 1. 流程提醒
        parts.append(FLOW_REMINDER)

        # 2. 任务前查教训
        lessons = search_lessons(extract_keywords(prompt), knowledge_path, search_script)
        if lessons:
            parts.append(
                "【任务前查教训】根据本次任务检索到以下历史教训，请先阅读再开始干活"
                "（如无相关则不适用）：\n\n" + lessons
            )

    return "\n\n".join(parts)


def main():
    """命令行入口：stdin 读 JSON，stdout 输出 JSON。"""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    prompt = str(payload.get("prompt", "") or "")
    mode = str(payload.get("mode", "auto"))

    context = generate_context(prompt, mode)

    result = {"context": context}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
