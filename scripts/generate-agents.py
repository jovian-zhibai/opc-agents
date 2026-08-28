#!/usr/bin/env python3
"""OPC Agent 多运行时生成器 — 从 prompts/（唯一真相源）+ adapter 配置生成各运行时的 Agent 定义文件。

用法:
  python3 scripts/generate-agents.py --runtime=opencode [--role=dev] [--write]
  python3 scripts/generate-agents.py --runtime=opencode --all          # 批量 dry-run
  python3 scripts/generate-agents.py --list                              # 列出可用运行时

设计:
  - prompts/ 是唯一真相源（运行时无关的纯角色定义）
  - adapters/<runtime>.yaml 定义该运行时的转换规则
  - 生成器从配置读取规则，输出运行时特定的 Agent 定义文件
  - 新增运行时只需写一个 adapter 配置，不改生成器
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ 需要 PyYAML：pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
PROMPTS_DIR = PROJECT_DIR / "prompts"
ADAPTERS_DIR = PROJECT_DIR / "adapters"

# ─── 工具函数 ───

def load_adapter(runtime: str) -> dict:
    """加载 adapter 配置。"""
    config_path = ADAPTERS_DIR / f"{runtime}.yaml"
    if not config_path.exists():
        print(f"❌ 找不到 adapter 配置: {config_path}", file=sys.stderr)
        print(f"   可用运行时: {list_available_runtimes()}", file=sys.stderr)
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_available_runtimes() -> list:
    """列出可用的运行时（adapters/ 目录下的 .yaml 文件）。"""
    if not ADAPTERS_DIR.exists():
        return []
    return sorted([p.stem for p in ADAPTERS_DIR.glob("*.yaml")])


def list_prompt_roles() -> list:
    """列出 prompts/ 目录下的所有角色。"""
    if not PROMPTS_DIR.exists():
        return []
    return sorted([p.stem for p in PROMPTS_DIR.glob("*.md")])


def strip_leading_front_matter(content: str) -> str:
    """去除 markdown 文件开头的迷你 front matter（第一个 --- 到第二个 --- 之间的内容）。"""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return content
    # 找第二个 ---
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            # 跳过 front matter 和后面的空行
            remaining = lines[i + 1:]
            # 去掉开头空行
            while remaining and remaining[0].strip() == "":
                remaining.pop(0)
            return "\n".join(remaining)
    return content


def remove_sections(content: str, sections_to_remove: list) -> str:
    """去除指定的 markdown 章节（从 ## 标题到下一个 ## 标题之间的内容）。"""
    if not sections_to_remove:
        return content
    lines = content.split("\n")
    result = []
    skip = False
    for line in lines:
        # 检测新的 ## 章节
        if re.match(r"^##\s", line):
            skip = False
            for sec in sections_to_remove:
                if line.strip().startswith(sec):
                    skip = True
                    break
        if not skip:
            result.append(line)
    return "\n".join(result)


def apply_path_replace(content: str, role: str, path_replace_config: dict) -> str:
    """应用路径前缀替换规则，支持按角色覆盖。"""
    if not path_replace_config:
        return content
    # 先看有没有角色特定的覆盖
    overrides = path_replace_config.get("overrides", {})
    if role in overrides:
        rules = overrides[role]
    else:
        rules = path_replace_config.get("default", [])
    if not rules:
        return content
    for rule in rules:
        content = content.replace(rule["from"], rule["to"])
    return content


def extract_front_matter(file_path: Path) -> str:
    """从现有文件提取 YAML front matter（第一个 --- 到第二个 --- 之间的内容，包含 ---）。"""
    if not file_path.exists():
        return ""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    fm_lines = ["---"]
    for i in range(1, len(lines)):
        fm_lines.append(lines[i])
        if lines[i].strip() == "---":
            break
    return "\n".join(fm_lines)


def inject_content(content: str, inject_configs: list, role: str) -> str:
    """在指定位置注入内容。"""
    if not inject_configs:
        return content
    for cfg in inject_configs:
        position = cfg.get("position", "before_body")
        text = cfg.get("content", "").replace("{{role}}", role)
        # 去掉末尾多余的换行
        text = text.rstrip("\n")
        if position == "after_front_matter":
            # 在 front matter 之后注入（front matter 以 --- 结尾）
            lines = content.split("\n")
            if lines and lines[0].strip() == "---":
                # 找第二个 ---
                for i in range(1, len(lines)):
                    if lines[i].strip() == "---":
                        # 在第二个 --- 之后注入
                        before = "\n".join(lines[:i + 1])
                        after = "\n".join(lines[i + 1:])
                        # 去掉 after 开头空行
                        after_lines = after.split("\n")
                        while after_lines and after_lines[0].strip() == "":
                            after_lines.pop(0)
                        after = "\n".join(after_lines)
                        content = f"{before}\n\n{text}\n\n{after}"
                        break
        elif position == "before_body":
            content = f"{text}\n\n{content}"
        elif position == "after_body":
            content = f"{content}\n\n{text}"
    return content


def inject_managed_block(entry_file: Path, block_content: str, block_type: str = "markdown", write: bool = False) -> dict:
    """注入/替换入口文件中的标记块内容。只替换标记块内，块外保持不动。"""
    if not entry_file.exists():
        return {"error": f"入口文件不存在: {entry_file}"}

    with open(entry_file, encoding="utf-8") as f:
        content = f.read()

    if block_type == "markdown":
        start_marker = "<!-- OPC:GENERATED:START -->"
        end_marker = "<!-- OPC:GENERATED:END -->"
    elif block_type == "toml":
        start_marker = "# OPC:GENERATED:START"
        end_marker = "# OPC:GENERATED:END"
    else:
        return {"error": f"不支持的 block_type: {block_type}"}

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        return {"error": f"未找到标记块 {start_marker} / {end_marker}，请先手动添加标记块"}

    if end_idx < start_idx:
        return {"error": "标记块顺序错误"}

    # 替换标记块内内容（保留标记本身）
    before = content[:start_idx + len(start_marker)]
    after = content[end_idx:]
    new_content = f"{before}\n{block_content.rstrip()}\n{after}"

    if write:
        with open(entry_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        return {"written": True, "file": str(entry_file)}
    else:
        # dry-run：写到 /tmp，统计差异
        import subprocess
        tmp_file = Path(f"/tmp/gen-block-{entry_file.name}")
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        result = subprocess.run(
            ["diff", str(entry_file), str(tmp_file)],
            capture_output=True, text=True
        )
        diff_lines = [l for l in result.stdout.split("\n") if l.startswith(("<", ">"))]
        return {"diff_count": len(diff_lines), "tmp_file": str(tmp_file)}


def generate_role(role: str, adapter_config: dict, write: bool = False) -> dict:
    """生成单个角色的 Agent 定义文件。返回差异统计。"""
    runtime = adapter_config["runtime"]
    agent_format = adapter_config.get("agent_format", {})
    output_dir = PROJECT_DIR / agent_format.get("output_dir", f".{runtime}/agents/")
    output_file = output_dir / f"{role}{agent_format.get('file_extension', '.md')}"
    prompts_file = PROMPTS_DIR / f"{role}.md"

    if not prompts_file.exists():
        print(f"  ❌ {role}: prompts/{role}.md 不存在", file=sys.stderr)
        return {"role": role, "error": "prompts file not found"}

    # 1. 读取 prompts 正文
    with open(prompts_file, encoding="utf-8") as f:
        content = f.read()

    # 2. 预处理：去除开头的迷你 front matter
    source_preprocess = adapter_config.get("source_preprocess", {})
    if source_preprocess.get("strip_leading_front_matter", False):
        content = strip_leading_front_matter(content)

    # 3. 去除指定章节
    sections_config = adapter_config.get("sections", {})
    content = remove_sections(content, sections_config.get("remove", []))

    # 4. 路径前缀替换
    content = apply_path_replace(content, role, adapter_config.get("path_replace", {}))

    # 5. 处理 front matter（先拼接 front matter，再注入内容，确保 after_front_matter 位置正确）
    fm_config = adapter_config.get("front_matter", {})
    if fm_config.get("enabled", False):
        if fm_config.get("source") == "existing":
            # 从现有输出文件提取 front matter
            existing_fm = extract_front_matter(output_file)
            if existing_fm:
                # 去掉 content 开头可能存在的 front matter（prompts 版没有，但保险起见）
                content = strip_leading_front_matter(content)
                content = f"{existing_fm}\n\n{content}"
        # template 模式未来实现

    # 6. 注入内容（在 front matter 拼接之后，确保 after_front_matter 位置正确）
    content = inject_content(content, sections_config.get("inject", []), role)

    # 7. 去掉末尾多余空行
    content = content.rstrip("\n") + "\n"

    # 7.5. TOML 格式转换（Codex 等运行时使用 TOML 而非 markdown + YAML front matter）
    agent_format = adapter_config.get("agent_format", {})
    if agent_format.get("type") == "toml":
        # 从 OpenCode 版提取 description（作为 fallback）
        opencode_file = PROJECT_DIR / ".opencode/agents" / f"{role}.md"
        description = ""
        if opencode_file.exists():
            with open(opencode_file, encoding="utf-8") as f:
                oc_content = f.read()
            lines = oc_content.split("\n")
            fm_content = []
            if lines and lines[0].strip() == "---":
                for i in range(1, len(lines)):
                    if lines[i].strip() == "---":
                        break
                    fm_content.append(lines[i])
            try:
                oc_fm = yaml.safe_load("\n".join(fm_content))
                description = oc_fm.get("description", "")
            except Exception:
                pass

        # 从 adapter 配置读取 TOML 字段
        toml_fields = adapter_config.get("toml_fields", {})
        model = toml_fields.get("model", "gpt-4o")
        reasoning_effort = toml_fields.get("model_reasoning_effort", "medium")

        # 生成 TOML 内容
        # developer_instructions 用三引号字符串，需要转义内部的三引号
        body = content.rstrip("\n")
        body_escaped = body.replace("'''", "\\'\\'\\'")

        toml_content = f'''name = "{role}"
description = "{description}"
model = "{model}"
model_reasoning_effort = "{reasoning_effort}"

developer_instructions = \'\'\'
{body_escaped}
\'\'\'
'''
        content = toml_content
        # 修改输出文件扩展名为 .toml
        output_file = output_dir / f"{role}.toml"

    # 8. 输出
    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ {role}: 已写入 {output_file.relative_to(PROJECT_DIR)}")
        return {"role": role, "written": True}
    else:
        # dry-run：写到 /tmp，统计差异
        tmp_file = Path(f"/tmp/gen-{runtime}-{role}.md")
        tmp_file.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(content)
        # 统计差异
        if output_file.exists():
            import subprocess
            result = subprocess.run(
                ["diff", str(tmp_file), str(output_file)],
                capture_output=True, text=True
            )
            diff_lines = [l for l in result.stdout.split("\n") if l.startswith(("<", ">"))]
            diff_count = len(diff_lines)
        else:
            diff_count = "N/A（目标文件不存在）"
        print(f"  {role}: {diff_count} 行差异")
        return {"role": role, "diff_count": diff_count, "tmp_file": str(tmp_file)}


# ─── 主逻辑 ───

def main():
    parser = argparse.ArgumentParser(description="OPC Agent 多运行时生成器")
    parser.add_argument("--runtime", "-r", help="运行时名称（如 opencode / claude-code / pi）")
    parser.add_argument("--role", help="单个角色名称（如 dev / advisor）")
    parser.add_argument("--all", action="store_true", help="批量生成所有角色（dry-run）")
    parser.add_argument("--write", action="store_true", help="直接写入目标文件（默认 dry-run）")
    parser.add_argument("--list", action="store_true", help="列出可用运行时")
    parser.add_argument("--entry-block", help="入口文件标记块注入（如 CLAUDE.md），需配合 --section 使用")
    parser.add_argument("--section", help="从 prompts/director.md 提取的节名（如 红线），配合 --entry-block 使用")
    parser.add_argument("--block-type", default="markdown", choices=["markdown", "toml"], help="标记块类型（默认 markdown）")
    args = parser.parse_args()

    if args.list:
        runtimes = list_available_runtimes()
        print("可用运行时:")
        for r in runtimes:
            config = load_adapter(r)
            print(f"  - {r}: {config.get('name', r)} — {config.get('description', '')}")
        return

    # --entry-block 模式：从 prompts/director.md 提取指定节并注入入口文件标记块
    if args.entry_block:
        if not args.section:
            print("❌ --entry-block 需配合 --section 使用（如 --section 红线）", file=sys.stderr)
            sys.exit(1)
        entry_file = PROJECT_DIR / args.entry_block
        if not entry_file.exists():
            print(f"❌ 入口文件不存在: {entry_file}", file=sys.stderr)
            sys.exit(1)
        # 从 prompts/director.md 提取指定节
        prompts_file = PROMPTS_DIR / "director.md"
        with open(prompts_file, encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")
        start = None
        end = None
        section_header = f"## {args.section}"
        for i, line in enumerate(lines):
            if line.strip() == section_header:
                start = i
            elif start is not None and line.startswith("## ") and i > start:
                end = i
                break
        if start is None:
            print(f"❌ 在 prompts/director.md 中未找到节: {section_header}", file=sys.stderr)
            sys.exit(1)
        if end is None:
            end = len(lines)
        block_content = "\n".join(lines[start:end]).rstrip()
        print(f"=== 入口文件标记块注入 ===")
        print(f"    入口文件: {entry_file.relative_to(PROJECT_DIR)}")
        print(f"    提取节: {section_header} ({len(block_content)} 字符)")
        print(f"    标记块类型: {args.block_type}")
        print(f"    模式: {'写入' if args.write else 'dry-run'}")
        print()
        result = inject_managed_block(entry_file, block_content, block_type=args.block_type, write=args.write)
        if "error" in result:
            print(f"❌ {result['error']}", file=sys.stderr)
            sys.exit(1)
        if args.write:
            print(f"✅ 已写入标记块: {entry_file.relative_to(PROJECT_DIR)}")
        else:
            diff_count = result.get("diff_count", 0)
            print(f"  标记块差异: {diff_count} 行")
            if diff_count == 0:
                print("✅ 标记块与 prompts/director.md 同步")
            else:
                print("⚠️  标记块与 prompts/director.md 不同步，需运行 --write 更新")
        return

    if not args.runtime:
        print("❌ 请指定 --runtime 或使用 --list 查看可用运行时", file=sys.stderr)
        sys.exit(1)

    adapter_config = load_adapter(args.runtime)
    print(f"=== 生成运行时: {adapter_config.get('name', args.runtime)} ===")
    print(f"    输出目录: {adapter_config.get('agent_format', {}).get('output_dir', 'N/A')}")
    print(f"    模式: {'写入' if args.write else 'dry-run'}")
    print()

    if args.all:
        roles = list_prompt_roles()
        # 所有角色均已纳入单源生成（director 于 2026-08-28 纳入）
        print(f"批量生成 {len(roles)} 个角色:")
        results = []
        for role in roles:
            results.append(generate_role(role, adapter_config, write=args.write))
        print()
        print("=== 说明 ===")
        print("  0 行 = 生成结果与现有版本完全一致")
        print("  少量行 = 格式差异，属单源统一的预期效果")
        print("  大量行 = 有实质内容差异，需排查转换规则")
    elif args.role:
        generate_role(args.role, adapter_config, write=args.write)
    else:
        print("❌ 请指定 --role 或 --all", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
