#!/bin/bash
# OPC 每日自检脚本

set -euo pipefail

# 知识库路径：优先使用环境变量，默认用本地路径（MCP 不可用时兜底）
KNOWLEDGE="${OPC_KNOWLEDGE_PATH:-$HOME/code/opc/opc-knowledge}"

echo "=== OPC 每日自检 ==="
echo ""

# 知识库 Inbox
echo "📥 Inbox 待处理："
INBOX="$KNOWLEDGE/00-Inbox"
if [ -d "$INBOX" ]; then
    count=$(find "$INBOX" -maxdepth 1 -not -name '.' 2>/dev/null | wc -l | tr -d ' ')
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
# 按 C3 设计（docs/design-c2-c3.md）：以 md 文件头的 last_reviewed 字段判断，不用 mtime。
# last_reviewed 缺失时以文件 mtime 兜底（保持口径一致：超过 180 天未复审）。
echo "⚠️ 过期知识（>180天未复审）："
if [ -d "$KNOWLEDGE" ]; then
    expired=$(
        python3 - "$KNOWLEDGE" <<'PYEOF'
import sys
import os
import datetime

kb = sys.argv[1]
cutoff = datetime.date.today() - datetime.timedelta(days=180)
hits = []
for root, dirs, files in os.walk(kb):
    for name in files:
        if not name.endswith(".md"):
            continue
        path = os.path.join(root, name)
        # 读文件头 last_reviewed 字段（前 20 行内，front matter 区域）
        last_reviewed = None
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f):
                    if i >= 20:
                        break
                    if line.startswith("last_reviewed:"):
                        val = line.split(":", 1)[1].strip()
                        try:
                            last_reviewed = datetime.date.fromisoformat(val)
                        except ValueError:
                            last_reviewed = None
                        break
        except OSError:
            continue
        mtime = datetime.date.fromtimestamp(os.path.getmtime(path))
        ref = last_reviewed if last_reviewed else mtime
        if ref < cutoff:
            hits.append(path)
for h in hits[:10]:
    print(h)
PYEOF
    )
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
