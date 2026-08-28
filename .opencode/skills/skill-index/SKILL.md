---
name: skill-index
description: >
  本地 skill 发现工具。当你需要某种能力但不确定用哪个 skill 时调用此 skill。
  输入：描述你在找什么能力的关键词（如 "PDF 处理" "React 测试" "数据库迁移"，可多词）。
  输出：匹配的 skill 名称 + 描述列表（名称命中优先、命中词越多越靠前），从中选出最合适的再调用。
  注意：此 skill 只做检索发现，不执行具体任务；找到对应 skill 后必须再调它完成工作。
  设计：以运行环境为准——实时扫描本机所有 skill 目录，装了什么就搜什么，增删自动生效；
  不假设某个 skill 必须存在，缺失时给出提示而非报错。
---

# Skill Index

在本地已安装的 skill 中搜索匹配项。

## 用法

调用 `search.sh` 并传入查询关键词（支持空格分隔的多关键词）：
```bash
echo "React 组件 测试" | bash search.sh
echo "PDF 生成" | bash search.sh
```

返回匹配的 skill 列表（name + description），排序规则：
1. **名称命中的排前面**（skill 名直接包含关键词，最相关）
2. **命中词越多越靠前**（多个关键词都命中的更匹配）
3. 描述命中排在名称命中之后

从中选择最相关的再调用。若未找到，换更通用的关键词重试。

## 原理

实时扫描 skill 目录中所有 `SKILL.md` 的 YAML front matter，按关键词匹配 `name` 和 `description` 字段。
扫描范围包括 `~/.claude/skills`、`~/.agents/skills`、`~/.config/opencode/agents`、`.opencode/skills` 等
所有已安装 skill 的位置。新安装的 skill 自动生效，无需手动维护索引。
