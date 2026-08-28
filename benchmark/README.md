# Advisor Prompt 精简基准测试

> 目标：验证 Advisor prompt 中"波特五力/SWOT/决策矩阵"三个教科书框架的精简是否导致弱模型（SenseNova）质量下降。
> 方法论：原版 vs 删减版，各跑 N=3-5 次，强模型盲评配对打分，任务完成度权重最高（50%）。

## 文件说明

| 文件 | 说明 |
|------|------|
| `tasks.md` | 3 道测试任务定义（每道题标明验哪个被砍框架） |
| `rubric.md` | 评分标准（5 维度，任务完成度权重 50%） |
| `advisor.trimmed.md` | 删减版候选文件（**不覆盖** prompts/advisor.md） |
| `run_advisor_benchmark.py` | 跑 SenseNova 测试的 harness |
| `judge_blind_pair.py` | 强模型盲评配对打分器 |
| `results/` | 测试结果输出目录 |

## 被砍框架

| 框架 | 原版行数 | 删减版行数 | 验证任务 |
|------|----------|------------|----------|
| 波特五力 | ~38 行 | 5 行 | 任务 1（主要）、任务 3（次要） |
| SWOT | ~29 行 | 5 行 | 任务 1（主要）、任务 3（次要） |
| 决策矩阵 | ~33 行 | 5 行 | 任务 2（主要）、任务 3（次要） |

原版 408 行 → 删减版 323 行（-85 行，-21%）。

## 使用方法

### 第 1 步：跑原版测试

```bash
# SenseNova 配置从 opencode.json 的 jensen003/souljian03 provider 读取
# 或设置环境变量 SENSENOVA_API_KEY / SENSENOVA_MODEL
python3 benchmark/run_advisor_benchmark.py --variant original --runs 3
```

### 第 2 步：跑删减版测试

```bash
python3 benchmark/run_advisor_benchmark.py --variant trimmed --runs 3
```

### 第 3 步：盲评配对打分

```bash
# 强模型裁判配置
export JUDGE_API_KEY="your-key"
export JUDGE_BASE_URL="https://api.example.com/v1"
export JUDGE_MODEL="gpt-4"  # 或 claude-opus 等

# 对每个任务打分
python3 benchmark/judge_blind_pair.py --task task1_market_entry --runs 3
python3 benchmark/judge_blind_pair.py --task task2_tech_selection --runs 3
python3 benchmark/judge_blind_pair.py --task task3_strategy --runs 3
```

## 判定规则

- 删减版总分 ≥ 原版总分的 95% → 质量不降，可考虑删减
- 删减版总分 < 原版总分的 95% → 质量下降，保留原版
- 结论存疑（分数接近、方差大）→ 默认保留原版

## 方法论铁律

1. **先跑基线存分**：原版先跑，分数存底
2. **harness 冻结后再动刀**：测试框架稳定后才改 prompt
3. **每变体跑 N=3-5 次比分布**：不看单次（弱模型有温度，单次可能被噪声带偏）
4. **裁判盲评+配对**：不告诉裁判哪个是原版/删减版，A/B 放同一次请求直接对比
5. **结论存疑默认保留**：宁可保留冗余，不冒质量下降的风险

## 注意事项

- `advisor.trimmed.md` 是**候选文件**，基准判定"质量不降"之后才回填 `prompts/advisor.md`
- 现阶段 `prompts/advisor.md` 保持不动
- 测试需要花钱（SenseNova API 调用 + 强模型裁判调用），请确认预算后再跑
