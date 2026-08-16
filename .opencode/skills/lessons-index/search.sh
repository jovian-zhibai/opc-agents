#!/bin/bash
# Lessons Index 搜索脚本
# 扫描 08-Lessons/ 目录，匹配文件名 + 正文
# 用法: bash search.sh "关键词"
# 输出：命中时输出文件路径 + 原文；未命中静默返回（空输出，退出码 0）
# 防刷屏：命中 >3 条时只列路径不 cat 全文；≤3 条才输出完整正文。

set -euo pipefail

# 确定教训库路径（脚本内写死回退，不依赖环境变量存在）
LESSONS_DIR="${OPC_KNOWLEDGE_PATH:-$HOME/code/opc/opc-knowledge}/08-Lessons"

# 目录不存在时静默退出
if [ ! -d "$LESSONS_DIR" ]; then
    exit 0
fi

query="${1:-}"
# 无查询词时静默退出
if [ -z "$query" ]; then
    exit 0
fi

# 最多输出完整正文的命中条数；超过则只列路径，避免刷屏
MAX_FULL=3

matched_files=()
for lesson_file in "$LESSONS_DIR"/*.md; do
    # 跳过非文件
    if [ ! -f "$lesson_file" ]; then
        continue
    fi

    # 状态过滤（确认闸）：draft 草稿不参与检索；active 或未标注 status 视为有效
    # （历史教训无 front matter 属正常，默认视为 active 保留检索价值）
    if grep -q "^status:[[:space:]]*draft" "$lesson_file" 2>/dev/null; then
        continue
    fi

    filename=$(basename "$lesson_file")
    # 用临时变量读取内容，避免 pipe 问题
    file_content=$(grep -v '^$' "$lesson_file" 2>/dev/null || true)

    # 匹配文件名 + 正文（here-string，不用 pipe）
    if grep -qi "$query" <<<"$filename$file_content" 2>/dev/null; then
        matched_files+=("$lesson_file")
    fi
done

matched=${#matched_files[@]}
# 未命中时静默退出
if [ "$matched" -eq 0 ]; then
    exit 0
fi

echo "找到 $matched 条相关教训，建议在开始任务前阅读。"

if [ "$matched" -le "$MAX_FULL" ]; then
    # 命中较少：输出完整正文
    for lesson_file in "${matched_files[@]}"; do
        echo ""
        echo "=== $lesson_file ==="
        cat "$lesson_file" 2>/dev/null || true
        echo ""
    done
else
    # 命中较多：只列路径，避免刷屏；提示用更精确的关键词重搜
    echo "（命中较多，仅列出文件路径。需要详情请用更精确的关键词重搜。）"
    for lesson_file in "${matched_files[@]}"; do
        echo "  $lesson_file"
    done
fi
exit 0
