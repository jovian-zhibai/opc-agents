#!/bin/bash
# Skill Index 搜索脚本
# 扫描 skill 目录，匹配 front matter 中的 name 和 description
# 用法: echo "查询词" | bash search.sh

set -euo pipefail

# 自动检测 skill 目录（Claude Code vs OpenCode）
SKILL_DIR=""
if [ -d "$HOME/.claude/skills" ]; then
    SKILL_DIR="$HOME/.claude/skills"
elif [ -d ".opencode/skills" ]; then
    SKILL_DIR=".opencode/skills"
else
    echo "未找到 skill 目录" >&2
    exit 1
fi

read -r query
query_lower=$(echo "$query" | tr '[:upper:]' '[:lower:]')

echo "=== Skill Index 搜索结果 ==="
echo "查询: $query"
echo ""

matches=0
for skill_md in "$SKILL_DIR"/*/SKILL.md; do
    [ -f "$skill_md" ] || continue
    skill_name=$(basename "$(dirname "$skill_md")")
    
    # 提取 YAML front matter 中的 description
    fm=$(sed -n '/^---$/,/^---$/p' "$skill_md" 2>/dev/null)
    desc=$(echo "$fm" | grep "^description:" | head -1 | sed 's/^description: *//')
    [ -z "$desc" ] && desc="（无描述）"
    
    # 匹配：name 或 description 包含查询词（大小写不敏感）
    if echo "$skill_name $desc" | grep -qi "$query_lower"; then
        echo "  - $skill_name: $desc"
        matches=$((matches + 1))
    fi
done

echo ""
if [ "$matches" -eq 0 ]; then
    echo "未找到匹配的 skill，尝试用更通用的关键词搜索"
else
    echo "找到 $matches 个匹配 skill，请选择最相关的调用"
fi
