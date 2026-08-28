"""测试：生成的 agent 文件必须有完整的 front matter，缺失即 fail。

背景：front matter 从 adapter template 配置生成（单源模式），不再从产物捞。
如果配置缺失或生成器出错，产物会丢失 front matter（模型温度/工具权限/skill 声明全丢）。
本测试确保每个运行时每个角色的生成文件都有合法的 front matter。
"""
import yaml
import pytest
from pathlib import Path

# 运行时 → 输出目录配置
RUNTIME_CONFIGS = {
    "opencode": {"dir": ".opencode/agents", "ext": ".md", "has_front_matter": True},
    "claude-code": {"dir": ".claude/agents", "ext": ".md", "has_front_matter": True},
    "pi": {"dir": ".pi/agents", "ext": ".md", "has_front_matter": True},
    "gemini": {"dir": ".gemini/agents", "ext": ".md", "has_front_matter": True},
    # codex 用 TOML 格式，不走 front matter 检查（由 test_toml_serialization.py 覆盖）
}

ROLES = [
    "advisor", "agent-manager", "dev", "director", "finance",
    "growth", "guardian", "product", "qa", "ui-ux"
]

# 某些运行时的某些角色没有 front matter（如 director 在 claude-code/pi/gemini 走入口文件，不走 agent front matter）
NO_FRONT_MATTER_EXCEPTIONS = {
    ("claude-code", "director"),
    ("pi", "director"),
    ("gemini", "director"),
}


def _extract_front_matter(content: str):
    """从 markdown 内容提取 YAML front matter，返回 (fm_dict, raw_text)。"""
    if not content.startswith("---"):
        return None, None
    end = content.find("---", 3)
    if end == -1:
        return None, None
    raw = content[4:end]
    try:
        fm = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None, raw
    return fm, raw


class TestFrontMatterIntegrity:
    """测试每个生成文件的 front matter 完整性。"""

    @pytest.mark.parametrize("runtime", RUNTIME_CONFIGS.keys())
    @pytest.mark.parametrize("role", ROLES)
    def test_file_exists(self, runtime, role):
        """生成文件必须存在。"""
        config = RUNTIME_CONFIGS[runtime]
        file_path = Path(config["dir"]) / f"{role}{config['ext']}"
        assert file_path.exists(), f"{runtime}/{role} 生成文件不存在: {file_path}"

    @pytest.mark.parametrize("runtime", RUNTIME_CONFIGS.keys())
    @pytest.mark.parametrize("role", ROLES)
    def test_has_front_matter(self, runtime, role):
        """生成文件必须有 front matter（以 --- 开头）。"""
        if (runtime, role) in NO_FRONT_MATTER_EXCEPTIONS:
            pytest.skip(f"{runtime}/{role} 设计上无 front matter")

        config = RUNTIME_CONFIGS[runtime]
        file_path = Path(config["dir"]) / f"{role}{config['ext']}"
        content = file_path.read_text(encoding="utf-8")

        assert content.startswith("---"), (
            f"{runtime}/{role} 缺少 front matter（不以 --- 开头）。"
            f"可能是 adapter template 配置缺失或生成器出错。"
        )

    @pytest.mark.parametrize("runtime", RUNTIME_CONFIGS.keys())
    @pytest.mark.parametrize("role", ROLES)
    def test_front_matter_valid_yaml(self, runtime, role):
        """front matter 必须是合法 YAML。"""
        if (runtime, role) in NO_FRONT_MATTER_EXCEPTIONS:
            pytest.skip(f"{runtime}/{role} 设计上无 front matter")

        config = RUNTIME_CONFIGS[runtime]
        file_path = Path(config["dir"]) / f"{role}{config['ext']}"
        content = file_path.read_text(encoding="utf-8")

        fm, raw = _extract_front_matter(content)
        assert fm is not None, (
            f"{runtime}/{role} front matter 不是合法 YAML。原始内容:\n{raw}"
        )
        assert isinstance(fm, dict), f"{runtime}/{role} front matter 解析结果不是 dict"

    @pytest.mark.parametrize("runtime", RUNTIME_CONFIGS.keys())
    @pytest.mark.parametrize("role", ROLES)
    def test_front_matter_has_description(self, runtime, role):
        """front matter 必须包含 description 字段（从 prompts/ 提取，唯一源）。"""
        if (runtime, role) in NO_FRONT_MATTER_EXCEPTIONS:
            pytest.skip(f"{runtime}/{role} 设计上无 front matter")

        config = RUNTIME_CONFIGS[runtime]
        file_path = Path(config["dir"]) / f"{role}{config['ext']}"
        content = file_path.read_text(encoding="utf-8")

        fm, _ = _extract_front_matter(content)
        assert fm is not None
        assert "description" in fm, (
            f"{runtime}/{role} front matter 缺少 description 字段。"
            f"description 应从 prompts/{role}.md 的 front matter 提取。"
        )
        assert isinstance(fm["description"], str)
        assert len(fm["description"]) > 0, f"{runtime}/{role} description 为空"

    def test_no_placeholder_in_front_matter(self):
        """front matter 中不应包含未解析的占位符（如 {{DESCRIPTION}}）。"""
        for runtime, config in RUNTIME_CONFIGS.items():
            for role in ROLES:
                if (runtime, role) in NO_FRONT_MATTER_EXCEPTIONS:
                    continue
                file_path = Path(config["dir"]) / f"{role}{config['ext']}"
                content = file_path.read_text(encoding="utf-8")
                fm, raw = _extract_front_matter(content)
                if raw:
                    assert "{{" not in raw, (
                        f"{runtime}/{role} front matter 包含未解析的占位符:\n{raw}"
                    )
