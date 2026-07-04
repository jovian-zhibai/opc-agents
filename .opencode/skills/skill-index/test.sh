#!/bin/bash
# test-skill-index.sh 验证 search.sh 行为正确

set -euo pipefail
SEARCH="$HOME/.claude/skills/skill-index/search.sh"
PASSED=0; FAILED=0

check() {
    local desc="$1" query="$2" expect="$3"
    local result
    result=$(echo "$query" | bash "$SEARCH" 2>&1 || true)
    if echo "$result" | grep -qi "$expect"; then
        echo "[PASS] $desc"
        PASSED=$((PASSED + 1))
    else
        echo "[FAIL] $desc — 期望匹配 '$expect'"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== Skill Index 测试 ==="
echo ""

# 1. 精确匹配（用实际存在的 skill）
check "搜索 'pdf'"         "pdf"         "pdf"
check "搜索 'code review'" "code review" "code-review"
check "搜索 'test'"        "test"        "test-driven-development"
check "搜索 'writing'"     "writing"     "writing-skills"

# 2. 无匹配时给出提示
check "无匹配通用词" "xyzzy_not_a_skill" "未找到"

# 3. 搜索描述中的词（非 skill 名）
check "搜索描述中的 'design'" "design" "frontend-design"
check "搜索描述中的 'skill'"  "skill"  "skill-creator"

# 4. 大小写不敏感
check "大写搜索" "PDF" "pdf"

echo ""
echo "结果: $PASSED/$((PASSED + FAILED)) 通过"
if [ "$FAILED" -gt 0 ]; then exit 1; else echo "✅ 全部通过"; fi
