"""sync-opencode.sh 测试：双环境核心章节同步逻辑。

测试策略：脚本路径基于 $0 定位（SCRIPT_DIR → ../prompts 与 ../.opencode/agents），
因此把脚本复制到临时目录结构（tmp/scripts/sync-opencode.sh），
配合 tmp/prompts/ 与 tmp/.opencode/agents/ 构造隔离环境，用 subprocess 调用。

覆盖：同步成功、已一致跳过、dry-run 不改文件、备份生成、章节缺失跳过。
"""

import os
import shutil
import subprocess

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC_SCRIPT = os.path.join(PROJECT_DIR, "scripts", "sync-opencode.sh")


def _setup_env(tmp_path):
    """构造隔离的 sync 环境，返回 (scripts_dir, prompts_dir, agents_dir)。"""
    scripts_dir = tmp_path / "scripts"
    prompts_dir = tmp_path / "prompts"
    agents_dir = tmp_path / ".opencode" / "agents"
    scripts_dir.mkdir(parents=True)
    prompts_dir.mkdir(parents=True)
    agents_dir.mkdir(parents=True)
    # 复制脚本到临时结构，保证 $0 定位到临时目录
    shutil.copy(SYNC_SCRIPT, scripts_dir / "sync-opencode.sh")
    return scripts_dir, prompts_dir, agents_dir


def _run(scripts_dir, *args):
    return subprocess.run(
        ["bash", "sync-opencode.sh", *args],
        cwd=str(scripts_dir),
        capture_output=True,
        text=True,
    )


# ---------- 1. 同步成功：差异章节被覆盖为 prompts 版 ----------

def test_sync_updates_diverged_section(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)
    (prompts_dir / "director.md").write_text(
        "---\nname: director\n---\n\n## 红线\n\n新红线内容 A\n",
        encoding="utf-8",
    )
    (agents_dir / "director.md").write_text(
        "---\nname: director\n---\n\n## 红线\n\n旧红线内容 B\n",
        encoding="utf-8",
    )

    result = _run(scripts_dir)

    assert result.returncode == 0, result.stderr
    # 同步后 agents 版红线 = prompts 版红线
    agents_content = (agents_dir / "director.md").read_text(encoding="utf-8")
    assert "新红线内容 A" in agents_content
    assert "旧红线内容 B" not in agents_content
    assert "1 处更新" in result.stdout or "1 行差异 → 0 行" in result.stdout


def test_sync_keeps_front_matter_intact(tmp_path):
    """同步只改核心章节，front matter 与正文其余部分不动。"""
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)
    (prompts_dir / "dev.md").write_text(
        "---\nname: dev\n---\n\n## 红线\n\n新红线\n",
        encoding="utf-8",
    )
    (agents_dir / "dev.md").write_text(
        "---\nname: dev\nskills:\n  - code-review\n---\n\n## 红线\n\n旧红线\n\n## 职责\n\n专属内容\n",
        encoding="utf-8",
    )

    _run(scripts_dir)

    agents_content = (agents_dir / "dev.md").read_text(encoding="utf-8")
    # front matter（skills）保留
    assert "skills:" in agents_content
    assert "code-review" in agents_content
    # 红线被更新
    assert "新红线" in agents_content
    # 红线后的专属内容保留
    assert "专属内容" in agents_content


# ---------- 2. 已一致：跳过不动 ----------

def test_sync_skips_identical_section(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)
    content = "---\nname: qa\n---\n\n## 红线\n\n相同内容\n"
    (prompts_dir / "qa.md").write_text(content, encoding="utf-8")
    (agents_dir / "qa.md").write_text(content, encoding="utf-8")

    result = _run(scripts_dir)

    assert result.returncode == 0
    assert "已一致" in result.stdout
    assert "0 处更新" in result.stdout or "同步完成" in result.stdout


# ---------- 3. dry-run：预览但不改文件 ----------

def test_dry_run_does_not_modify(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)
    (prompts_dir / "dev.md").write_text(
        "---\nname: dev\n---\n\n## 红线\n\n新红线\n",
        encoding="utf-8",
    )
    (agents_dir / "dev.md").write_text(
        "---\nname: dev\n---\n\n## 红线\n\n旧红线\n",
        encoding="utf-8",
    )
    before = (agents_dir / "dev.md").read_text(encoding="utf-8")

    result = _run(scripts_dir, "--dry-run")

    assert result.returncode == 0
    assert "dry-run" in result.stdout
    # 文件未被修改
    assert (agents_dir / "dev.md").read_text(encoding="utf-8") == before


# ---------- 4. 备份生成 ----------

def test_sync_creates_backup(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)
    (prompts_dir / "dev.md").write_text(
        "---\nname: dev\n---\n\n## 红线\n\n新红线\n",
        encoding="utf-8",
    )
    (agents_dir / "dev.md").write_text(
        "---\nname: dev\n---\n\n## 红线\n\n旧红线\n",
        encoding="utf-8",
    )

    import glob

    # 备份文件名 = /tmp/opc-sync-backup-{role}-{section去字母}.md。
    # 注意："## 红线" 去非 a-zA-Z 后为空 → 固定文件名 opc-sync-backup-dev-.md，
    # 重复运行会覆盖而非新增。备份语义是「同步前保留一份旧版可回滚」，
    # 因此断言：该文件存在且内容为同步前的旧红线。
    _run(scripts_dir)

    backups = glob.glob("/tmp/opc-sync-backup-dev-*")
    assert backups, "应生成备份文件"
    # 备份内容是同步前的旧内容
    backup_content = open(backups[0], encoding="utf-8").read()
    assert "旧红线" in backup_content
    assert "新红线" not in backup_content


# ---------- 5. 章节缺失：跳过 ----------

def test_sync_skips_missing_section(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)
    # prompts 版没有红线章节
    (prompts_dir / "guardian.md").write_text(
        "---\nname: guardian\n---\n\n## 职责\n\n内容\n",
        encoding="utf-8",
    )
    (agents_dir / "guardian.md").write_text(
        "---\nname: guardian\n---\n\n## 红线\n\n已有红线\n",
        encoding="utf-8",
    )

    result = _run(scripts_dir)

    assert result.returncode == 0
    # prompts 无该章节 → 跳过，agents 版红线保持原样
    agents_content = (agents_dir / "guardian.md").read_text(encoding="utf-8")
    assert "已有红线" in agents_content
    assert "0 处更新" in result.stdout


# ---------- 6. agents 版不存在对应角色：跳过 ----------

def test_sync_skips_role_without_agents_file(tmp_path):
    scripts_dir, prompts_dir, agents_dir = _setup_env(tmp_path)
    # prompts 有，但 agents 没有对应文件
    (prompts_dir / "only-prompts.md").write_text(
        "---\nname: only-prompts\n---\n\n## 红线\n\n内容\n",
        encoding="utf-8",
    )

    result = _run(scripts_dir)

    assert result.returncode == 0
    assert "同步完成" in result.stdout
