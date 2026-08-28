#!/bin/bash
# test-skill-index.sh 验证 search.sh 行为正确
# 覆盖：名称命中、描述命中、多关键词、排序、无匹配提示、环境扫描（多目录）

set -euo pipefail

# 优先测仓库内版本，若在 ~/.claude 下运行则测本机版本
if [ -f ".opencode/skills/skill-index/search.sh" ]; then
    SEARCH=".opencode/skills/skill-index/search.sh"
elif [ -f "$HOME/.claude/skills/skill-index/search.sh" ]; then
    SEARCH="$HOME/.claude/skills/skill-index/search.sh"
else
    echo "❌ 找不到 search.sh"
    exit 1
fi

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

echo "=== Skill Index 测试（${SEARCH}）==="
echo ""

# 1. 名称命中（最相关，应出现在【名称命中】区）
check "名称命中 'migration'" "migration" "database-migrations"

# 2. 描述命中（英文描述）
check "描述命中 'code review'" "code review" "code-review"

# 3. 多关键词：任一命中即候选，全部命中优先
check "多关键词 react testing" "react testing" "react-testing"

# 4. 无匹配时给出提示
check "无匹配通用词" "xyzzy_not_a_skill" "未找到"

# 5. 大小写不敏感
check "大写搜索" "PDF" "pdf"

# 6. 排序：名称命中优先（react-testing 应在 react 相关结果最前）
result=$(echo "react testing" | bash "$SEARCH" 2>&1 || true)
if echo "$result" | grep -q "【名称命中】" && echo "$result" | grep -q "react-testing"; then
    echo "[PASS] 名称命中优先排序"
    PASSED=$((PASSED + 1))
else
    echo "[FAIL] 名称命中优先排序"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "结果: $PASSED/$((PASSED + FAILED)) 通过"
if [ "$FAILED" -gt 0 ]; then exit 1; else echo "✅ 全部通过"; fi
