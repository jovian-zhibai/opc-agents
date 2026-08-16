# OPC Session Notes
# 格式：[日期] [Agent] 发现/注意：[一句话要点]
# 例：[2026-07-11] QA 提示：Dev 登录模块漏了输入校验，下次类似功能注意
# 例：[2026-07-11] Guardian 发现：express 4.18.2 有个 CVE
# 每次新会话启动时读最后 20 行，同一个坑不踩第二次。

[2026-07-05] Director 注册：ZhiWei 项目 (知微，商机发现与推演系统)，路径 /Users/souljian/code/ZhiWei，P0-P3 核心链路已完成

[2026-08-13] Dev 修复 grove 404：fetchProviderModels 用 u.origin+'/models' 丢 baseUrl 路径(如 /v1)导致 OpenAI 兼容端点 /models 404；改为保留完整路径拼接。教训：拼 API URL 别用 u.origin 丢路径，先 baseUrl+尾斜杠处理再拼 '/models'。
