# OPC Agents

一人公司（One Person Company）的 AI Agent 团队系统。

基于 Claude Code 的 slash 命令 + CLAUDE.md + 独立提示词文件构建。

## 架构

1 个指挥 + 8 个执行：

- **Director**：总指挥（内置于 CLAUDE.md），/director 深度调度
- **Advisor**：智囊，/advisor 思维伙伴
- **Product**：产品经理，/product 需求梳理
- **Dev**：高级工程师，/dev 代码实现
- **QA**：测试工程师，/qa 质量守门
- **Ops**：运维工程师，/ops 部署监控
- **Growth**：增长运营，/growth 内容用户
- **Finance**：财务合规，/finance 记账预警
- **Guardian**：问题发现者，/guardian 风险巡检

## 快速开始

1. Clone 本仓库
2. 在目录下启动 Claude Code
3. 首次启动会自动进入初始化流程

## 知识库

通过 MCP 接入 Obsidian，详见 CLAUDE.md 中的知识库配置。

## 原则

- Agent 负责执行层，创始人负责决策层
- QA 和 Guardian 的首要职责是质疑，不是配合
- 文档是交付物的一部分
- 不读取上下文就开工 = 返工
- 知识有保质期，超过 180 天需复审
