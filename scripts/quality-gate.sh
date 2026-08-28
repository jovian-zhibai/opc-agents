#!/bin/bash
# OPC Agent 一致性检查（五运行时版）
# 检查 prompts/（唯一真相源）+ 各运行时 agents/ 目录的引用一致性和完整性
# 当前主检查 prompts/ vs .opencode/agents/，CLAUDE.md 标记块单独校验

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMPTS_DIR="$PROJECT_DIR/prompts"
AGENTS_DIR="$PROJECT_DIR/.opencode/agents"
SKILLS_DIR="$PROJECT_DIR/.opencode/skills"
KNOWLEDGE="${OPC_KNOWLEDGE_PATH:-$HOME/code/opc/opc-knowledge}"

ERRORS=0
WARNINGS=0

echo "=== OPC Agent 一致性检查（五运行时版） ==="
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
  if ! grep -qE "## (核心职责|核心能力|你的定位|核心原则)" "$prompt_file" 2>/dev/null &&
    ! grep -qE "## (红线|协作接口|产出规则|工作流程)" "$prompt_file" 2>/dev/null; then
    echo "  ❌ $agent_name — 缺少核心职责/红线/协作接口等关键章节"
    ERRORS=$((ERRORS + 1))
  fi
done
if [ $ERRORS -eq 0 ]; then
  echo "  ✅ 所有 prompt 关键章节完整"
fi

echo ""

# ---------- 2.5. prompts/ Front matter 完整性 ----------
# prompts/ 为 Claude Code 共享版，按设计不含 front matter（front matter 是 .opencode/agents/ 的 OpenCode 专属机制）。
# 因此「无 front matter」不构成警告（降级为 ℹ️ 信息），只检查「有开头 --- 但未闭合」的结构错误。
echo "📋 prompts/ front matter 检查："
pm_errors=0
pm_without_fm=0
for prompt_file in "$PROMPTS_DIR"/*.md; do
  agent_name=$(basename "$prompt_file" .md)
  first_line=$(head -1 "$prompt_file" 2>/dev/null)
  if [ "$first_line" = "---" ]; then
    # 有开头 ---，检查 10 行内是否有闭合 ---
    fm_block=$(sed -n '2,10p' "$prompt_file" 2>/dev/null)
    if ! grep -q '^---$' <<<"$fm_block"; then
      echo "  ❌ $agent_name — front matter 有开头 --- 但 10 行内无闭合 ---"
      pm_errors=$((pm_errors + 1))
    fi
  else
    pm_without_fm=$((pm_without_fm + 1))
  fi
done
if [ "$pm_errors" -eq 0 ]; then
  echo "  ✅ 所有 prompts/ front matter 结构完整"
  if [ "$pm_without_fm" -gt 0 ]; then
    echo "  ℹ️  $pm_without_fm 个 prompts/ 无 front matter（设计如此，Claude Code 共享版不要求 front matter）"
  fi
else
  ERRORS=$((ERRORS + pm_errors))
fi

echo ""

# ---------- 3. .opencode/agents/ Front matter 完整性 ----------
echo "📋 OpenCode front matter 检查："
if [ -d "$AGENTS_DIR" ]; then
  REQUIRED_FIELDS=("description" "mode" "temperature" "steps")
  fm_errors=0
  for agent_file in "$AGENTS_DIR"/*.md; do
    agent_name=$(basename "$agent_file" .md)
    fm=$(sed -n '/^---$/,/^---$/p' "$agent_file" 2>/dev/null)
    for field in "${REQUIRED_FIELDS[@]}"; do
      if ! grep -q "^$field:" <<<"$fm"; then
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

# 收集实际 prompt 列表（后续检查复用）
ACTUAL_PROMPTS=()
for f in "$PROMPTS_DIR"/*.md; do
  ACTUAL_PROMPTS+=("$(basename "$f" .md)")
done

# ---------- 4. routing.yaml 一致性检查 ----------
echo "🔗 routing.yaml 一致性检查："
ROUTING_YAML="$PROJECT_DIR/routing.yaml"

# 4a. routing.yaml 是否存在
if [ ! -f "$ROUTING_YAML" ]; then
  echo "  ❌ routing.yaml 不存在（单一真相源缺失）"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✅ routing.yaml 存在"

  # 4b. 检查 prompt 名是否在 routing.yaml agent 字段中出现（大小写不敏感，连字符/驼峰归一化）
  for a in "${ACTUAL_PROMPTS[@]}"; do
    # agent-manager → AgentManager（macOS sed 不支持 \U，用 bash 拼接）
    camel="$(echo "$a" | awk -F- '{ for(i=1;i<=NF;i++){ $i=toupper(substr($i,1,1)) substr($i,2) } print }' OFS='')"
    if ! grep -qiE "agent:.*($a|$camel)" "$ROUTING_YAML" 2>/dev/null; then
      echo "  ⚠️  $a 存在于 prompts/ 但 routing.yaml 未引用"
      WARNINGS=$((WARNINGS + 1))
    fi
  done

  # 4c. 检查三份 director 是否都引用 routing.yaml 而非手写归属表
  routing_ok=true
  for f in "$PROJECT_DIR/CLAUDE.md" "$PROMPTS_DIR/director.md" "$AGENTS_DIR/director.md"; do
    fname=$(basename "$(dirname "$f")")/$(basename "$f")
    if [ -f "$f" ]; then
      if ! grep -q "routing.yaml" "$f" 2>/dev/null; then
        echo "  ❌ $fname 未引用 routing.yaml，可能仍在手写归属表"
        ERRORS=$((ERRORS + 1))
        routing_ok=false
      fi
    fi
  done
  if $routing_ok; then
    echo "  ✅ 所有 director 均引用 routing.yaml"
  fi
fi

echo ""

# ---------- 4.5. Director 漂移检查（prompts/ vs .opencode/） ----------
echo "🔍 Director 漂移检查："
PROMPTS_DIRECTOR="$PROMPTS_DIR/director.md"
OPENCODE_DIRECTOR="$AGENTS_DIR/director.md"

if [ -f "$PROMPTS_DIRECTOR" ] && [ -f "$OPENCODE_DIRECTOR" ]; then
  DRIFT_ERRORS=0

  # 提取核心章节进行比对（排除 front matter 和运行时特有内容）
  # 检查质量门禁是否一致
  PROMPTS_GATE=$(grep "覆盖率达标" "$PROMPTS_DIRECTOR" 2>/dev/null || echo "")
  OPENCODE_GATE=$(grep "覆盖率达标" "$OPENCODE_DIRECTOR" 2>/dev/null || echo "")
  if [ "$PROMPTS_GATE" != "$OPENCODE_GATE" ]; then
    echo "  ❌ 质量门禁不一致"
    echo "     prompts/director.md: $PROMPTS_GATE"
    echo "     .opencode/agents/director.md: $OPENCODE_GATE"
    DRIFT_ERRORS=$((DRIFT_ERRORS + 1))
  fi

  # 检查归属表引用是否一致（都引 routing.yaml 而非手写）
  PROMPTS_ROUTING=$(grep -c "routing.yaml" "$PROMPTS_DIRECTOR" 2>/dev/null || echo "0")
  OPENCODE_ROUTING=$(grep -c "routing.yaml" "$OPENCODE_DIRECTOR" 2>/dev/null || echo "0")
  if [ "$PROMPTS_ROUTING" -eq 0 ] || [ "$OPENCODE_ROUTING" -eq 0 ]; then
    echo "  ❌ 至少一份 director 未引用 routing.yaml（漂移风险）"
    DRIFT_ERRORS=$((DRIFT_ERRORS + 1))
  fi

  # 检查"兼容声明"红线是否在两份中同步（连这条不同步就是讽刺）
  if ! grep -q "不改规则不同步" "$PROMPTS_DIRECTOR" 2>/dev/null ||
    ! grep -q "不改规则不同步" "$OPENCODE_DIRECTOR" 2>/dev/null; then
    echo "  ❌ '不改规则不同步'红线在其中一份 director 中缺失，连兼容声明本身都没同步"
    DRIFT_ERRORS=$((DRIFT_ERRORS + 1))
  fi

  # 检查"会话收尾/反馈信号"节（阶段三反馈线）是否同步——正文漂移靠多锚点捕获
  for anchor in "反馈信号" "agent-metrics" "会话收尾"; do
    if ! grep -q "$anchor" "$PROMPTS_DIRECTOR" 2>/dev/null ||
      ! grep -q "$anchor" "$OPENCODE_DIRECTOR" 2>/dev/null; then
      echo "  ❌ 锚点 '$anchor' 未在两份 director 中同时存在（反馈信号节漂移，正文未同步）"
      DRIFT_ERRORS=$((DRIFT_ERRORS + 1))
    fi
  done

  if [ "$DRIFT_ERRORS" -eq 0 ]; then
    echo "  ✅ 两份 director 核心内容一致"
  else
    ERRORS=$((ERRORS + DRIFT_ERRORS))
  fi
else
  echo "  ⚠️  缺少 director 文件，跳过漂移检查"
fi

echo ""

# ---------- 4.6. 阶段三产物检查 ----------
echo "🔗 阶段三产物检查："
FEEDBACK_SCHEMA="$PROJECT_DIR/feedback.schema.json"
AGENT_MANAGER="$PROMPTS_DIR/agent-manager.md"

# 4.6a. feedback.schema.json 存在性
if [ ! -f "$FEEDBACK_SCHEMA" ]; then
  echo "  ⚠️  feedback.schema.json 不存在（阶段三反馈信号定义缺失）"
  WARNINGS=$((WARNINGS + 1))
else
  echo "  ✅ feedback.schema.json 存在"
fi

# 4.6b. agent-manager.md 是否引用 feedback.schema.json
if [ -f "$AGENT_MANAGER" ]; then
  if ! grep -q "feedback.schema.json" "$AGENT_MANAGER" 2>/dev/null; then
    echo "  ⚠️  agent-manager.md 未引用 feedback.schema.json（阶段三反馈线未接通）"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  ✅ agent-manager.md 已引用 feedback.schema.json"
  fi
fi

echo ""

# ---------- 4.7. 子 Agent 职责边界表一致性 ----------
echo "🔍 子 Agent 职责边界表检查："
BOUNDARY_HEADERS=("与其他 Agent 的职责边界" "代码审查分工")
boundary_errors=0

for a in "${ACTUAL_PROMPTS[@]}"; do
  [ "$a" = "director" ] && continue # director 走 4.5 专门检查
  prompts_f="$PROMPTS_DIR/$a.md"
  opencode_f="$AGENTS_DIR/$a.md"
  [ ! -f "$prompts_f" ] || [ ! -f "$opencode_f" ] && continue

  for hdr in "${BOUNDARY_HEADERS[@]}"; do
    # 检查标题存在性：一版有、另一版必须有
    if grep -q "$hdr" "$prompts_f" 2>/dev/null; then
      in_prompts=1
    else
      in_prompts=0
    fi
    if grep -q "$hdr" "$opencode_f" 2>/dev/null; then
      in_opencode=1
    else
      in_opencode=0
    fi
    if [ "$in_prompts" -ne "$in_opencode" ]; then
      if [ "$in_prompts" -eq 1 ]; then
        echo "  ❌ $a: '$hdr' 在 prompts/ 中存在但 opencode 版缺失"
      else
        echo "  ❌ $a: '$hdr' 在 opencode 版中存在但 prompts/ 缺失"
      fi
      boundary_errors=$((boundary_errors + 1))
    fi
  done
done

if [ "$boundary_errors" -eq 0 ]; then
  echo "  ✅ 所有子 Agent 职责边界表 prompts 版与 opencode 版一致"
else
  ERRORS=$((ERRORS + boundary_errors))
fi

# ---------- 4.8. 关键字段漂移检查（prompts/ vs .opencode/ 行为级） ----------
# 锚点检查查不出正文漂移（2026-08-16 审查发现 9/10 文件存在行为级差异）。
# 这里对每个角色文件校验关键字段（红线/路径变量/环境变量）是否 prompts 版与 opencode 版同步。
# 注：路径前缀（$OPC_WORK_PATH vs .opencode/work）是有意设计的两环境差异，不做硬比对。
# ---------- 4.8. 角色文件内容级漂移检查（prompts/ vs .opencode/） ----------
# 锚点 grep 判别力为零（2026-08-16 重审确认），改为逐行 diff 归一化内容：
#   - 去掉 front matter（仅当文件首行是 --- 时才进入 front matter 模式，
#     避免正文中间的 --- 分隔线被误当 front matter 边界——ui-ux/finance 曾因此丢整段）
#   - 归一化路径前缀（$OPC_WORK_PATH / .opencode/work / work/ 是两环境有意差异）
#   - 归一化空白
# 剩余差异行数超过阈值 → 报错（可能的行为级漂移）。
field_errors=0

for a in "${ACTUAL_PROMPTS[@]}"; do
  [ "$a" = "director" ] && continue
  prompts_f="$PROMPTS_DIR/$a.md"
  opencode_f="$AGENTS_DIR/$a.md"
  [ ! -f "$prompts_f" ] || [ ! -f "$opencode_f" ] && continue

  # 归一化函数：仅当首行是 --- 才去 front matter；正文中的 --- 分隔线保留
  normalize() {
    # 双引号内 \\\$ 输出字面 \$，sed 匹配字面 '$OPC_WORK_PATH' 文本（规避 SC2016）
    awk '
      NR == 1 && /^---$/ { in_fm=1; next }
      in_fm == 1 && /^---$/ { in_fm=0; next }   # front matter 结束
      in_fm == 0 { print }                        # 无 front matter 或已出 front matter：全部输出
    ' "$1" |
      sed -E "s#\\\$OPC_WORK_PATH#WORK#g; s#{{WORK_PATH}}#WORK#g; s#\.opencode/work#WORK#g; s#(^|[^A-Za-z])work/#WORK/#g" |
      sed -E "s/\\\$OPC_KNOWLEDGE_PATH/KB/g" |
      sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' |
      grep -vE '^$'
  }

  # 逐行 diff，只统计 prompts 独有行（< 方向）——prompts 是基准版，
  # prompts 有而 opencode 缺的才是危险漂移（红线/章节缺失）；
  # opencode 独有行（> 方向）多为更全内容，是有意差异不报错。
  prompts_only=$(diff <(normalize "$prompts_f") <(normalize "$opencode_f") 2>/dev/null | grep -cE '^<' || true)
  opencode_only=$(diff <(normalize "$prompts_f") <(normalize "$opencode_f") 2>/dev/null | grep -cE '^>' || true)
  if [ "$prompts_only" -gt 8 ]; then
    echo "  ❌ ${a}: prompts 版有 ${prompts_only} 行在 opencode 版缺失（opencode 多 ${opencode_only} 行）——疑似红线/章节漂移，请人工核对"
    field_errors=$((field_errors + 1))
  else
    echo "  ✅ ${a}: prompts 独有 ${prompts_only} 行（阈值内），opencode 多 ${opencode_only} 行（多为更全内容，接受）"
  fi

  # 红线专项检查：prompts 版含密钥泄露红线，opencode 版缺失 → 直接报错（不靠行数阈值）
  if grep -q "不泄露.*密钥\|不泄露.*API key" "$prompts_f" 2>/dev/null &&
    ! grep -q "不泄露.*密钥\|不泄露.*API key" "$opencode_f" 2>/dev/null; then
    echo "  ❌ ${a}: prompts 版含密钥泄露红线，opencode 版缺失——红线缺失属关键漂移"
    field_errors=$((field_errors + 1))
  fi
done

if [ "$field_errors" -eq 0 ]; then
  echo "  ✅ 所有子 Agent prompts 关键内容在 opencode 版均保留"
else
  ERRORS=$((ERRORS + field_errors))
fi

echo ""

# ---------- 5. Skill 引用检查 ----------
echo "🎯 Skill 引用完整性检查："
echo "  ℹ️  社区 skill 运行时安装、不提交仓库——以下缺失为预期，非错误。"
echo "  ℹ️  全局依赖见 routing.yaml『全局依赖』注释（如 anysearch 仅存在于 ~/.agents/skills/）。"
echo "  ℹ️  skill 缺失均按 Director 降级规则处理（搜索类走 webfetch 等），不阻塞，故不计数警告。"
if [ -d "$AGENTS_DIR" ]; then
  skill_missing=0
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
            # 逐个列出缺失项（不合并汇总），区分全局依赖与完全缺失
            if [ -d "$HOME/.agents/skills/$skill_name" ]; then
              echo "  ℹ️  ${agent_name} → ${skill_name}：全局依赖（存在于 ~/.agents/skills/，OpenCode 本地未安装属预期）"
            else
              echo "  ℹ️  ${agent_name} → ${skill_name}：本地与全局均不存在（社区 skill 未安装，或引用已失效——若 routing.yaml 未声明预期，建议核对）"
            fi
            skill_missing=$((skill_missing + 1))
          fi
        fi
      fi
    done <"$agent_file"
  done
  if [ "$skill_missing" -eq 0 ]; then
    echo "  ✅ 所有 skill 引用完整"
  else
    echo "  ℹ️  共 $skill_missing 个缺失（逐个见上；社区 skill 未安装属预期行为，不阻塞）"
  fi
fi

echo ""

# ---------- 6. 知识库路径检查 ----------
echo "📚 知识库路径检查："
CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
if [ ! -d "$KNOWLEDGE" ]; then
  echo "  ⚠️  知识库目录 $KNOWLEDGE 不存在，跳过（CI 环境正常现象）"
elif [ -f "$CLAUDE_MD" ]; then
  MISSING_DIRS=0
  KB_DIRS=$(awk '/^\| [0-9]{2}-/ {print $2}' "$CLAUDE_MD" 2>/dev/null | head -20 || true)
  while IFS= read -r dir; do
    [[ -z "$dir" ]] && continue
    if [[ "$dir" =~ ^[0-9]{2}- ]]; then
      if [ ! -d "$KNOWLEDGE/$dir" ]; then
        echo "  ❌ CLAUDE.md 引用知识库目录 $dir，但实际路径 $KNOWLEDGE/$dir 不存在"
        MISSING_DIRS=$((MISSING_DIRS + 1))
      fi
    fi
  done <<EOF
$KB_DIRS
EOF
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

# ---------- 7.5. Secret 字面值扫描 ----------
echo "🔑 Secret 字面值扫描（git tracked 文件）："
# 只扫『git 跟踪 + 未被 ignore 的未跟踪』文件（即会被提交进仓库的集合）：
#   - .env 已 .gitignore，本地含真实 key，纳入扫描只会误报——天然排除
#   - .env.example 是占位符模板，同样排除
#   - 排除 quality-gate.sh 自身（其正文含正则定义，属自引用误报）
SCAN_FILES=$(git ls-files --cached --others --exclude-standard 2>/dev/null |
  grep -vE '(^|/)\.env(\.example)?$' | grep -v '^scripts/quality-gate.sh$' || true)
SECRET_HITS=""
if [ -n "$SCAN_FILES" ]; then
  # 过滤掉含正则定义字面本身的命中（quality-gate.sh/ci.yml 等检查脚本正文含模式文本，属自引用误报）
  SECRET_HITS=$(printf '%s\n' "$SCAN_FILES" | xargs grep -nE 'sk-[A-Za-z0-9]{20,}|SENSENOVA_API_KEY=.{5,}|api_key=.{10,}|token=.{20,}' 2>/dev/null |
    grep -vF -e 'sk-[A-Za-z0-9]{20,}' -e 'api_key=.{10,}' -e 'token=.{20,}' -e 'SENSENOVA_API_KEY=.{5,}' \
      -e 'sk-\[A-Za-z0-9\]\{20,\}' -e 'api_key=\.\{10,\}' -e 'token=\.\{20,\}' -e 'SENSENOVA_API_KEY=\.\{5,\}' || true)
fi
if [ -n "$SECRET_HITS" ]; then
  echo "  ❌ 将被提交进仓库的文件中发现疑似硬编码密钥："
  echo "$SECRET_HITS" | while IFS= read -r line; do echo "     $line"; done
  ERRORS=$((ERRORS + 1))
else
  echo "  ✅ 将被提交的文件中未发现硬编码密钥（.env/.env.example 为本地配置与模板，不纳入）"
fi

echo ""

# ---------- 7.6. PreToolUse Hook 自检 ----------
echo "🔒 PreToolUse Hook 自检："
HOOK_SCRIPT="$PROJECT_DIR/.claude/hooks/protect-prompts.py"

if [ ! -f "$HOOK_SCRIPT" ]; then
  echo "  ⚠️  protect-prompts.py 不存在，跳过 hook 自检"
else
  if ! command -v python3 >/dev/null 2>&1; then
    echo "  ⚠️  python3 不可用，跳过 hook 自检（quality-gate 不依赖 python3，仅此节跳过）"
  else
    hook_errors=0
    hook_test() {
      local desc="$1" tool="$2" path="$3" expected="$4"
      local input="{\"tool_name\":\"$tool\",\"tool_input\":{\"file_path\":\"$path\"}}"
      local actual
      actual=$(echo "$input" | {
        python3 "$HOOK_SCRIPT" 2>/dev/null
        echo $?
      } || true)
      actual=$(echo "$actual" | tail -1)
      if [ "$actual" -ne "$expected" ]; then
        echo "  ❌ $desc -> exit $actual (expected $expected)"
        hook_errors=$((hook_errors + 1))
      fi
    }
    hook_test "CLAUDE.md 拦截" "Write" "CLAUDE.md" 1
    hook_test "routing.yaml 拦截" "Edit" "routing.yaml" 1
    hook_test "prompts/ 拦截" "Write" "prompts/qa.md" 1
    hook_test ".opencode/agents/ 拦截" "Edit" ".opencode/agents/director.md" 1
    hook_test "普通源码放行" "Write" "src/main.py" 0
    hook_test "Read 放行" "Read" "prompts/qa.md" 0

    if [ "$hook_errors" -eq 0 ]; then
      echo "  ✅ Hook 自检通过（关键路径 exit code 正确）"
    else
      echo "  ❌ Hook 自检 $hook_errors 项失败——物理保护可能失效"
      ERRORS=$((ERRORS + hook_errors))
    fi
  fi
fi

echo ""

# ---------- 8. 跨阶段 commit 扫描（warn only，非硬拦截） ----------
echo "🔍 跨阶段 commit 扫描（仅 warn，不阻塞）："
echo "  ⚠️  此检查只抓明显手滑，改 commit message 措辞即可绕过——不是安全门禁。"
echo "  真正的硬拦截是 Director 红线中的'不跨阶段提交'规则。"
LATEST_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "")
if grep -qi "阶段一\|阶段二\|阶段三" <<<"$LATEST_MSG" 2>/dev/null; then
  PHASE_COUNT=0
  grep -qi "阶段一" <<<"$LATEST_MSG" && PHASE_COUNT=$((PHASE_COUNT + 1))
  grep -qi "阶段二" <<<"$LATEST_MSG" && PHASE_COUNT=$((PHASE_COUNT + 1))
  grep -qi "阶段三" <<<"$LATEST_MSG" && PHASE_COUNT=$((PHASE_COUNT + 1))
  if [ "$PHASE_COUNT" -ge 2 ]; then
    echo "  ⚠️  最近一次 commit 疑似跨阶段打包（含 $PHASE_COUNT 个阶段标记），请确认是否经创始人逐阶段确认"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  ✅ 最近 commit 未检测到跨阶段标记"
  fi
else
  echo "  ✅ 最近 commit 未检测到阶段标记"
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
