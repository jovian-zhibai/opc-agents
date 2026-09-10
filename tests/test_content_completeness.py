"""测试：prompts/ 源内容在【全部五运行时】产物中逐行保留（内容级完整性闸）。

背景（2026-09-10 审查）：quality-gate 4.8 的内容级漂移检查只比对 prompts/ vs .opencode/，
pi/claude/gemini/codex 无同类闸——CI 的字节级再生检查防不住「生成器 bug 丢内容」
（ui-ux 47 行静默丢弃事故正是这个模式：产物与再生结果一致地错，字节检查双盲）。
本测试把 4.8 的思路推广到全部运行时：prompts 版每一有效行（归一化后）必须出现在
对应运行时产物中；产物多出（注入行/更全内容）允许。

与 4.8 的归一化规则对齐：
- 去 front matter（仅当首行为 ---）
- 路径 token 归一化（两环境有意差异）
- 相对链接深度归一化（各运行时目录层级不同，仅比较链接目标名）
- 去行内空白、去空行
"""
import re
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"

ROLES = [
    "advisor", "agent-manager", "dev", "director", "finance",
    "growth", "guardian", "product", "qa", "ui-ux",
]

# 运行时产物提取器：返回该运行时该角色的正文文本（md 原文 / toml 的 developer_instructions）
RUNTIMES = {
    "opencode": ("md", PROJECT_ROOT / ".opencode" / "agents"),
    "claude-code": ("md", PROJECT_ROOT / ".claude" / "agents"),
    "pi": ("md", PROJECT_ROOT / ".pi" / "agents"),
    "gemini": ("md", PROJECT_ROOT / ".gemini" / "agents"),
    "codex": ("toml", PROJECT_ROOT / ".codex" / "agents"),
}

# prompts 独有行阈值：与 quality-gate 4.8 对齐（能力边界节等属有意差异，留容差）
MISSING_LINE_THRESHOLD = 8


def _strip_front_matter(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:])
    return text


def _normalize(text: str) -> list[str]:
    """归一化为有效行集合（保序）。"""
    text = _strip_front_matter(text)
    # 路径 token：两环境有意差异（与 4.8 的 sed 规则对齐）
    text = re.sub(r"\$OPC_WORK_PATH|\{\{WORK_PATH\}\}|\.opencode/work|(?<![A-Za-z])work/", "WORK/", text)
    text = text.replace("$OPC_KNOWLEDGE_PATH", "KB")
    # 相对链接深度：各运行时目录层级不同，比较时归并为链接目标
    text = re.sub(r"\]\((?:\.\./)+", "](", text)
    out = []
    for line in text.split("\n"):
        s = re.sub(r"\s+", "", line)  # 行内所有空白
        if s:
            out.append(s)
    return out


def _load_text(kind: str, path: Path) -> str:
    if kind == "toml":
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return data.get("developer_instructions", "")
    return path.read_text(encoding="utf-8")


def _cases():
    cases = []
    for runtime, (kind, agents_dir) in RUNTIMES.items():
        for role in ROLES:
            f = agents_dir / f"{role}.{'toml' if kind == 'toml' else 'md'}"
            if f.exists() and (PROMPTS_DIR / f"{role}.md").exists():
                cases.append(pytest.param(runtime, role, id=f"{runtime}/{role}"))
    return cases


@pytest.mark.parametrize("runtime,role", _cases())
def test_prompts_content_preserved_in_runtime(runtime, role):
    """prompts 版有效行（归一化）必须在运行时产物中出现——缺失超阈值 = 行为级漂移。"""
    kind, agents_dir = RUNTIMES[runtime]
    prompts_lines = set(_normalize((PROMPTS_DIR / f"{role}.md").read_text(encoding="utf-8")))
    agent_text = _load_text(kind, agents_dir / f"{role}.{'toml' if kind == 'toml' else 'md'}")
    artifact_lines = set(_normalize(agent_text))
    missing = prompts_lines - artifact_lines
    assert len(missing) <= MISSING_LINE_THRESHOLD, (
        f"{runtime}/{role}: prompts 源有 {len(missing)} 行在产物中缺失（阈值 "
        f"{MISSING_LINE_THRESHOLD}）——疑似生成器丢内容或红线漂移。缺失样例：\n"
        + "\n".join(sorted(missing)[:5])
    )
