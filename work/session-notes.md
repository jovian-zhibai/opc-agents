# OPC Session Notes
# 格式：[日期] [Agent] 发现/注意：[一句话要点]
# 例：[2026-07-11] QA 提示：Dev 登录模块漏了输入校验，下次类似功能注意
# 例：[2026-07-11] Guardian 发现：express 4.18.2 有个 CVE
# 每次新会话启动时读最后 20 行，同一个坑不踩第二次。

[2026-07-05] Director 注册：ZhiWei 项目 (知微，商机发现与推演系统)，路径 /Users/souljian/code/ZhiWei，P0-P3 核心链路已完成

[2026-08-13] Dev 修复 grove 404：fetchProviderModels 用 u.origin+'/models' 丢 baseUrl 路径(如 /v1)导致 OpenAI 兼容端点 /models 404；改为保留完整路径拼接。教训：拼 API URL 别用 u.origin 丢路径，先 baseUrl+尾斜杠处理再拼 '/models'。

[2026-08-16] Director 总结：opc-agents 全面升级日。① 两轮审查修复 15 项问题（4.8 漂移检查重写/4b 驼峰/产出物 gc 清除/密钥占位）② 三项优化（任务前查教训 hook、sync 红线段同步、CLAUDE.md 瘦身 357→303）③ 补齐 5 项缺口（教训确认闸 draft 过滤、pre-commit 自动跑 gate、审查报告归档、RULES-CHANGELOG、session-notes 引导注入）④ 教训 3 条入库（产出物不入库/检查机制自身也要被检查/双向 diff 误报）⑤ 质量评分 6.5→8.5。注意：教训/流程机制已迁移到双运行时（pi 纯净删扩展 / CC 用 .claude/hooks/lessons-prompt.py UserPromptSubmit hook / OC 用 director.md 会话启动自动检查章节）；pre-commit 已配（规则文件改动自动跑 gate）；opc-tool 实验已废弃删除（确认原 opc-agents 模式是对的，别重蹈覆辙造轮子）。
