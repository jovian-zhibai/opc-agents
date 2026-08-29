#!/usr/bin/env bash
# backup-knowledge.sh — OPC 知识库手动备份脚本
#
# 用途：把 $OPC_KNOWLEDGE_PATH 的变更 commit 并 push 到 GitHub 私有仓库。
# 安全闸：commit 前跑 secret 扫描，命中则中止，不 commit 不 push。
#
# 使用方式：手动/按需跑，不挂全自动 cron push。
#   bash scripts/backup-knowledge.sh
#
# 设计原则：
#   - 无变更时优雅跳过（exit 0）
#   - secret 扫描命中时报警并 exit 1（不 commit 不 push）
#   - 所有变量加引号，过 ShellCheck
#   - 复用 opc-agents quality-gate.sh §7.5 的 5 种 secret 正则

set -euo pipefail

# ---------- 配置 ----------

# 知识库路径（优先环境变量，默认 ~/code/opc/opc-knowledge）
KNOWLEDGE_PATH="${OPC_KNOWLEDGE_PATH:-$HOME/code/opc/opc-knowledge}"

# ---------- Secret 扫描函数 ----------

# 扫描知识库工作区，命中任何 secret 模式则返回 1
# 复用 quality-gate.sh §7.5 的 5 种正则
scan_secrets() {
  local hit=0
  local scan_dir="$1"

  echo "🔍 运行 secret 扫描（5 种模式）..."

  # 模式 1：sk- 前缀（OpenAI 等 API key）
  if grep -rnE 'sk-[A-Za-z0-9]{20,}' \
      --include="*.md" --include="*.txt" --include="*.json" \
      --include="*.yaml" --include="*.yml" --include="*.html" \
      --include="*.canvas" --include="*.env" \
      "$scan_dir" 2>/dev/null | grep -v "/.git/"; then
    echo "❌ 命中 sk- 前缀 secret"
    hit=1
  fi

  # 模式 2：api_key 带引号长字面量
  if grep -rnE 'api_key[[:space:]]*=[[:space:]]*["'"'"'][A-Za-z0-9_-+/=]{16,}["'"'"']' \
      --include="*.md" --include="*.txt" --include="*.json" \
      --include="*.yaml" --include="*.yml" --include="*.html" \
      "$scan_dir" 2>/dev/null | grep -v "/.git/"; then
    echo "❌ 命中 api_key 带引号长字面量"
    hit=1
  fi

  # 模式 3：token= 长串
  if grep -rnE 'token[[:space:]]*=[[:space:]]*["'"'"']?[A-Za-z0-9_-]{20,}["'"'"']?' \
      --include="*.md" --include="*.txt" --include="*.json" \
      --include="*.yaml" --include="*.yml" \
      "$scan_dir" 2>/dev/null | grep -v "/.git/"; then
    echo "❌ 命中 token= 长串"
    hit=1
  fi

  # 模式 4：SENSENOVA_API_KEY=
  if grep -rnE 'SENSENOVA_API_KEY[[:space:]]*=[[:space:]]*["'"'"']?[A-Za-z0-9_-]{10,}' \
      --include="*.md" --include="*.txt" --include="*.json" \
      --include="*.yaml" --include="*.yml" --include="*.env" \
      "$scan_dir" 2>/dev/null | grep -v "/.git/"; then
    echo "❌ 命中 SENSENOVA_API_KEY="
    hit=1
  fi

  # 模式 5：JWT（eyJ 三段式）
  if grep -rnE 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}' \
      --include="*.md" --include="*.txt" --include="*.json" \
      "$scan_dir" 2>/dev/null | grep -v "/.git/"; then
    echo "❌ 命中 JWT"
    hit=1
  fi

  if [ "$hit" -eq 1 ]; then
    return 1
  fi
  echo "✅ secret 扫描通过，5 种模式无命中"
  return 0
}

# ---------- 主逻辑 ----------

main() {
  echo "📦 OPC 知识库备份"
  echo "   知识库路径: $KNOWLEDGE_PATH"
  echo ""

  # 检查知识库目录存在
  if [ ! -d "$KNOWLEDGE_PATH" ]; then
    echo "❌ 知识库目录不存在: $KNOWLEDGE_PATH"
    echo "   请设置 OPC_KNOWLEDGE_PATH 环境变量或确认路径正确"
    exit 1
  fi

  cd "$KNOWLEDGE_PATH"

  # 检查是否是 git 仓库
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "❌ 知识库目录不是 git 仓库: $KNOWLEDGE_PATH"
    exit 1
  fi

  # 检查有无变更
  if [ -z "$(git status --porcelain)" ]; then
    echo "✅ 知识库无变更，跳过备份"
    exit 0
  fi

  echo "📝 检测到变更:"
  git status --short
  echo ""

  # Secret 扫描闸
  if ! scan_secrets "$KNOWLEDGE_PATH"; then
    echo ""
    echo "🚨 Secret 扫描命中，中止备份！未 commit 未 push。"
    echo "   请检查上述文件，移除 secret 后再运行本脚本。"
    echo "   注意：正则有盲区（带 . 的 JWT、带 :@# 的 key、图片内部），人工复核仍必要。"
    exit 1
  fi

  echo ""

  # Commit
  local commit_msg
  commit_msg="backup $(date +%F_%T)"
  echo "📝 Commit: $commit_msg"
  git add -A
  git commit -m "$commit_msg"

  echo ""

  # Push
  echo "🚀 Push 到 origin/main..."
  if ! git push origin main; then
    echo "❌ Push 失败"
    exit 1
  fi

  echo ""
  echo "✅ 备份完成"
  echo "   最新 commit: $(git rev-parse --short HEAD)"
  echo "   远程: $(git remote get-url origin)"
}

main "$@"
