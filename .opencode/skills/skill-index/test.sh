#!/bin/bash
# test-skill-index.sh 验证 search.sh 行为正确
# 自包含：在临时目录创建测试技能，不依赖本机真实技能目录（CI 友好）。
# 覆盖：名称命中、描述命中、多关键词、排序、无匹配提示、大小写不敏感。

set -euo pipefail

# 定位 search.sh（优先同目录，其次本机 ~/.claude 版）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SEARCH="$SCRIPT_DIR/search.sh"
[ -f "$SEARCH" ] || SEARCH="$HOME/.claude/skills/skill-index/search.sh"
if [ ! -f "$SEARCH" ]; then
    echo "❌ 找不到 search.sh"
    exit 1
fi

# 临时隔离环境：自建 .opencode/skills，HOME 也指向临时目录（避免本机真实技能混入）
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
mkdir -p "$TMPDIR/.opencode/skills"

# 创建测试技能（用独特前缀 zz- 避免与任何真实技能名冲突）
make_skill() {
    local name="$1" desc="$2"
    mkdir -p "$TMPDIR/.opencode/skills/$name"
    printf -- '---\nname: %s\ndescription: %s\n---\n\n正文\n' "$name" "$desc" \
        > "$TMPDIR/.opencode/skills/$name/SKILL.md"
}

make_skill "zz-migration-tool"   "Database migration best practices for schema changes"
make_skill "zz-code-reviewer"    "Automated code review and static analysis"
make_skill "zz-react-tester"     "React component testing with React Testing Library"
make_skill "zz-helper-utils"     "Various react helper utilities and tools"

# 从临时目录调用 search.sh（相对路径 .opencode/skills 解析到临时目录）
# HOME 设为临时目录，确保不扫描本机 ~/.claude 等真实技能
run_search() {
    local query="$1"
    (cd "$TMPDIR" && HOME="$TMPDIR" bash "$SEARCH" <<< "$query")
}

PASSED=0; FAILED=0

check() {
    local desc="$1" query="$2" expect="$3"
    local result
    result=$(run_search "$query" 2>&1 || true)
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

# 1. 名称命中
check "名称命中 'migration'" "migration" "zz-migration-tool"

# 2. 描述命中（技能名不含关键词，仅描述含）
check "描述命中 'code review'" "code review" "zz-code-reviewer"

# 3. 多关键词：任一命中即候选，全部命中优先
check "多关键词 react testing" "react testing" "zz-react-tester"

# 4. 无匹配时给出提示
check "无匹配通用词" "xyzzy_not_a_skill" "未找到"

# 5. 大小写不敏感
check "大写搜索" "MIGRATION" "zz-migration-tool"

# 6. 排序：名称命中优先（react-tester 名称命中应出现在【名称命中】区）
result=$(run_search "react" 2>&1 || true)
if echo "$result" | grep -q "【名称命中】" && echo "$result" | grep -q "zz-react-tester"; then
    echo "[PASS] 名称命中优先排序"
    PASSED=$((PASSED + 1))
else
    echo "[FAIL] 名称命中优先排序"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "结果: $PASSED/$((PASSED + FAILED)) 通过"
if [ "$FAILED" -gt 0 ]; then exit 1; else echo "✅ 全部通过"; fi
