#!/bin/bash
# sync-opencode.sh — 双环境核心章节单向同步
#
# 目的：把 prompts/ 版每个角色的核心章节同步到 .opencode/agents/ 版。
# 4.8 检查负责"检测"漂移，本脚本负责"修复"——两者配套。
#
# 安全设计（保正增长）：
#   - 只同步 CORE_SECTIONS 声明的章节，其余内容（front matter、特有段落）一律不动
#   - 当前唯一安全可同步的章节是「## 红线」：
#     「能力边界/职责边界」在 opencode 版由 front matter skills 替代，属有意差异，勿同步
#   - 同步前自动备份 opencode 版到 /tmp/opc-sync-backup-{role}-{section}.md
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

# 核心章节清单：未来要同步更多章节时在此追加（注意避免同步有意差异的章节）
CORE_SECTIONS=("## 红线")

# 从文件中提取指定章节（遇下一个 ## 标题即停），去空行
extract_section() {
  local section="$1"
  awk -v sec="$section" '
    index($0, sec) == 1 { in_sec=1; print; next }
    in_sec == 1 { if (/^## /) exit; print }
  ' "$2" | grep -vE '^$'
}

# 用新章节内容替换目标文件的指定章节（遇下一个 ## 标题即结束该章节）
# 内容经临时文件传入（macOS awk 的 -v 不支持多行字符串）
replace_section() {
  local file="$1" section="$2" new_content_str="$3"
  local tmp=$(mktemp)
  printf '%s\n' "$new_content_str" >"$tmp"
  awk -v redfile="$tmp" -v sec="$section" '
    BEGIN { printed_new=0; in_sec=0; while ((getline l < redfile) > 0) new_content = new_content l "\n" }
    index($0, sec) == 1 {
      if (!printed_new) { printf "%s", new_content; printed_new=1 }
      in_sec=1; next
    }
    in_sec == 1 && /^## / { in_sec=0; print; next }
    in_sec == 0 { print }
  ' "$file"
  rm -f "$tmp"
}

echo "=== 双环境核心章节同步（章节: ${CORE_SECTIONS[*]}）==="
total_improved=0

for prompts_f in "$PROMPTS_DIR"/*.md; do
  role=$(basename "$prompts_f" .md)
  opencode_f="$AGENTS_DIR/$role.md"
  [ ! -f "$opencode_f" ] && continue

  for section in "${CORE_SECTIONS[@]}"; do
    prompts_sec=$(extract_section "$section" "$prompts_f")
    opencode_sec=$(extract_section "$section" "$opencode_f")

    # 章节不存在（如某角色无此章节）则跳过
    [ -z "$prompts_sec" ] && continue

    # 相同则跳过
    if [ "$prompts_sec" = "$opencode_sec" ]; then
      echo "  ✅ ${role}: ${section} 已一致"
      continue
    fi

    before_diff=$(diff <(echo "$opencode_sec") <(echo "$prompts_sec") | grep -cE '^[<>]' || true)

    if [ "$DRY_RUN" = true ]; then
      echo "  ⚠️  ${role}: ${section} 有 ${before_diff} 行差异（dry-run，未改动）"
      continue
    fi

    # 备份 + 替换
    cp "$opencode_f" "/tmp/opc-sync-backup-${role}-$(echo "$section" | tr -cd 'a-zA-Z').md"
    new_content=$(replace_section "$opencode_f" "$section" "$prompts_sec")
    printf '%s\n' "$new_content" >"$opencode_f"

    after_diff=$(diff <(extract_section "$section" "$opencode_f") <(extract_section "$section" "$prompts_f") | grep -cE '^[<>]' || true)
    echo "  🔄 ${role}: ${section} ${before_diff} 行差异 → ${after_diff} 行（已备份）"
    total_improved=$((total_improved + 1))
  done
done

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "=== dry-run 完成（未改动任何文件）==="
else
  echo "=== 同步完成：${total_improved} 处更新 ==="
  echo "建议随后跑 bash scripts/quality-gate.sh 确认 0 errors"
fi
