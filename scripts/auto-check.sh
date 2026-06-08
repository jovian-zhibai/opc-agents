#!/bin/bash
# OPC 每日自检脚本

# 知识库路径：优先使用环境变量，默认用本地路径（MCP 不可用时兜底）
KNOWLEDGE="${OPC_KNOWLEDGE_PATH:-/Users/souljian/code/opc/opc-knowledge}"

echo "=== OPC 每日自检 ==="
echo ""

# 知识库 Inbox
echo "📥 Inbox 待处理："
INBOX="$KNOWLEDGE/00-Inbox"
if [ -d "$INBOX" ]; then
    count=$(ls "$INBOX" 2>/dev/null | wc -l | tr -d ' ')
    echo "  $count 条待整理"
else
    echo "  目录不存在: $INBOX"
fi

echo ""

# 活跃任务
echo "📋 活跃任务："
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/state-manager.py" status 2>/dev/null || echo "  状态文件不存在"

echo ""

# Git 状态
echo "📁 Git 状态："
git status --short 2>/dev/null || echo "  不是 git 仓库"

echo ""

# 过期知识
echo "⚠️ 过期知识（>180天）："
if [ -d "$KNOWLEDGE" ]; then
    expired=$(find "$KNOWLEDGE" -name "*.md" -mtime +180 2>/dev/null | head -10)
    if [ -n "$expired" ]; then
        echo "$expired"
    else
        echo "  无过期知识"
    fi
else
    echo "  知识库目录不存在: $KNOWLEDGE"
fi

echo ""
echo "=== 自检完成 ==="
