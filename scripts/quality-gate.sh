#!/bin/bash
# OPC 质量门禁检查

echo "=== OPC 质量门禁 ==="
echo ""

ERRORS=0

# 1. Lint 检查
echo "🔍 Lint 检查："
if [ -f "package.json" ]; then
    if npm run lint --silent 2>/dev/null; then
        echo "  ✅ 通过"
    else
        echo "  ❌ 失败"
        ERRORS=$((ERRORS + 1))
    fi
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
    if python3 -m ruff check . 2>/dev/null; then
        echo "  ✅ 通过"
    else
        echo "  ❌ 失败"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  ⚠️ 未检测到项目类型"
fi

echo ""

# 2. 测试
echo "🧪 测试检查："
if [ -f "package.json" ]; then
    if npm test --silent 2>/dev/null; then
        echo "  ✅ 通过"
    else
        echo "  ❌ 失败"
        ERRORS=$((ERRORS + 1))
    fi
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
    if python3 -m pytest --quiet 2>/dev/null; then
        echo "  ✅ 通过"
    else
        echo "  ❌ 失败"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  ⚠️ 未检测到项目类型"
fi

echo ""

# 3. 类型检查
echo "📐 类型检查："
if [ -f "tsconfig.json" ]; then
    if npx tsc --noEmit 2>/dev/null; then
        echo "  ✅ 通过"
    else
        echo "  ❌ 失败"
        ERRORS=$((ERRORS + 1))
    fi
elif [ -f "pyproject.toml" ] || [ -f "mypy.ini" ]; then
    if python3 -m mypy . --ignore-missing-imports 2>/dev/null; then
        echo "  ✅ 通过"
    else
        echo "  ❌ 失败"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "  ⚠️ 未检测到类型检查配置"
fi

echo ""

# 4. 覆盖率检查（≥ 80%）
echo "📊 覆盖率检查（≥ 80%）："
COVERAGE_THRESHOLD=80
if [ -f "package.json" ]; then
    COVERAGE=$(npm test -- --coverage --coverageReporters=text-summary 2>/dev/null | grep "Lines" | grep -oE '[0-9]+' | head -1)
    if [ -n "$COVERAGE" ] && [ "$COVERAGE" -ge "$COVERAGE_THRESHOLD" ]; then
        echo "  ✅ 通过 (${COVERAGE}%)"
    elif [ -n "$COVERAGE" ]; then
        echo "  ❌ 失败 (${COVERAGE}% < ${COVERAGE_THRESHOLD}%)"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ⚠️ 无法获取覆盖率数据"
    fi
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
    COVERAGE=$(python3 -m pytest --cov=. --cov-report=term-missing 2>/dev/null | grep "TOTAL" | grep -oE '[0-9]+' | head -1)
    if [ -n "$COVERAGE" ] && [ "$COVERAGE" -ge "$COVERAGE_THRESHOLD" ]; then
        echo "  ✅ 通过 (${COVERAGE}%)"
    elif [ -n "$COVERAGE" ]; then
        echo "  ❌ 失败 (${COVERAGE}% < ${COVERAGE_THRESHOLD}%)"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ⚠️ 无法获取覆盖率数据（需要 pytest-cov）"
    fi
else
    echo "  ⚠️ 未检测到项目类型"
fi

echo ""

# 结果
echo "===================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ 质量门禁通过"
    exit 0
else
    echo "❌ 质量门禁失败 ($ERRORS 项不通过)"
    exit 1
fi
