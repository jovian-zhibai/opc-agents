# 故障管道

DETECTED → TRIAGED → MITIGATED → RESOLVED → POSTMORTEM

| 阶段 | 负责Agent | 产出 |
|------|----------|------|
| DETECTED | Guardian/Ops | 告警信息 |
| TRIAGED | Director | 风险评级(P0/P1/P2) |
| MITIGATED | Ops | 临时止血措施 |
| RESOLVED | Dev | 根因修复 |
| POSTMORTEM | Director | 复盘报告，写入知识库04-Solutions/ |
