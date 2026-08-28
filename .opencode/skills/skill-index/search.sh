#!/bin/bash
# Skill Index 搜索脚本
# 扫描所有 skill 目录（~/.claude/skills、~/.agents/skills、.opencode/skills 等），
# 按意图关键词匹配 front matter 中的 name 和 description，返回最适合的 skill。
#
# 设计原则：以「运行环境」为准——本地装了哪些 skill 就扫哪些，增删都自动生效，
# 不假设某个 skill 必须存在；找不到匹配时给出提示而非报错。
#
# 用法:
#   echo "查询词" | bash search.sh
#   echo "React 组件 测试" | bash search.sh   # 多关键词，任一命中即候选
#
# 排序：名称命中优先，命中词越多越靠前（名称记 2 分/描述记 1 分），便于选「最适合」的。

set -euo pipefail

# 收集所有 skill 目录路径（环境里实际存在的）
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
# 多关键词：空格分隔，全部命中才算匹配（AND）
IFS=' ' read -r -a QUERY_TERMS <<<"$query_lower"
[ ${#QUERY_TERMS[@]} -eq 0 ] && QUERY_TERMS=("")

echo "=== Skill Index 搜索结果 ==="
echo "查询: $query"
echo ""

# 收集所有候选（名称命中优先，其次描述命中）
name_hits=""
desc_hits=""
seen=""

for dir in "${SKILL_DIRS[@]}"; do
    for skill_md in "$dir"/*/SKILL.md; do
        [ -f "$skill_md" ] || continue
        skill_name=$(basename "$(dirname "$skill_md")")

        # 去重（同名 skill 只保留第一个出现的目录）
        grep -q " $skill_name " <<<" $seen " && continue
        seen="$seen $skill_name"

        # 提取 description
        fm=$(sed -n '/^---$/,/^---$/p' "$skill_md" 2>/dev/null)
        desc=$(grep "^description:" <<<"$fm" 2>/dev/null | head -1 | sed 's/^description: *//' || true)
        [ -z "$desc" ] && desc="（无描述）"

        lower_name=$(echo "$skill_name" | tr '[:upper:]' '[:lower:]')
        lower_desc=$(echo "$desc" | tr '[:upper:]' '[:lower:]')

        # 意图匹配：任一关键词命中即视为候选（OR），命中词越多相关性越高。
        # 名称命中权重更高（记 2 分），描述命中记 1 分，按总分排序。
        hit_count=0
        name_hit_all=true
        for term in "${QUERY_TERMS[@]}"; do
            term_hit=false
            if grep -q "$term" <<<"$lower_name"; then
                hit_count=$((hit_count + 2))
                term_hit=true
            elif grep -q "$term" <<<"$lower_desc"; then
                hit_count=$((hit_count + 1))
                term_hit=true
            fi
            if ! grep -q "$term" <<<"$lower_name"; then
                name_hit_all=false
            fi
            [ "$term_hit" = false ] && continue
        done
        [ "$hit_count" -eq 0 ] && continue

        path_label=${dir//$HOME/\~}
        line="  - $skill_name ($path_label): $desc"
        if $name_hit_all && [ "$hit_count" -gt 0 ]; then
            name_hits="$name_hits
$line"
        else
            desc_hits="$desc_hits
$line"
        fi
    done
done

# 输出：名称命中在前（更相关），描述命中在后
matches=0
if [ -n "$name_hits" ]; then
    echo "【名称命中】（最相关）"
    echo "$name_hits" | grep -v '^$' | head -20
    matches=$((matches + $(echo "$name_hits" | grep -c '^  - ' || true)))
fi
if [ -n "$desc_hits" ]; then
    echo ""
    echo "【描述命中】"
    echo "$desc_hits" | grep -v '^$' | head -20
    matches=$((matches + $(echo "$desc_hits" | grep -c '^  - ' || true)))
fi

echo ""
if [ "$matches" -eq 0 ]; then
    echo "未找到匹配的 skill，尝试用更通用的关键词搜索"
else
    echo "找到 $matches 个匹配 skill，请选择最相关的调用"
fi
