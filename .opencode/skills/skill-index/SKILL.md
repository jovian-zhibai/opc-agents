---
name: skill-index
description: >
  本地 skill 发现工具。当你需要某种能力但不确定用哪个 skill 时调用此 skill。
  输入：描述你在找什么能力的关键词（如 "PDF 处理" "React 测试" "数据库迁移"）。
  输出：匹配的 skill 名称 + 描述列表，从中选出最合适的再调用。
  注意：此 skill 只做检索发现，不执行具体任务；找到对应 skill 后必须再调它完成工作。
---

# Skill Index

在本地已安装的 skill 中搜索匹配项。

## 用法

调用 `search.sh` 并传入查询关键词：
```bash
bash search.sh "PDF 生成"
```
返回匹配的 skill 列表（name + description），从中选择最相关的再调用。

## 原理

实时扫描 skill 目录中所有 `SKILL.md` 的 YAML front matter，按关键词匹配 `name` 和 `description` 字段。新安装的 skill 自动生效，无需手动维护索引。
