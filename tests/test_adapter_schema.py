"""adapters/*.yaml 结构校验：生成器命脉，字段拼错会静默生成错产物。

本测试锁住 adapter 配置的结构契约，防止加新运行时或改字段时写错 adapter
导致静默生成错误产物。参照 routing.yaml schema 校验的写法，纯 Python 实现，
不引 jsonschema 依赖。

包含：
1. 正向测试：5 个现有 adapter 全部通过校验
2. 反向测试：故意造不合规 adapter（缺必需键/类型错误/未知字段），验证能被拒
"""

import os
import copy

import pytest
import yaml

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAPTERS_DIR = os.path.join(PROJECT_DIR, "adapters")

# 5 个现有 adapter
EXISTING_ADAPTERS = ["opencode", "claude-code", "pi", "gemini", "codex"]

# 共同的必需顶层键
REQUIRED_TOP_KEYS = [
    "runtime", "name", "description", "agent_format",
    "path_replace", "sections", "source_preprocess",
    "scheduling", "file_protection", "detect",
]

# 可选顶层键（允许存在，但不要求）
OPTIONAL_TOP_KEYS = ["front_matter", "toml_fields", "director_entry", "entry"]

# 允许的所有顶层键（用于 additionalProperties 检查）
ALLOWED_TOP_KEYS = set(REQUIRED_TOP_KEYS) | set(OPTIONAL_TOP_KEYS)

# agent_format 必需键
AGENT_FORMAT_REQUIRED = ["type", "output_dir", "file_extension"]

# path_replace 必需键
PATH_REPLACE_REQUIRED = ["default"]

# scheduling 必需键
SCHEDULING_REQUIRED = ["type"]


def validate_adapter(data: dict) -> list:
    """校验一个 adapter 配置，返回错误列表（空列表表示通过）。"""
    errors = []

    if not isinstance(data, dict):
        return ["adapter 必须是 dict（YAML mapping）"]

    # 1. 必需顶层键
    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"缺少必需顶层键: {key}")

    # 2. 未知顶层键
    for key in data:
        if key not in ALLOWED_TOP_KEYS:
            errors.append(f"未知顶层键: {key}（允许的键: {sorted(ALLOWED_TOP_KEYS)}）")

    # 3. 类型校验
    if "runtime" in data and not isinstance(data["runtime"], str):
        errors.append(f"runtime 必须是 str，实际是 {type(data['runtime']).__name__}")
    if "name" in data and not isinstance(data["name"], str):
        errors.append(f"name 必须是 str，实际是 {type(data['name']).__name__}")
    if "description" in data and not isinstance(data["description"], str):
        errors.append(f"description 必须是 str，实际是 {type(data['description']).__name__}")

    # 4. agent_format 子结构
    if "agent_format" in data:
        af = data["agent_format"]
        if not isinstance(af, dict):
            errors.append("agent_format 必须是 dict")
        else:
            for key in AGENT_FORMAT_REQUIRED:
                if key not in af:
                    errors.append(f"agent_format 缺少必需键: {key}")
            if "type" in af and af["type"] not in ("toml", "markdown_yaml_frontmatter", "plain_markdown"):
                errors.append(f"agent_format.type 非法值: {af['type']}（允许: toml / markdown_yaml_frontmatter / plain_markdown）")

    # 5. path_replace 子结构
    if "path_replace" in data:
        pr = data["path_replace"]
        if not isinstance(pr, dict):
            errors.append("path_replace 必须是 dict")
        else:
            for key in PATH_REPLACE_REQUIRED:
                if key not in pr:
                    errors.append(f"path_replace 缺少必需键: {key}")
            if "default" in pr and not isinstance(pr["default"], list):
                errors.append("path_replace.default 必须是 list")

    # 6. sections 子结构
    if "sections" in data and not isinstance(data["sections"], dict):
        errors.append("sections 必须是 dict")

    # 7. source_preprocess 子结构
    if "source_preprocess" in data and not isinstance(data["source_preprocess"], dict):
        errors.append("source_preprocess 必须是 dict")

    # 8. scheduling 子结构
    if "scheduling" in data:
        sc = data["scheduling"]
        if not isinstance(sc, dict):
            errors.append("scheduling 必须是 dict")
        else:
            for key in SCHEDULING_REQUIRED:
                if key not in sc:
                    errors.append(f"scheduling 缺少必需键: {key}")

    # 9. file_protection 子结构
    if "file_protection" in data and not isinstance(data["file_protection"], dict):
        errors.append("file_protection 必须是 dict")

    # 10. detect 子结构
    if "detect" in data and not isinstance(data["detect"], dict):
        errors.append("detect 必须是 dict")

    # 11. front_matter 子结构（可选）
    if "front_matter" in data:
        fm = data["front_matter"]
        if not isinstance(fm, dict):
            errors.append("front_matter 必须是 dict")
        elif "enabled" not in fm:
            errors.append("front_matter 缺少必需键: enabled")

    # 12. toml_fields 子结构（可选，codex 专用）
    if "toml_fields" in data and not isinstance(data["toml_fields"], dict):
        errors.append("toml_fields 必须是 dict")

    # 13. director_entry 子结构（可选）
    if "director_entry" in data and not isinstance(data["director_entry"], dict):
        errors.append("director_entry 必须是 dict")

    # 14. entry 子结构（可选，opencode 专用）
    if "entry" in data and not isinstance(data["entry"], dict):
        errors.append("entry 必须是 dict")

    return errors


# ─── 正向测试：5 个现有 adapter 全部通过 ───

class TestExistingAdapters:
    @pytest.mark.parametrize("runtime", EXISTING_ADAPTERS)
    def test_adapter_file_exists(self, runtime):
        path = os.path.join(ADAPTERS_DIR, f"{runtime}.yaml")
        assert os.path.exists(path), f"adapter 文件不存在: {path}"

    @pytest.mark.parametrize("runtime", EXISTING_ADAPTERS)
    def test_adapter_valid_yaml(self, runtime):
        path = os.path.join(ADAPTERS_DIR, f"{runtime}.yaml")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{runtime}.yaml 解析后不是 dict"

    @pytest.mark.parametrize("runtime", EXISTING_ADAPTERS)
    def test_adapter_passes_schema(self, runtime):
        path = os.path.join(ADAPTERS_DIR, f"{runtime}.yaml")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        errors = validate_adapter(data)
        assert errors == [], f"{runtime}.yaml 校验失败:\n" + "\n".join(f"  - {e}" for e in errors)

    def test_runtime_field_matches_filename(self):
        """adapter 的 runtime 字段必须与文件名一致。"""
        for runtime in EXISTING_ADAPTERS:
            path = os.path.join(ADAPTERS_DIR, f"{runtime}.yaml")
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert data.get("runtime") == runtime, \
                f"{runtime}.yaml 的 runtime 字段 ({data.get('runtime')}) 与文件名不一致"


# ─── 反向测试：故意造不合规 adapter，验证能被拒 ───

class TestSchemaRejectsInvalid:
    def _make_valid_adapter(self):
        """造一个最小合法 adapter，用于反向测试的基础。"""
        return {
            "runtime": "test-runtime",
            "name": "Test Runtime",
            "description": "Test adapter for schema validation",
            "agent_format": {
                "type": "markdown_yaml_frontmatter",
                "output_dir": ".test/agents/",
                "file_extension": ".md",
            },
            "path_replace": {"default": []},
            "sections": {"remove": [], "inject": []},
            "source_preprocess": {"strip_leading_front_matter": True},
            "scheduling": {"type": "mention_tab", "description": "test"},
            "file_protection": {"mechanism": "approval_policy"},
            "detect": {"command": "test", "directory": ".test"},
        }

    def test_valid_adapter_passes(self):
        """基础合法 adapter 必须通过（确保反向测试的基础是对的）。"""
        data = self._make_valid_adapter()
        errors = validate_adapter(data)
        assert errors == [], f"合法 adapter 意外失败: {errors}"

    def test_missing_required_key_rejected(self):
        """缺少必需顶层键必须被拒。"""
        for key in REQUIRED_TOP_KEYS:
            data = self._make_valid_adapter()
            del data[key]
            errors = validate_adapter(data)
            assert any(key in e for e in errors), \
                f"缺少必需键 {key} 未被检测到，errors: {errors}"

    def test_unknown_top_key_rejected(self):
        """未知顶层键必须被拒。"""
        data = self._make_valid_adapter()
        data["unknown_field_xyz"] = "should be rejected"
        errors = validate_adapter(data)
        assert any("unknown_field_xyz" in e for e in errors), \
            f"未知顶层键未被检测到，errors: {errors}"

    def test_wrong_type_rejected(self):
        """字段类型错误必须被拒。"""
        data = self._make_valid_adapter()
        data["runtime"] = 123  # 应该是 str
        errors = validate_adapter(data)
        assert any("runtime" in e and "str" in e for e in errors), \
            f"runtime 类型错误未被检测到，errors: {errors}"

    def test_agent_format_missing_key_rejected(self):
        """agent_format 缺少必需键必须被拒。"""
        data = self._make_valid_adapter()
        del data["agent_format"]["type"]
        errors = validate_adapter(data)
        assert any("agent_format" in e and "type" in e for e in errors), \
            f"agent_format 缺少 type 未被检测到，errors: {errors}"

    def test_agent_format_invalid_type_rejected(self):
        """agent_format.type 非法值必须被拒。"""
        data = self._make_valid_adapter()
        data["agent_format"]["type"] = "invalid_format"
        errors = validate_adapter(data)
        assert any("invalid_format" in e for e in errors), \
            f"agent_format.type 非法值未被检测到，errors: {errors}"

    def test_front_matter_missing_enabled_rejected(self):
        """front_matter 缺少 enabled 必须被拒。"""
        data = self._make_valid_adapter()
        data["front_matter"] = {"source": "existing"}  # 缺 enabled
        errors = validate_adapter(data)
        assert any("front_matter" in e and "enabled" in e for e in errors), \
            f"front_matter 缺少 enabled 未被检测到，errors: {errors}"
