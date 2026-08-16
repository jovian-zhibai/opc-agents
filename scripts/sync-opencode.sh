#!/bin/bash
# sync-opencode.sh — 双环境红线段单向同步
#
# 目的：把 prompts/ 版每个角色的「## 红线」章节同步到 .opencode/agents/ 版。
# 4.8 检查负责"检测"红线漂移，本脚本负责"修复"——两者配套。
#
# 安全设计（保正增长）：
#   - 只同步「## 红线」章节，其余内容（front matter、特有段落）一律不动
#   - 同步前自动备份 opencode 版到 /tmp/opc-sync-backup-{role}.md
#   - 输出每角色"同步前 diff 行数 → 同步后 diff 行数"，便于验证
#   - --dry-run 只预览不动文件
#
# 用法: bash scripts/sync-opencode.sh [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR/../prompts"
AGENTS_DIR="$SCRIPT_DIR/../.opencode/agents"

DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

# 从文件中提取「## 红线」章节（遇下一个 ## 标题即停），去空行
# 注：进入红线段后遇到任何其他 ## 标题（如 ## 性格/## 能力边界）立即结束
extract_redline() {
  awk '
    /^## 红线/ { in_sec=1; print; next }
    in_sec == 1 { if (/^## /) exit; print }
  ' "$1" | grep -vE '^$'
}

# 用新红线内容替换目标文件的红线章节（遇下一个 ## 标题即结束红线段）
# 红线内容经临时文件传入（macOS awk 的 -v 不支持多行字符串）
replace_redline() {
  local file="$1" new_section="$2"
  local tmp=$(mktemp)
  printf '%s\n' "$new_section" >"$tmp"
  awk -v redfile="$tmp" '
    BEGIN { printed_new=0; in_sec=0; while ((getline l < redfile) > 0) new_content = new_content l "\n" }
    /^## 红线/ {
      if (!printed_new) { printf "%s", new_content; printed_new=1 }
      in_sec=1; next
    }
    in_sec == 1 && /^## / { in_sec=0; print; next }
    in_sec == 0 { print }
  ' "$file"
  rm -f "$tmp"
}

echo "=== 双环境红线段同步 ==="
total_improved=0

for prompts_f in "$PROMPTS_DIR"/*.md; do
  role=$(basename "$prompts_f" .md)
  opencode_f="$AGENTS_DIR/$role.md"
  [ ! -f "$opencode_f" ] && continue

  prompts_redline=$(extract_redline "$prompts_f")
  opencode_redline=$(extract_redline "$opencode_f")

  # 相同则跳过
  if [ "$prompts_redline" = "$opencode_redline" ]; then
    echo "  ✅ $role: 红线段已一致"
    continue
  fi

  before_diff=$(diff <(echo "$opencode_redline") <(echo "$prompts_redline") | grep -cE '^[<>]' || true)

  if [ "$DRY_RUN" = true ]; then
    echo "  ⚠️  $role: 红线段有 ${before_diff} 行差异（dry-run，未改动）"
    continue
  fi

  # 备份 + 替换
  cp "$opencode_f" "/tmp/opc-sync-backup-${role}.md"
  new_content=$(replace_redline "$opencode_f" "$prompts_redline")
  printf '%s\n' "$new_content" >"$opencode_f"

  after_diff=$(diff <(extract_redline "$opencode_f") <(extract_redline "$prompts_f") | grep -cE '^[<>]' || true)
  echo "  🔄 $role: 红线段 ${before_diff} 行差异 → ${after_diff} 行（备份: /tmp/opc-sync-backup-${role}.md）"
  total_improved=$((total_improved + 1))
done

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "=== dry-run 完成（未改动任何文件）==="
else
  echo "=== 同步完成：${total_improved} 个角色更新 ==="
  echo "建议随后跑 bash scripts/quality-gate.sh 确认 0 errors"
fi
