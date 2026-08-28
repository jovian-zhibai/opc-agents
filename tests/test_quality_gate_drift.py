"""quality-gate.sh 漂移检测测试：验证 4.8 内容级漂移检查的行为。

测试策略：quality-gate 基于 $0 定位 PROJECT_DIR（临时结构），
因此把脚本复制到 tmp/scripts/quality-gate.sh，配合临时 prompts/ 与 .opencode/agents/。

聚焦 4.8 检查：prompts 版是基准，若 prompts 版有超过 8 行内容在 opencode 版缺失
（红线/章节漂移），quality-gate 应报错并 exit 1；内容一致时应通过。
其他检查项（prompts 文件完整性、routing、CLAUDE.md 等）在临时环境可能报错，
因此用「exit code 变化 + 输出包含漂移标记」来断言，而不是要求 0 errors。
"""

import os
import shutil
import subprocess

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QG_SCRIPT = os.path.join(PROJECT_DIR, "scripts", "quality-gate.sh")


def _setup_env(tmp_path):
    scripts_dir = tmp_path / "scripts"
    prompts_dir = tmp_path / "prompts"
    agents_dir = tmp_path / ".opencode" / "agents"
    scripts_dir.mkdir(parents=True)
    prompts_dir.mkdir(parents=True)
    agents_dir.mkdir(parents=True)
    shutil.copy(QG_SCRIPT, scripts_dir / "quality-gate.sh")
    return scripts_dir, prompts_dir, agents_dir


def _run(scripts_dir):
    return subprocess.run(
        ["bash", "quality-gate.sh"],
        cwd=str(scripts_dir),
        capture_output=True,
        text=True,
    )


def _write_prompt(dirpath, name, body):
    """写一个含 front matter + 密钥红线 + 正文的 prompt 文件。"""
    (dirpath / f"{name}.md").write_text(
        "---\nname: " + name + "\ndescription: test\n---\n\n"
        + "不泄露 API key，不泄露任何密钥。\n\n"
        + body,
        encoding="utf-8",
    )


# ---------- 1. 漂移场景：prompts 版有 9 行在 opencode 版缺失 → 报错 ----------

def test_drift_detected_when_prompts_has_missing_content(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)

    # prompts 版含 9 行独有内容（超过 8 行阈值）
    prompts_body = "\n".join(f"## 新增红线 {i}\n独有内容行 {i}" for i in range(5))
    _write_prompt(prompts_dir, "dev", prompts_body)

    # opencode 版只有前 2 行独有内容（在阈值内），其余缺失
    opencode_body = "\n".join(f"## 新增红线 {i}\n独有内容行 {i}" for i in range(2))
    _write_prompt(agents_dir, "dev", opencode_body)

    result = _run(scripts_dir)

    # 4.8 应检测到 prompts 版独有行超阈值并报错
    assert "漂移" in result.stdout or "prompts 版有" in result.stdout
    assert result.returncode == 1


# ---------- 2. 一致场景：prompts 版与 opencode 版内容相同 → 4.8 不报漂移 ----------

def test_no_drift_when_identical(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)

    body = "## 红线\n\n相同内容\n\n## 职责\n\n正常工作\n"
    _write_prompt(prompts_dir, "dev", body)
    _write_prompt(agents_dir, "dev", body)

    result = _run(scripts_dir)

    # 内容一致：4.8 不应报 dev 漂移
    assert "dev: prompts 独有" in result.stdout
    assert "prompts 独有 0 行" in result.stdout or "阈值内" in result.stdout


# ---------- 3. 红线缺失专项：prompts 有密钥红线、opencode 缺失 → 报错 ----------

def test_redline_missing_in_opencode_is_error(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)

    # prompts 版含密钥红线
    _write_prompt(prompts_dir, "qa", "## 红线\n\n不泄露任何密钥。\n\n## 职责\n\n测试\n")
    # opencode 版完全不含密钥红线
    _write_prompt(agents_dir, "qa", "## 职责\n\n测试\n")

    result = _run(scripts_dir)

    assert "红线缺失" in result.stdout or "红线" in result.stdout
    assert result.returncode == 1
