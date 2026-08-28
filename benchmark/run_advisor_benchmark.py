#!/usr/bin/env python3
"""
Advisor 基准测试运行器。

用法：
  python3 benchmark/run_advisor_benchmark.py --variant original --runs 3
  python3 benchmark/run_advisor_benchmark.py --variant trimmed --runs 3

配置：
  - API endpoint 和 key 从环境变量或 opencode.json 读取（JENSEN003/SOULJIAN03 provider）
  - 模型名通过 --model 参数指定，或从环境变量 SENSENOVA_MODEL 读取

输出：
  - benchmark/results/{task_id}_{variant}_{run}.md  原始模型输出
  - benchmark/results/summary_{variant}.json          运行摘要
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCHMARK_DIR / "results"

# 任务定义（与 benchmark/tasks.md 一致）
TASKS = [
    {
        "id": "task1_market_entry",
        "name": "新市场进入分析",
        "prompt": (
            "我们是一个做 AI 代码助手的小团队，目前产品是云端 SaaS。"
            "现在创始人想进入\"AI 代码助手私有化部署\"市场（卖给有数据合规要求的中大型企业）。\n\n"
            "请分析：这个市场值不值得进？我们的处境如何？给出你的判断和建议。\n"
            "不需要写代码，只做分析。"
        ),
        "frameworks_tested": ["波特五力", "SWOT"],
    },
    {
        "id": "task2_tech_selection",
        "name": "技术方案选型对比",
        "prompt": (
            "我们要给产品加一个\"代码搜索\"功能，有三个方案：\n"
            "1. 方案 A（自研）：用 Elasticsearch 自建索引，开发量 4 人周，后续维护需 1 人/月，搜索质量可控但需持续优化\n"
            "2. 方案 B（开源）：用 Sourcegraph 开源版部署，开发量 1 人周，维护需 0.5 人/月，功能全但服务器成本高（需 16G 内存机器）\n"
            "3. 方案 C（SaaS）：用第三方代码搜索 API，开发量 0.5 人周，无维护成本，但按调用量付费（预估月费 $200-$500），且代码要发给第三方\n\n"
            "请帮我对比这三个方案，给出推荐。我们团队 3 个开发，预算有限，代码安全是顾虑但不是绝对红线。"
        ),
        "frameworks_tested": ["决策矩阵"],
    },
    {
        "id": "task3_strategy",
        "name": "产品线战略取舍",
        "prompt": (
            "我们公司现在有两条产品线：\n"
            "- 产品线 X：AI 代码助手 SaaS，月收入 $5K，增长慢（月增 5%），竞争激烈，团队花 60% 时间维护\n"
            "- 产品线 Y：AI 代码助手私有化部署，月收入 $1K，增长快（月增 30%），但客户少（3 个），团队花 40% 时间\n\n"
            "创始人在考虑：要不要砍掉 X，全力做 Y？还是反过来？还是两条都保留？\n\n"
            "请帮我分析这个决策，给出你的建议。注意：团队只有 3 个人，资金只够撑 6 个月。"
        ),
        "frameworks_tested": ["第一性原理", "SWOT", "决策矩阵", "认知偏差"],
    },
]


def load_prompt_file(variant: str) -> str:
    """加载 Advisor prompt 文件。"""
    if variant == "original":
        path = PROJECT_ROOT / "prompts" / "advisor.md"
    elif variant == "trimmed":
        path = BENCHMARK_DIR / "advisor.trimmed.md"
    else:
        raise ValueError(f"未知 variant: {variant}")
    if not path.exists():
        raise FileNotFoundError(f"prompt 文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def load_sensenova_config():
    """从 opencode.json 加载 SenseNova 配置（JENSEN003/SOULJIAN03 provider）。"""
    config_path = PROJECT_ROOT / "opencode.json"
    if not config_path.exists():
        return None
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        # 查找 JENSEN003 或 SOULJIAN03 provider
        providers = config.get("providers", {})
        for name in ["jensen003", "souljian03", "JENSEN003", "SOULJIAN03"]:
            if name in providers:
                p = providers[name]
                return {
                    "base_url": p.get("base_url") or p.get("api_base"),
                    "api_key": p.get("api_key") or os.environ.get("SENSENOVA_API_KEY"),
                    "model": p.get("model") or os.environ.get("SENSENOVA_MODEL", "sensenova"),
                }
        return None
    except (json.JSONDecodeError, KeyError):
        return None


def call_llm(system_prompt: str, user_prompt: str, config: dict, model: str = None) -> str:
    """调用 LLM API（OpenAI 兼容格式）。"""
    try:
        from openai import OpenAI
    except ImportError:
        print("错误：需要安装 openai 库。运行: pip install openai", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )

    response = client.chat.completions.create(
        model=model or config["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,  # 适中温度，允许一定变化
        max_tokens=4096,
    )
    return response.choices[0].message.content


def run_benchmark(variant: str, runs: int, model: str = None, delay: int = 2):
    """运行基准测试。"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 加载配置
    config = load_sensenova_config()
    if not config or not config.get("api_key"):
        print("错误：未找到 SenseNova API 配置。", file=sys.stderr)
        print("请在 opencode.json 中配置 jensen003/souljian03 provider，", file=sys.stderr)
        print("或设置环境变量 SENSENOVA_API_KEY 和 SENSENOVA_MODEL。", file=sys.stderr)
        sys.exit(1)

    if model:
        config["model"] = model

    print(f"=== Advisor 基准测试 ===")
    print(f"变体: {variant}")
    print(f"每次任务运行次数: {runs}")
    print(f"模型: {config['model']}")
    print(f"API endpoint: {config['base_url']}")
    print()

    # 加载 prompt
    system_prompt = load_prompt_file(variant)
    print(f"已加载 prompt: {len(system_prompt)} 字符")
    print()

    summary = {
        "variant": variant,
        "model": config["model"],
        "runs_per_task": runs,
        "tasks": [],
    }

    for task in TASKS:
        print(f"--- 任务: {task['name']} ({task['id']}) ---")
        print(f"  验证框架: {', '.join(task['frameworks_tested'])}")

        task_results = []
        for run in range(1, runs + 1):
            print(f"  运行 {run}/{runs}...", end=" ", flush=True)
            try:
                output = call_llm(system_prompt, task["prompt"], config)
                # 保存原始输出
                out_file = RESULTS_DIR / f"{task['id']}_{variant}_{run}.md"
                out_file.write_text(output, encoding="utf-8")
                task_results.append({
                    "run": run,
                    "output_file": str(out_file),
                    "output_length": len(output),
                    "status": "success",
                })
                print(f"✅ ({len(output)} 字符)")
            except Exception as e:
                task_results.append({
                    "run": run,
                    "status": "error",
                    "error": str(e),
                })
                print(f"❌ {e}")

            if run < runs:
                time.sleep(delay)  # 避免限流

        summary["tasks"].append({
            "id": task["id"],
            "name": task["name"],
            "frameworks_tested": task["frameworks_tested"],
            "results": task_results,
        })
        print()

    # 保存摘要
    summary_file = RESULTS_DIR / f"summary_{variant}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"摘要已保存: {summary_file}")
    print()
    print("=== 完成 ===")
    print(f"原始输出目录: {RESULTS_DIR}")
    print(f"下一步: 运行 judge_blind_pair.py 进行盲评配对打分")


def main():
    parser = argparse.ArgumentParser(description="Advisor 基准测试运行器")
    parser.add_argument("--variant", choices=["original", "trimmed"], required=True,
                        help="测试变体: original(原版) / trimmed(删减版)")
    parser.add_argument("--runs", type=int, default=3,
                        help="每个任务运行次数（建议 3-5，比分布不看单次）")
    parser.add_argument("--model", type=str, default=None,
                        help="模型名（覆盖 opencode.json 中的配置）")
    parser.add_argument("--delay", type=int, default=2,
                        help="每次调用之间的延迟秒数（避免限流）")
    args = parser.parse_args()

    run_benchmark(args.variant, args.runs, args.model, args.delay)


if __name__ == "__main__":
    main()
