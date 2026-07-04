#!/bin/bash
# PreToolUse hook 自检测试用例
# 用法: bash .claude/hooks/test-cases.sh

set -u

HOOK=".claude/hooks/protect-prompts.py"
PASSED=0
FAILED=0

check() {
    local desc="$1" tool="$2" path="$3" expected="$4"
    local input="{\"tool_name\":\"$tool\",\"tool_input\":{\"file_path\":\"$path\"}}"
    local actual
    # set -e 下用 || true 防 python3 非零退出杀掉捕获
    actual=$(echo "$input" | { python3 "$HOOK" 2>/dev/null; echo $?; } || true)
    # 取最后一行作为 exit code
    actual=$(echo "$actual" | tail -1)
    if [ "$actual" -eq "$expected" ]; then
        echo "[PASS] $desc"
        PASSED=$((PASSED + 1))
    else
        echo "[FAIL] $desc -> exit $actual (expected $expected)"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== PreToolUse Hook 自检 ==="
echo ""

check "绝对路径 prompts/"       "Write" "/Users/souljian/code/opc/opc-agents/prompts/qa.md" 1
check "绝对路径 .opencode/agents/" "Edit" "/Users/souljian/code/opc/opc-agents/.opencode/agents/director.md" 1
check "./prompts/ 前缀"         "Write" "./prompts/qa.md" 1
check "CLAUDE.md"               "Write" "CLAUDE.md" 1
check "routing.yaml"            "Edit"  "routing.yaml" 1
check "feedback.schema.json"    "Write" "feedback.schema.json" 1
check "opencode.json"            "Edit"  "opencode.json" 1
check "相对 prompts/"           "Write" "prompts/qa.md" 1
check "相对 .opencode/agents/"  "Edit"  ".opencode/agents/dev.md" 1
check "skills/ 放行"            "Write" ".opencode/skills/api/SKILL.md" 0
check "普通源码"                "Write" "src/main.py" 0
check "Read 放行"               "Read"  "prompts/qa.md" 0

echo ""
echo "结果: $PASSED/$((PASSED + FAILED)) 通过"
if [ "$FAILED" -gt 0 ]; then
    echo "❌ $FAILED 个失败"
    exit 1
else
    echo "✅ 全部通过"
fi
