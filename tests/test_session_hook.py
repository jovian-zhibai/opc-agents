"""tests/test_session_hook.py — 五运行时共享核心 opc_session_hook.py 测试。

覆盖：
  - generate_context 三种模式：session_start / user_prompt / auto
  - 降级：state.json / session-notes / search.sh 缺失或损坏时不报错
  - 临时目录 + 环境变量隔离，不依赖真实用户路径
"""
import json
import os
import sys
import stat
from pathlib import Path

import pytest

# 把 scripts/ 加入 sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

import opc_session_hook as hook  # noqa: E402


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """创建隔离的临时目录结构，设置环境变量。"""
    agents_path = tmp_path / "opc-agents"
    work_path = tmp_path / "work"
    knowledge_path = tmp_path / "knowledge"

    # 创建目录结构
    (agents_path / "scripts").mkdir(parents=True)
    (agents_path / ".opencode" / "skills" / "lessons-index").mkdir(parents=True)
    work_path.mkdir(parents=True)
    knowledge_path.mkdir(parents=True)

    # 设置环境变量
    monkeypatch.setenv("OPC_AGENTS_PATH", str(agents_path))
    monkeypatch.setenv("OPC_WORK_PATH", str(work_path))
    monkeypatch.setenv("OPC_KNOWLEDGE_PATH", str(knowledge_path))

    return {
        "agents_path": agents_path,
        "work_path": work_path,
        "knowledge_path": knowledge_path,
        "state_file": agents_path / "scripts" / "state.json",
        "session_notes": work_path / "session-notes.md",
        "search_script": agents_path / ".opencode" / "skills" / "lessons-index" / "search.sh",
    }


def _write_state_json(state_file, tasks):
    """写入模拟的 state.json。"""
    state_file.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False), encoding="utf-8")


def _write_session_notes(session_notes, lines):
    """写入模拟的 session-notes.md。"""
    session_notes.write_text("\n".join(lines), encoding="utf-8")


def _write_search_script(search_script, output="模拟教训内容"):
    """写入模拟的 search.sh（可执行）。"""
    search_script.write_text(f"#!/bin/bash\necho '{output}'\n", encoding="utf-8")
    search_script.chmod(search_script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


# ─── session_start 模式 ───

class TestSessionStartMode:
    def test_with_unfinished_tasks_and_notes(self, isolated_env):
        """有未完成任务 + session-notes → 含中断恢复+会话引导+流程提醒。"""
        _write_state_json(isolated_env["state_file"], [
            {"name": "任务A", "current_phase": "开发", "status": "in_progress"},
        ])
        _write_session_notes(isolated_env["session_notes"], [
            "[2026-08-28] 上次干到登录功能接口",
            "[2026-08-27] 注意数据库连接串别写错",
        ])

        result = hook.generate_context("", "session_start")

        assert "【中断恢复】" in result
        assert "任务A" in result
        assert "【会话上下文】" in result
        assert "登录功能接口" in result
        assert "【流程提醒】" in result

    def test_without_unfinished_tasks(self, isolated_env):
        """无未完成任务 → 含会话引导+流程提醒，不含中断恢复。"""
        _write_state_json(isolated_env["state_file"], [
            {"name": "已完成任务", "status": "completed"},
        ])
        _write_session_notes(isolated_env["session_notes"], ["[2026-08-28] 测试记录"])

        result = hook.generate_context("", "session_start")

        assert "【中断恢复】" not in result
        assert "【会话上下文】" in result
        assert "【流程提醒】" in result

    def test_no_session_notes(self, isolated_env):
        """无 session-notes → 含流程提醒，不含会话引导。"""
        _write_state_json(isolated_env["state_file"], [])

        result = hook.generate_context("", "session_start")

        assert "【会话上下文】" not in result
        assert "【流程提醒】" in result

    def test_empty_state_json(self, isolated_env):
        """state.json 为空文件 → 不报错，返回流程提醒。"""
        isolated_env["state_file"].write_text("", encoding="utf-8")

        result = hook.generate_context("", "session_start")

        assert "【流程提醒】" in result
        assert "【中断恢复】" not in result

    def test_corrupt_state_json(self, isolated_env):
        """state.json 损坏（非法 JSON）→ 不报错，静默跳过中断恢复。"""
        isolated_env["state_file"].write_text("{invalid json", encoding="utf-8")
        _write_session_notes(isolated_env["session_notes"], ["[2026-08-28] 测试"])

        result = hook.generate_context("", "session_start")

        assert "【中断恢复】" not in result
        assert "【会话上下文】" in result
        assert "【流程提醒】" in result


# ─── user_prompt 模式 ───

class TestUserPromptMode:
    def test_with_lessons(self, isolated_env):
        """prompt≥4 字 + search.sh 存在 → 含流程提醒+教训检索。"""
        _write_search_script(isolated_env["search_script"], "登录功能教训：别用明文密码")

        result = hook.generate_context("帮我写登录功能", "user_prompt")

        assert "【流程提醒】" in result
        assert "【任务前查教训】" in result
        assert "登录功能教训" in result

    def test_short_prompt_returns_empty(self, isolated_env):
        """prompt<4 字 → 返回空。"""
        result = hook.generate_context("hi", "user_prompt")
        assert result == ""

    def test_empty_prompt_returns_empty(self, isolated_env):
        """prompt 为空 → 返回空。"""
        result = hook.generate_context("", "user_prompt")
        assert result == ""

    def test_no_search_script(self, isolated_env):
        """无 search.sh → 含流程提醒，不含教训检索。"""
        # 不创建 search.sh

        result = hook.generate_context("帮我写登录功能", "user_prompt")

        assert "【流程提醒】" in result
        assert "【任务前查教训】" not in result

    def test_search_script_fails(self, isolated_env):
        """search.sh 执行失败（非零退出）→ 不报错，静默跳过教训检索。"""
        isolated_env["search_script"].write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
        isolated_env["search_script"].chmod(
            isolated_env["search_script"].stat().st_mode | stat.S_IEXEC
        )

        result = hook.generate_context("帮我写登录功能", "user_prompt")

        assert "【流程提醒】" in result
        assert "【任务前查教训】" not in result


# ─── auto 模式 ───

class TestAutoMode:
    def test_with_prompt_goes_user_prompt(self, isolated_env):
        """有 prompt≥4 字 → 走 user_prompt（含流程提醒，无中断恢复）。"""
        _write_state_json(isolated_env["state_file"], [
            {"name": "任务A", "current_phase": "开发", "status": "in_progress"},
        ])
        _write_session_notes(isolated_env["session_notes"], ["[2026-08-28] 测试"])

        result = hook.generate_context("帮我写登录功能", "auto")

        # user_prompt 模式不含中断恢复和会话引导
        assert "【中断恢复】" not in result
        assert "【会话上下文】" not in result
        assert "【流程提醒】" in result

    def test_without_prompt_goes_session_start(self, isolated_env):
        """无 prompt → 走 session_start（含中断恢复+会话引导+流程提醒）。"""
        _write_state_json(isolated_env["state_file"], [
            {"name": "任务A", "current_phase": "开发", "status": "in_progress"},
        ])
        _write_session_notes(isolated_env["session_notes"], ["[2026-08-28] 测试"])

        result = hook.generate_context("", "auto")

        assert "【中断恢复】" in result
        assert "【会话上下文】" in result
        assert "【流程提醒】" in result

    def test_short_prompt_goes_session_start(self, isolated_env):
        """prompt<4 字 → 走 session_start。"""
        _write_session_notes(isolated_env["session_notes"], ["[2026-08-28] 测试"])

        result = hook.generate_context("hi", "auto")

        # session_start 模式含会话引导
        assert "【会话上下文】" in result
        assert "【流程提醒】" in result


# ─── 降级综合测试 ───

class TestDegradation:
    def test_all_files_missing_session_start(self, isolated_env):
        """所有文件缺失（session_start）→ 不报错，仅返回流程提醒。"""
        # 不创建任何文件

        result = hook.generate_context("", "session_start")

        assert result == hook.FLOW_REMINDER

    def test_all_files_missing_user_prompt_long(self, isolated_env):
        """所有文件缺失（user_prompt 长 prompt）→ 不报错，返回流程提醒。"""
        result = hook.generate_context("帮我写登录功能", "user_prompt")

        assert result == hook.FLOW_REMINDER

    def test_knowledge_path_missing(self, isolated_env):
        """OPC_KNOWLEDGE_PATH 指向不存在目录 → 不报错。"""
        # search.sh 存在但 knowledge_path 不存在（已在 isolated_env 中创建为空目录）
        _write_search_script(isolated_env["search_script"], "教训内容")

        result = hook.generate_context("帮我写登录功能", "user_prompt")

        assert "【流程提醒】" in result
        # search.sh 应该仍能执行（它不依赖 knowledge_path）
        assert "【任务前查教训】" in result

    def test_state_json_wrong_structure(self, isolated_env):
        """state.json 结构不对（无 tasks 字段）→ 不报错，静默跳过。"""
        isolated_env["state_file"].write_text(
            json.dumps({"wrong_key": "value"}, ensure_ascii=False),
            encoding="utf-8",
        )

        result = hook.generate_context("", "session_start")

        assert "【中断恢复】" not in result
        assert "【流程提醒】" in result

    def test_session_notes_only_comments(self, isolated_env):
        """session-notes 只有注释行（# 开头）→ 视为无有效内容，不含会话引导。"""
        _write_session_notes(isolated_env["session_notes"], [
            "# 这是注释",
            "# 也是注释",
        ])

        result = hook.generate_context("", "session_start")

        assert "【会话上下文】" not in result
        assert "【流程提醒】" in result
