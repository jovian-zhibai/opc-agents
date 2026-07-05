#!/bin/bash
# Lessons Index 搜索脚本
# 扫描 08-Lessons/ 目录，匹配文件名 + 正文
# 用法: bash search.sh "关键词"
# 输出：命中时输出文件路径 + 原文；未命中静默返回（空输出，退出码 0）

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


matched=0
for lesson_file in "$LESSONS_DIR"/*.md; do
    # 跳过非文件
    if [ ! -f "$lesson_file" ]; then
        continue
    fi

    filename=$(basename "$lesson_file")
    # 用临时文件读取内容，避免 pipe 问题
    file_content=$(grep -v '^$' "$lesson_file" 2>/dev/null || true)

    # 匹配文件名 + 正文（here-string，不用 pipe）
    if grep -qi "$query" <<<"$filename$file_content" 2>/dev/null; then
        echo "=== $lesson_file ==="
        cat "$lesson_file" 2>/dev/null || true
        echo ""
        matched=$((matched + 1))
    fi
done

# 已命中时输出提示；未命中时静默
if [ "$matched" -ge 1 ]; then
    echo "找到 $matched 条相关教训，建议在开始任务前阅读。"
fi
exit 0
