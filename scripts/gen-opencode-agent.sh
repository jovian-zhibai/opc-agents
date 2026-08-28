#!/bin/bash
# gen-opencode-agent.sh — 单源生成：从 prompts/<role>.md 生成 .opencode/agents/<role>.md
#
# 设计：prompts/ 为唯一真相源，opencode 版由脚本自动生成（front matter + 转换规则）。
# 转换规则：
#   1. 提取现有 opencode 版的 front matter（试点阶段作为配置源，未来独立配置化）
#   2. 去掉"能力边界"章节（opencode 用 front matter skills 替代）
#   3. 路径前缀替换（各角色不同，见 PATH_REPLACE 配置）
#   4. 加 mirror 声明行
#
# 用法:
#   bash scripts/gen-opencode-agent.sh <role> [--write]   # 单角色，默认 dry-run 到 /tmp
#   bash scripts/gen-opencode-agent.sh --all               # 批量 dry-run 所有角色，输出差异统计
#   --write 直接覆盖 .opencode/agents/<role>.md（危险，需确认）

set -euo pipefail

# ---------- 路径前缀替换规则配置 ----------
# 各角色 opencode 版实际使用的路径前缀不同：
#   默认：$OPC_WORK_PATH/ → .opencode/work/
#   agent-manager：$OPC_WORK_PATH/ → work/
#   director：混合使用（部分保留 $OPC_WORK_PATH/），暂不替换，需单独统一
get_path_replace() {
  case "$1" in
    agent-manager) echo 's|\$OPC_WORK_PATH/|work/|g' ;;
    director)      echo '' ;;  # 暂不替换，director 版路径前缀需先统一
    *)             echo 's|\$OPC_WORK_PATH/|.opencode/work/|g' ;;
  esac
}

# ---------- 生成单个角色 ----------
generate_role() {
  local role="$1"
  local write="${2:-false}"
  local prompts_file="prompts/$role.md"
  local opencode_file=".opencode/agents/$role.md"

  if [ ! -f "$prompts_file" ]; then
    echo "❌ prompts/$role.md 不存在"
    return 1
  fi
  if [ ! -f "$opencode_file" ]; then
    echo "❌ .opencode/agents/$role.md 不存在"
    return 1
  fi

  local path_replace
  path_replace=$(get_path_replace "$role")

  # 1. 提取现有 opencode 版的 front matter
  local front_matter
  front_matter=$(awk '/^---$/{c++; print; if(c==2) exit; next} c>=1{print}' "$opencode_file")

  # 2. 取 prompts 正文，应用转换规则：
  #    a. 去掉开头的迷你 front matter（部分 prompts 文件有 optimization_log 块）
  #    b. 去掉"能力边界"章节（opencode 用 front matter skills 替代）
  #    c. 路径前缀替换
  #    d. 去掉末尾空行
  local body
  if head -1 "$prompts_file" | grep -q '^---$'; then
    # 有开头 front matter：跳过第一个 --- 到第二个 --- 之间的内容
    body=$(awk '/^---$/{c++; if(c==2){next}} c>=2{print}' "$prompts_file")
  else
    body=$(cat "$prompts_file")
  fi
  # 去掉"能力边界"章节
  body=$(echo "$body" | awk '/^## 能力边界/{skip=1; next} /^## /{skip=0} !skip')
  if [ -n "$path_replace" ]; then
    body=$(echo "$body" | sed -E "$path_replace")
  fi
  # 去掉末尾空行
  body=$(echo "$body" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')

  # 3. 组装
  local output
  output=$(cat <<EOF
$front_matter

> 📖 此文件 mirror \`prompts/$role.md\`。完整内容以 prompts/ 为准。

$body
EOF
)

  if [ "$write" = true ]; then
    echo "$output" > "$opencode_file"
    echo "✅ 已写入 $opencode_file"
  else
    local tmp="/tmp/gen-$role.md"
    echo "$output" > "$tmp"
    # 统计差异行数（先存 diff 输出再 grep，规避 pipefail 下 diff exit 1 的问题）
    local diff_output diff_count
    diff_output=$(diff "$tmp" "$opencode_file" 2>/dev/null || true)
    diff_count=$(echo "$diff_output" | grep -cE '^[<>]' || echo 0)
    echo "$role: $diff_count 行差异"
  fi
}

# ---------- 主逻辑 ----------
if [ "${1:-}" = "--all" ]; then
  echo "=== 批量 dry-run：所有角色单源生成差异统计 ==="
  echo ""
  for f in prompts/*.md; do
    role=$(basename "$f" .md)
    generate_role "$role" false
  done
  echo ""
  echo "=== 说明 ==="
  echo "  0 行 = 生成结果与现有版本完全一致"
  echo "  少量行 = 格式差异（空行等），属单源统一的预期效果"
  echo "  大量行 = 有实质内容差异，需排查转换规则是否完备"
  exit 0
fi

ROLE="${1:-}"
WRITE=false
[ "${2:-}" = "--write" ] && WRITE=true

if [ -z "$ROLE" ]; then
  echo "用法: bash scripts/gen-opencode-agent.sh <role> [--write]"
  echo "      bash scripts/gen-opencode-agent.sh --all"
  exit 1
fi

generate_role "$ROLE" "$WRITE"
