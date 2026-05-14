# 开发管道

IDEA → GROOMED → SCOPED → DESIGNED → IMPLEMENTED → TESTED → REVIEWED → MERGED → DEPLOYED → DONE

| 阶段 | 负责Agent | 产出 | 质量门禁 |
|------|----------|------|---------|
| IDEA | 创始人 | 粗略想法 | 无 |
| GROOMED | Product | PRD+验收标准 | PRD格式完整 |
| SCOPED | Dev | 技术方案 | 方案可行 |
| DESIGNED | Product+Dev | UI/交互描述 | 关键页面已描述 |
| IMPLEMENTED | Dev | 代码+PR | 编译通过 |
| TESTED | QA | 测试报告 | 覆盖率/lint/类型通过 |
| REVIEWED | QA | 审查通过 | 无未解决Comment |
| MERGED | Dev | 合并到main | CI绿灯 |
| DEPLOYED | Ops | 线上可访问 | 健康检查通过 |
| DONE | Director | 关闭Issue | 验收标准满足 |

## 回退规则

- TESTED→IMPLEMENTED：测试不通过
- REVIEWED→IMPLEMENTED：审查发现重大问题
- DEPLOYED→MERGED：部署失败，Ops回滚
