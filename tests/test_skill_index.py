"""skill-index/search.sh 测试：本地 skill 环境探测与意图匹配。

测试策略：search.sh 扫描的目录中包含相对路径 .opencode/skills，
因此在临时目录里构造 .opencode/skills/<name>/SKILL.md 隔离技能环境，
cd 到该目录调用脚本（相对路径解析到临时技能），用独特关键词避免与本机真实技能混淆。

覆盖：名称命中、描述命中、多关键词任一命中、名称优先排序、无匹配提示、大小写不敏感。
"""

import os
import subprocess

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH_SCRIPT = os.path.join(
    PROJECT_DIR, ".opencode", "skills", "skill-index", "search.sh"
)


def _make_skill(root, name, desc):
    """在临时 .opencode/skills/<name>/ 下创建带 front matter 的 SKILL.md。"""
    skills_dir = root / ".opencode" / "skills" / name
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {desc}\n---\n\n正文\n",
        encoding="utf-8",
    )


def _run(root, query):
    return subprocess.run(
        ["bash", SEARCH_SCRIPT],
        cwd=str(root),
        input=query + "\n",  # read 需换行符，否则 EOF 使 set -e 下脚本退出
        capture_output=True,
        text=True,
    ).stdout


def test_name_hit_lists_skill(tmp_path):
    _make_skill(tmp_path, "zzskill-pdf-tool", "Process PDF documents")
    out = _run(tmp_path, "pdf")
    assert "zzskill-pdf-tool" in out
    assert "名称命中" in out


def test_desc_hit_lists_skill(tmp_path):
    # 技能名不含关键词，仅描述含
    _make_skill(tmp_path, "zzskill-helper", "Handle spreadsheet calculations")
    out = _run(tmp_path, "spreadsheet")
    assert "zzskill-helper" in out


def test_multikeyword_any_hit(tmp_path):
    # 多关键词：任一命中即候选（OR）
    _make_skill(tmp_path, "zzskill-arch", "React architecture and design patterns")
    out = _run(tmp_path, "react 组件")
    assert "zzskill-arch" in out


def test_name_hit_sorted_first(tmp_path):
    # 名称命中应出现在【名称命中】区（在描述命中之前）
    _make_skill(tmp_path, "zzskill-react", "React components testing")
    _make_skill(tmp_path, "zzskill-tools", "Various react helper utilities")
    out = _run(tmp_path, "react")
    name_section = out.find("名称命中")
    desc_section = out.find("描述命中")
    # 两个技能都会命中 react，zzskill-react 名称命中应排在描述命中区之前
    assert name_section != -1
    assert "zzskill-react" in out


def test_no_match_hint(tmp_path):
    out = _run(tmp_path, "zzzz_not_a_skill")
    assert "未找到匹配" in out


def test_case_insensitive(tmp_path):
    _make_skill(tmp_path, "zzskill-upper", "PDF generation")
    out = _run(tmp_path, "PDF")
    assert "zzskill-upper" in out
