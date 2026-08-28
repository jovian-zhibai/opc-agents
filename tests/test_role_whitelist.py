"""测试：生成器角色白名单防呆——非白名单 .md 文件不生成垃圾 agent。

背景：list_prompt_roles() 原来用 glob("*.md") 把 prompts/ 下所有 .md 当角色，
放一个 stray 文件（如 README.md、draft.md）会生成垃圾 agent。
现在加固定 10 角色白名单（与 ci.yml EXPECTED 同源），非白名单跳过并告警。
"""
import sys
import importlib
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _load_generate_agents():
    """加载 generate-agents.py（文件名带连字符，需 importlib）。"""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("generate_agents", SCRIPTS_DIR / "generate-agents.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


generate_agents = _load_generate_agents()


class TestRoleWhitelist:
    """测试角色白名单防呆。"""

    def test_known_roles_constant_has_10_roles(self):
        """KNOWN_ROLES 常量包含 10 个角色，与 ci.yml EXPECTED 同源。"""
        expected = {
            "advisor", "agent-manager", "dev", "director", "finance",
            "growth", "guardian", "product", "qa", "ui-ux",
        }
        assert generate_agents.KNOWN_ROLES == expected
        assert len(generate_agents.KNOWN_ROLES) == 10

    def test_list_prompt_roles_returns_only_known(self, tmp_path, monkeypatch):
        """list_prompt_roles() 只返回白名单内的角色，不含 stray 文件。"""
        # 创建临时 prompts 目录
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        # 放 3 个已知角色 + 2 个 stray 文件
        for role in ["advisor", "dev", "director"]:
            (prompts_dir / f"{role}.md").write_text(f"# {role}\n")
        (prompts_dir / "_stray.md").write_text("# stray\n")
        (prompts_dir / "README.md").write_text("# readme\n")

        monkeypatch.setattr(generate_agents, "PROMPTS_DIR", prompts_dir)
        roles = generate_agents.list_prompt_roles()

        assert set(roles) == {"advisor", "dev", "director"}
        assert "_stray" not in roles
        assert "README" not in roles

    def test_stray_file_does_not_generate_agent(self, tmp_path, monkeypatch, capsys):
        """stray 文件不会触发生成器产出 agent 文件。"""
        # 创建临时项目结构
        project_dir = tmp_path / "project"
        prompts_dir = project_dir / "prompts"
        adapters_dir = project_dir / "adapters"
        output_dir = project_dir / "output"
        prompts_dir.mkdir(parents=True)
        adapters_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        # 放一个已知角色 + 一个 stray
        (prompts_dir / "advisor.md").write_text("---\ndescription: test\n---\n# advisor\n")
        (prompts_dir / "_stray.md").write_text("# stray\n")

        # 创建一个最小 adapter
        (adapters_dir / "test.yaml").write_text(f"""
runtime: test
name: Test
agent_format:
  type: plain_markdown
  output_dir: {output_dir}/
  file_extension: .md
front_matter:
  enabled: false
path_replace:
  default: []
""")

        monkeypatch.setattr(generate_agents, "PROJECT_DIR", project_dir)
        monkeypatch.setattr(generate_agents, "PROMPTS_DIR", prompts_dir)
        monkeypatch.setattr(generate_agents, "ADAPTERS_DIR", adapters_dir)

        # 跑 --all 生成（main() 正常返回，不抛 SystemExit）
        sys.argv = ["generate-agents.py", "--runtime=test", "--all", "--write"]
        generate_agents.main()

        # 验证：只生成了 advisor，没有生成 _stray
        generated = list(output_dir.glob("*.md"))
        generated_names = [f.stem for f in generated]
        assert "advisor" in generated_names
        assert "_stray" not in generated_names

        # 验证：stderr 有跳过告警
        captured = capsys.readouterr()
        assert "_stray" in captured.err or "跳过" in captured.err

    def test_all_10_known_roles_exist_in_prompts(self):
        """仓库实际 prompts/ 目录包含全部 10 个白名单角色。"""
        roles = generate_agents.list_prompt_roles()
        assert len(roles) == 10
        assert set(roles) == generate_agents.KNOWN_ROLES
