#!/bin/bash
# OPC Agent 一致性检查（双运行时版）
# 检查 prompts/（共享）+ .opencode/agents/（OpenCode 配置）的引用一致性和完整性

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMPTS_DIR="$PROJECT_DIR/prompts"
AGENTS_DIR="$PROJECT_DIR/.opencode/agents"
SKILLS_DIR="$PROJECT_DIR/.opencode/skills"
KNOWLEDGE="${OPC_KNOWLEDGE_PATH:-$HOME/code/opc/opc-knowledge}"

ERRORS=0
WARNINGS=0

echo "=== OPC Agent 一致性检查（双运行时版） ==="
echo ""

# ---------- 1. prompts/ 文件完整性 ----------
echo "📋 prompts/ 完整性检查："
EXPECTED_PROMPTS=("advisor" "agent-manager" "dev" "director" "finance" "growth" "guardian" "product" "qa" "ui-ux")
for name in "${EXPECTED_PROMPTS[@]}"; do
  if [ ! -f "$PROMPTS_DIR/$name.md" ]; then
    echo "  ❌ prompts/$name.md 不存在"
    ERRORS=$((ERRORS + 1))
  fi
done
if [ $ERRORS -eq 0 ]; then
  echo "  ✅ 所有 10 个 prompt 文件存在"
fi

echo ""

# ---------- 2. prompts/ 关键章节检查 ----------
echo "📋 prompts/ 关键章节检查："
for prompt_file in "$PROMPTS_DIR"/*.md; do
  agent_name=$(basename "$prompt_file" .md)
  if ! grep -qE "## (核心职责|核心能力|你的定位|核心原则)" "$prompt_file" 2>/dev/null && \
     ! grep -qE "## (红线|协作接口|产出规则|工作流程)" "$prompt_file" 2>/dev/null; then
    echo "  ❌ $agent_name — 缺少核心职责/红线/协作接口等关键章节"
    ERRORS=$((ERRORS + 1))
  fi
done
if [ $ERRORS -eq 0 ]; then
  echo "  ✅ 所有 prompt 关键章节完整"
fi

echo ""

# ---------- 3. .opencode/agents/ Front matter 完整性 ----------
echo "📋 OpenCode front matter 检查："
if [ -d "$AGENTS_DIR" ]; then
  REQUIRED_FIELDS=("description" "mode" "temperature" "steps")
  fm_errors=0
  for agent_file in "$AGENTS_DIR"/*.md; do
    agent_name=$(basename "$agent_file" .md)
    for field in "${REQUIRED_FIELDS[@]}"; do
      if ! grep -q "^$field:" <(sed -n '/^---$/,/^---$/p' "$agent_file" 2>/dev/null); then
        echo "  ❌ $agent_name — 缺少 front matter 字段: $field"
        fm_errors=$((fm_errors + 1))
      fi
    done
  done
  if [ "$fm_errors" -eq 0 ]; then
    echo "  ✅ 所有 OpenCode Agent front matter 完整"
  else
    ERRORS=$((ERRORS + fm_errors))
  fi
else
  echo "  ⚠️  .opencode/agents/ 目录不存在（非 OpenCode 环境可忽略）"
fi

echo ""

# ---------- 4. prompts/ 文件 vs CLAUDE.md 引用 ----------
echo "🔗 Agent 引用一致性检查（CLAUDE.md）："
ACTUAL_PROMPTS=()
for f in "$PROMPTS_DIR"/*.md; do
  ACTUAL_PROMPTS+=("$(basename "$f" .md)")
done

echo "  实际 prompt 数: ${#ACTUAL_PROMPTS[@]}"
echo "  实际 prompt 列表: ${ACTUAL_PROMPTS[*]}"

for a in "${ACTUAL_PROMPTS[@]}"; do
  if ! grep -qi "| $a " "$PROJECT_DIR/CLAUDE.md" 2>/dev/null && \
     ! grep -qi "$a" "$PROJECT_DIR/CLAUDE.md" 2>/dev/null; then
    echo "  ⚠️  $a 是实际存在的 prompt，但 CLAUDE.md 未引用"
    WARNINGS=$((WARNINGS + 1))
  fi
done

# 也检查 .opencode/agents/director.md
if [ -f "$AGENTS_DIR/director.md" ]; then
  echo ""
  echo "🔗 Agent 引用一致性检查（director.md）："
  for a in "${ACTUAL_PROMPTS[@]}"; do
    # 跳过 director 自身
    [ "$a" = "director" ] && continue
    if ! grep -qi "$a" "$AGENTS_DIR/director.md" 2>/dev/null; then
      echo "  ⚠️  $a 存在于 prompts/ 但 director.md 未引用"
      WARNINGS=$((WARNINGS + 1))
    fi
  done
fi

echo ""

# ---------- 5. Skill 引用检查 ----------
echo "🎯 Skill 引用完整性检查："
if [ -d "$AGENTS_DIR" ]; then
  for agent_file in "$AGENTS_DIR"/*.md; do
    agent_name=$(basename "$agent_file" .md)
    in_skills=false
    while IFS= read -r line; do
      if [[ "$line" =~ ^skills: ]]; then
        in_skills=true
        continue
      fi
      if $in_skills; then
        if [[ "$line" =~ ^[a-z] ]] || [[ "$line" =~ ^--- ]]; then
          in_skills=false
          continue
        fi
        skill_name=$(echo "$line" | sed -n 's/^[[:space:]]*-[[:space:]]*//p' | sed 's/[[:space:]]*#.*//')
        if [ -n "$skill_name" ]; then
          if [ ! -d "$SKILLS_DIR/$skill_name" ]; then
            echo "  ⚠️  $agent_name 引用了不存在的 skill: $skill_name"
            WARNINGS=$((WARNINGS + 1))
          fi
        fi
      fi
    done < "$agent_file"
  done
fi
if [ $WARNINGS -eq 0 ]; then
  echo "  ✅ 所有 skill 引用完整"
fi

echo ""

# ---------- 6. 知识库路径检查 ----------
echo "📚 知识库路径检查："
CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
  MISSING_DIRS=0
  while IFS= read -r dir; do
    if [[ "$dir" =~ ^[0-9]{2}- ]]; then
      if [ ! -d "$KNOWLEDGE/$dir" ]; then
        echo "  ❌ CLAUDE.md 引用知识库目录 $dir，但实际路径 $KNOWLEDGE/$dir 不存在"
        MISSING_DIRS=$((MISSING_DIRS + 1))
      fi
    fi
  done < <(grep -oP '^\| \K[0-9]{2}-[^ ]+' "$CLAUDE_MD" 2>/dev/null | head -20)
  if [ "$MISSING_DIRS" -eq 0 ]; then
    echo "  ✅ 所有 CLAUDE.md 引用的知识库目录都存在"
  else
    ERRORS=$((ERRORS + MISSING_DIRS))
  fi
fi

echo ""

# ---------- 7. 红线密钥检查 ----------
echo "🔑 密钥泄露红线检查（prompts/）："
for prompt_file in "$PROMPTS_DIR"/*.md; do
  agent_name=$(basename "$prompt_file" .md)
  if ! grep -q "不泄露任何密钥\|不泄露.*API key" "$prompt_file" 2>/dev/null; then
    echo "  ❌ $agent_name — 缺少密钥泄露红线"
    ERRORS=$((ERRORS + 1))
  fi
done

# 也检查 CLAUDE.md
if ! grep -q "不泄露任何密钥\|不泄露.*API key" "$CLAUDE_MD" 2>/dev/null; then
  echo "  ❌ CLAUDE.md — 缺少密钥泄露红线"
  ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
  echo "  ✅ 所有 prompt 和 CLAUDE.md 都有密钥泄露红线"
fi

echo ""
echo "===================="
echo "结果：$ERRORS 个错误，$WARNINGS 个警告"
if [ $ERRORS -eq 0 ]; then
  echo "✅ Agent 一致性检查通过"
  exit 0
else
  echo "❌ Agent 一致性检查失败 ($ERRORS 项不通过)"
  exit 1
fi
