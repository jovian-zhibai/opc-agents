#!/bin/bash
# OPC Agent 一致性检查
# 替代旧版的 lint/test 检查（本项目无传统应用代码）
# 检查 Agent 配置文件之间的引用一致性和完整性

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS_DIR="$PROJECT_DIR/.opencode/agents"
SKILLS_DIR="$PROJECT_DIR/.opencode/skills"
KNOWLEDGE="${OPC_KNOWLEDGE_PATH:-$HOME/code/opc/opc-knowledge}"

ERRORS=0
WARNINGS=0

echo "=== OPC Agent 一致性检查 ==="
echo ""

# ---------- 1. Front matter 完整性 ----------
echo "📋 Front matter 检查："
REQUIRED_FIELDS=("description" "mode" "model" "temperature" "steps")
for agent_file in "$AGENTS_DIR"/*.md; do
  agent_name=$(basename "$agent_file" .md)
  for field in "${REQUIRED_FIELDS[@]}"; do
    if ! grep -q "^$field:" <(sed -n '/^---$/,/^---$/p' "$agent_file" 2>/dev/null); then
      echo "  ❌ $agent_name — 缺少 front matter 字段: $field"
      ERRORS=$((ERRORS + 1))
    fi
  done
done
if [ $? -eq 0 ] && [ $ERRORS -eq 0 ]; then
  echo "  ✅ 所有 Agent front matter 完整"
fi

echo ""

# ---------- 2. Agent 文件 vs Director 引用 ----------
echo "🔗 Agent 引用一致性检查："
ACTUAL_AGENTS=()
for f in "$AGENTS_DIR"/*.md; do
  ACTUAL_AGENTS+=("$(basename "$f" .md)")
done

# 排除 director 自身（它是 primary，不算 subagent）
SUBAGENTS=()
for a in "${ACTUAL_AGENTS[@]}"; do
  mode=$(sed -n '/^---$/,/^---$/p' "$AGENTS_DIR/$a.md" 2>/dev/null | grep "^mode:" | awk '{print $2}' | head -1)
  if [ "$mode" = "subagent" ]; then
    SUBAGENTS+=("$a")
  fi
done

echo "  实际 subagent 数: ${#SUBAGENTS[@]}"
echo "  实际 subagent 列表: ${SUBAGENTS[*]}"

# 检查 Director 的 Agent 团队表中是否列出了所有 subagent
for a in "${SUBAGENTS[@]}"; do
  if ! grep -qi "| $a " "$AGENTS_DIR/director.md" 2>/dev/null; then
    echo "  ⚠️  $a 是实际存在的 subagent，但 Director 的 Agent 团队表未引用"
    WARNINGS=$((WARNINGS + 1))
  fi
done

echo ""

# ---------- 3. Skill 引用检查 ----------
echo "🎯 Skill 引用完整性检查："
for agent_file in "$AGENTS_DIR"/*.md; do
  agent_name=$(basename "$agent_file" .md)
  # 从 front matter 中提取 skills 列表
  in_skills=false
  while IFS= read -r line; do
    if [[ "$line" =~ ^skills: ]]; then
      in_skills=true
      continue
    fi
    if $in_skills; then
      # 检查是否离开了 skills 块
      if [[ "$line" =~ ^[a-z] ]] || [[ "$line" =~ ^--- ]]; then
        in_skills=false
        continue
      fi
      # 提取 skill 名称
      skill_name=$(echo "$line" | sed -n 's/^[[:space:]]*-[[:space:]]*//p' | sed 's/[[:space:]]*#.*//')
      if [ -n "$skill_name" ]; then
        # 检查 skill 目录是否存在
        if [ ! -d "$SKILLS_DIR/$skill_name" ]; then
          echo "  ⚠️  $agent_name 引用了不存在的 skill: $skill_name"
          WARNINGS=$((WARNINGS + 1))
        fi
      fi
    fi
  done < "$agent_file"
done
if [ $? -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo "  ✅ 所有 skill 引用完整"
fi

echo ""

# ---------- 4. 知识库路径检查 ----------
echo "📚 知识库路径检查："
CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
  # 提取 CLAUDE.md 中引用的所有 KB 目录
  MISSING_DIRS=0
  while IFS= read -r dir; do
    # 只检查 00-15 编号的目录
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

# ---------- 5. 红线密钥检查 ----------
echo "🔑 密钥泄露红线检查："
for agent_file in "$AGENTS_DIR"/*.md; do
  agent_name=$(basename "$agent_file" .md)
  if ! grep -q "不泄露任何密钥\|不泄露.*API key" "$agent_file" 2>/dev/null; then
    echo "  ❌ $agent_name — 缺少密钥泄露红线"
    ERRORS=$((ERRORS + 1))
  fi
done
if [ $? -eq 0 ] && [ $ERRORS -eq 0 ]; then
  echo "  ✅ 所有 Agent 都有密钥泄露红线"
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
