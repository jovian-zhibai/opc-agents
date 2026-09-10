"""测试：.pi/SYSTEM.md（Pi Director 运行时入口）与生成器派生结果一致。

背景（2026-09-10 审查发现）：SYSTEM.md 历史上手工维护（f5c041d），
改 prompts/director.md 后 CI 只再生 .pi/agents/，入口文件不会跟着动——
Pi 运行时的 Director 身份可静默漂移。现派生规则已纳入 generate-agents.py
（director_entry.source=derived），本测试锁死「派生结果 == 仓库中文件」：
任何人改了 prompts/ 或生成规则但忘了 --write 重建 SYSTEM.md，测试即报错。
"""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# 先让 pyyaml 可被 generate-agents 导入（CI 环境有；本地缺则整体跳过）
pytest.importorskip("yaml")


def _load_generator():
    path = SCRIPTS_DIR / "generate-agents.py"
    spec = importlib.util.spec_from_file_location("generate_agents", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load_generator()

SYSTEM_MD = PROJECT_ROOT / ".pi" / "SYSTEM.md"
PI_DIRECTOR = PROJECT_ROOT / ".pi" / "agents" / "director.md"


@pytest.mark.skipif(not SYSTEM_MD.exists(), reason=".pi/SYSTEM.md 不存在")
def test_system_md_matches_derivation():
    """派生规则必须逐字节重现仓库中的 .pi/SYSTEM.md。"""
    derived = gen.derive_pi_system_md(PI_DIRECTOR.read_text(encoding="utf-8"))
    current = SYSTEM_MD.read_text(encoding="utf-8")
    assert derived == current, (
        ".pi/SYSTEM.md 与派生结果不一致——改过 prompts/director.md 或派生规则？\n"
        "修复：python3 scripts/generate-agents.py --runtime=pi --all --write"
    )


@pytest.mark.skipif(not SYSTEM_MD.exists(), reason=".pi/SYSTEM.md 不存在")
def test_system_md_no_front_matter_or_mirror_line():
    """入口文件不应含 front matter / mirror 注入行（那是 agents/ 产物的特征）。"""
    text = SYSTEM_MD.read_text(encoding="utf-8")
    assert not text.startswith("---"), "SYSTEM.md 不应带 YAML front matter"
    assert "此文件 mirror" not in text, "SYSTEM.md 不应含 mirror 注入行"


@pytest.mark.skipif(not SYSTEM_MD.exists(), reason=".pi/SYSTEM.md 不存在")
def test_system_md_link_depth():
    """链接深度：SYSTEM.md 在 .pi/（比 agents/ 浅一层），指向仓库根的链接应为 ../../。"""
    text = SYSTEM_MD.read_text(encoding="utf-8")
    assert "](../../routing.yaml)" in text
    assert "](../../../feedback.schema.json)" in text
    assert "](../routing.yaml)" not in text, "入口层不应出现 agents 层深度"


def test_pi_adapter_declares_derived_source():
    """adapters/pi.yaml 必须声明 director_entry.source=derived（生成链启用的开关）。"""
    yaml = pytest.importorskip("yaml")
    cfg = yaml.safe_load((PROJECT_ROOT / "adapters" / "pi.yaml").read_text(encoding="utf-8"))
    entry = cfg.get("director_entry", {})
    assert entry.get("file") == ".pi/SYSTEM.md"
    assert entry.get("source") == "derived", (
        "director_entry.source 应为 derived（入口纳入生成链），当前: "
        f"{entry.get('source')!r}"
    )
