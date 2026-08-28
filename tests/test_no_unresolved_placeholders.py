"""测试：生成产物中不应包含未解析的 {{...}} 占位符。

防止生成器 bug 导致占位符未被替换（如 apply_path_replace 的 overrides 覆盖 default 问题）。
也防止将来新增占位符时忘记在 adapter 里配置替换规则。
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 需要检查的生成产物目录（各运行时的 agents/ 目录）
RUNTIME_AGENTS_DIRS = [
    PROJECT_ROOT / ".opencode" / "agents",
    PROJECT_ROOT / ".claude" / "agents",
    PROJECT_ROOT / ".pi" / "agents",
    PROJECT_ROOT / ".gemini" / "agents",
    PROJECT_ROOT / ".codex" / "agents",
]

# 匹配 {{...}} 占位符（非贪婪，允许内部有空格、字母、数字、下划线、连字符）
PLACEHOLDER_PATTERN = re.compile(r"\{\{[^{}]*\}\}")

# 文件扩展名白名单（只检查这些类型的生成产物）
ALLOWED_EXTENSIONS = {".md", ".toml"}


def _collect_generated_files():
    """收集所有需要检查的生成产物文件。"""
    files = []
    for agents_dir in RUNTIME_AGENTS_DIRS:
        if not agents_dir.exists():
            continue
        for f in agents_dir.iterdir():
            if f.is_file() and f.suffix in ALLOWED_EXTENSIONS:
                files.append(f)
    return files


def test_no_unresolved_placeholders_in_generated_agents():
    """所有生成的 agent 文件中不应包含未解析的 {{...}} 占位符。"""
    files = _collect_generated_files()
    assert len(files) > 0, "未找到任何生成的 agent 文件，检查目录结构是否正确"

    violations = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines(), start=1):
            matches = PLACEHOLDER_PATTERN.findall(line)
            if matches:
                rel_path = f.relative_to(PROJECT_ROOT)
                violations.append(f"{rel_path}:{line_num}: {matches} -> {line.strip()[:80]}")

    if violations:
        pytest.fail(
            f"发现 {len(violations)} 处未解析的 {{...}} 占位符（生成器 bug 或 adapter 配置缺失）：\n"
            + "\n".join(violations[:20])
            + ("\n...（更多省略）" if len(violations) > 20 else "")
        )


def test_placeholder_pattern_actually_matches():
    """元测试：确认 PLACEHOLDER_PATTERN 能匹配常见占位符格式。"""
    assert PLACEHOLDER_PATTERN.search("{{WORK_PATH}}")
    assert PLACEHOLDER_PATTERN.search("{{LESSONS_SEARCH_CMD}}")
    assert PLACEHOLDER_PATTERN.search("text {{ROLE_NAME}} more")
    # 不匹配单大括号
    assert not PLACEHOLDER_PATTERN.search("{WORK_PATH}")
    assert not PLACEHOLDER_PATTERN.search("{{WORK_PATH")  # 未闭合
