#!/bin/bash
# Skill Index 搜索脚本
# 扫描所有 skill 目录，匹配 front matter 中的 name 和 description
# 用法: echo "查询词" | bash search.sh

set -euo pipefail

# 收集所有 skill 目录路径
SKILL_DIRS=()
for d in \
    "$HOME/.claude/skills" \
    "$HOME/.agents/skills" \
    "$HOME/.config/opencode/agents" \
    ".opencode/skills"; do
    [ -d "$d" ] && SKILL_DIRS+=("$d")
done

if [ ${#SKILL_DIRS[@]} -eq 0 ]; then
    echo "未找到任何 skill 目录" >&2
    exit 1
fi

read -r query
query_lower=$(echo "$query" | tr '[:upper:]' '[:lower:]')

echo "=== Skill Index 搜索结果 ==="
echo "查询: $query"
echo ""

matches=0
seen=""

for dir in "${SKILL_DIRS[@]}"; do
    for skill_md in "$dir"/*/SKILL.md; do
        [ -f "$skill_md" ] || continue
        skill_name=$(basename "$(dirname "$skill_md")")

        # 去重
        grep -q " $skill_name " <<<" $seen " && continue
        seen="$seen $skill_name"

        # 提取 description（|| true 防无 description 中断）
        fm=$(sed -n '/^---$/,/^---$/p' "$skill_md" 2>/dev/null)
        desc=$(grep "^description:" <<<"$fm" 2>/dev/null | head -1 | sed 's/^description: *//' || true)
        [ -z "$desc" ] && desc="（无描述）"

        # 匹配
        if grep -qi "$query_lower" <<<"$skill_name $desc" 2>/dev/null; then
            path_label=$(sed "s|$HOME|~|" <<<"$dir")
            echo "  - $skill_name ($path_label): $desc"
            matches=$((matches + 1))
        fi
    done
done

echo ""
if [ "$matches" -eq 0 ]; then
    echo "未找到匹配的 skill，尝试用更通用的关键词搜索"
else
    echo "找到 $matches 个匹配 skill，请选择最相关的调用"
fi
