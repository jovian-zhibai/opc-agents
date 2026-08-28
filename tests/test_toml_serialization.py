"""TOML 序列化健壮性测试。

覆盖：
1. 对抗性单元测试：直接给 serialize_toml_agent 喂含 '''、\\、\"、end''' 等的正文，
   断言 round-trip 解析后与原文逐字一致（守住"能解析但内容被静默篡改"的 bug）。
2. 全量 .codex/agents/*.toml 可被 tomllib 解析。
"""
import importlib.util
import sys
from pathlib import Path

import pytest
import tomllib

# 把 scripts/ 加入 path，导入生成器（文件名带连字符，需用 importlib 加载）
PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"


def _load_generate_agents():
    path = str(SCRIPTS_DIR / "generate-agents.py")
    spec = importlib.util.spec_from_file_location("generate_agents", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


generate_agents = _load_generate_agents()
serialize_toml_agent = generate_agents.serialize_toml_agent


# ─── 对抗性正文用例 ───

ADVERSARIAL_BODIES = [
    # 含三引号（原 bug 触发点）
    (
        "triple_quote_middle",
        "开头\n包含三引号: '''这里是三引号内容'''\n结尾",
    ),
    # 三引号紧贴结尾（end'''）
    (
        "triple_quote_at_end",
        "正文内容\n结尾三引号'''",
    ),
    # 三引号紧贴开头
    (
        "triple_quote_at_start",
        "'''开头三引号\n正文内容",
    ),
    # 连续多个三引号
    (
        "multiple_triple_quotes",
        "a'''b'''c'''d",
    ),
    # 含反斜杠（literal string 中是字面量，basic string 中需转义）
    (
        "backslash_path",
        "Windows 路径: C:\\Users\\test\\file.txt\n反斜杠结尾\\",
    ),
    # 含双引号（basic string 中需转义）
    (
        "double_quotes",
        '他说："你好"\n连续双引号: """\n结尾双引号"',
    ),
    # 混合：三引号 + 反斜杠 + 双引号
    (
        "mixed_adversarial",
        "三引号: '''内容'''\n反斜杠: C:\\temp\n双引号: \"quote\"\n结尾'''\\",
    ),
    # 空正文
    (
        "empty_body",
        "",
    ),
    # 只有换行
    (
        "only_newlines",
        "\n\n\n",
    ),
    # 含 TOML 特殊字符
    (
        "toml_special_chars",
        "等号 = 井号 # 方括号 [ ] 花括号 { } 逗号 ,\n制表符\t和\r回车",
    ),
    # Unicode + 三引号
    (
        "unicode_triple_quote",
        "中文：'''三引号内容'''\n日文：「」\nemoji: 🚀",
    ),
]


@pytest.mark.parametrize("name,body", ADVERSARIAL_BODIES, ids=[x[0] for x in ADVERSARIAL_BODIES])
def test_serialize_toml_roundtrip_adversarial(name, body):
    """对抗性正文 round-trip：序列化 → tomllib 解析 → developer_instructions 与原文逐字一致。

    这是守住"能解析但内容被静默篡改"bug 的关键测试。
    原 bug：body.replace("'''", "\\'\\'\\'") 把反斜杠转义套在 TOML literal string 上，
    literal string 不支持转义，导致 ''' 被篡改为 \\'\\'\\'（含多余反斜杠）。
    """
    toml_str = serialize_toml_agent(
        role="test-agent",
        description="测试描述",
        developer_instructions=body,
    )

    # 必须能被 tomllib 解析
    parsed = tomllib.loads(toml_str)

    # 字段正确
    assert parsed["name"] == "test-agent"
    assert parsed["description"] == "测试描述"
    # model / model_reasoning_effort 不硬编码，由用户 ~/.codex/config.toml 全局配置决定
    assert "model" not in parsed, "生成的 TOML 不应硬编码 model 字段"
    assert "model_reasoning_effort" not in parsed, "生成的 TOML 不应硬编码 model_reasoning_effort 字段"

    # 关键断言：developer_instructions 与原文逐字一致（rstrip 换行是生成器的约定）
    expected = body.rstrip("\n")
    actual = parsed["developer_instructions"]
    assert actual == expected, (
        f"对抗性正文 round-trip 不一致！\n"
        f"用例: {name}\n"
        f"预期 ({len(expected)} 字符): {repr(expected)}\n"
        f"实际 ({len(actual)} 字符): {repr(actual)}"
    )


def test_all_codex_toml_files_parseable():
    """全量 .codex/agents/*.toml 能被 tomllib 解析，且包含必要字段。"""
    codex_dir = PROJECT_DIR / ".codex" / "agents"
    toml_files = sorted(codex_dir.glob("*.toml"))

    assert len(toml_files) >= 10, f"codex agents 数量不足: {len(toml_files)}"

    for toml_file in toml_files:
        with open(toml_file, "rb") as f:
            parsed = tomllib.load(f)

        # 必要字段存在
        assert "name" in parsed, f"{toml_file.name} 缺少 name 字段"
        assert "developer_instructions" in parsed, f"{toml_file.name} 缺少 developer_instructions 字段"
        assert len(parsed["developer_instructions"]) > 0, f"{toml_file.name} 的 developer_instructions 为空"
