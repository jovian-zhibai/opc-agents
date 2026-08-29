#!/usr/bin/env python3
"""
结构化通信 · 真实任务三臂对比运行器 v2。

三臂：
  A = 现状自由（无结构化产出要求，普通 Dev prompt）
  B = prose 强制（benchmark/dev-b-prose-v2.md）
  C = 完整 schema（benchmark/dev-c-schema-v2.md）

3 个真实任务（有上游材料）× 3 臂 × 2 次 = 18 次，SenseNova。

不自动判分，只保存原始产出。人工判两件事：
  ① 上游信息完整性（下游有没有拿到上游的关键事实）
  ② 编造（判断字段没内容时是老实写"无"还是硬编）

用法：
  python3 benchmark/run_real_tasks_v2.py --runs 2
  python3 benchmark/run_real_tasks_v2.py --runs 2 --arm A  # 只跑 A 臂
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCHMARK_DIR / "results" / "real-tasks-v2"

# A 臂：现状自由 —— 直接读取真实的 prompts/dev.md（去掉 front matter），不是简化稻草人
def load_a_prompt() -> str:
    """加载真实的 Dev prompt（prompts/dev.md，去掉 front matter）。"""
    dev_md = PROJECT_ROOT / "prompts" / "dev.md"
    content = dev_md.read_text(encoding="utf-8")
    # 去掉 front matter（--- 包裹的部分）
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()
    return content

# 3 个真实任务（从 tasks-v2.md 提取，这里内联方便脚本使用）
TASKS = [
    {
        "id": "task1_prd_feature",
        "name": "带 PRD 的小功能实现",
        "upstream_key_facts": [
            "验收标准 1-5（5 列、筛选约束、文件名格式、loading、10000 条上限）",
            "技术约束（papaparse、exportCsv.ts、不引新依赖）",
        ],
        "prompt": """## PRD：用户管理页面 CSV 导出

### 需求描述
在现有用户管理页面（src/pages/UserManagement/index.tsx）的工具栏增加一个"导出 CSV"按钮，点击后将当前筛选条件下的用户列表导出为 CSV 文件下载。

### 验收标准
1. 导出的 CSV 包含列：ID、用户名、邮箱、注册时间、状态
2. 导出范围受当前页面筛选条件（状态筛选、搜索关键词）约束
3. 导出文件名格式：users_{YYYYMMDD_HHmmss}.csv
4. 导出过程中按钮显示 loading 状态，防止重复点击
5. 单次导出上限 10000 条，超过时提示用户缩小筛选范围

### 技术约束
- 使用项目已有的 csv 库（papaparse，已在 package.json 中）
- 导出逻辑放在 src/pages/UserManagement/exportCsv.ts，不要写在组件里
- 不引入新的依赖

请基于以上 PRD，给出实现方案（关键设计 + 核心代码片段即可，不需要完整可运行代码）。""",
    },
    {
        "id": "task2_bug_fix",
        "name": "带真实报错日志的 bug 修复",
        "upstream_key_facts": [
            "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0",
            "pandas 从 1.5 升到 2.1 后开始报错",
            "输入文件是 Excel 导出的 CSV，可能含中文",
        ],
        # 判分口径（人工判分时参考）：
        # - "pandas 1.5→2.1 升级"是红鲱鱼干扰项，真因是 Excel 导出的 CSV 是 GBK/GB2312 编码
        # - 识别出"升级是干扰项、真因是编码"才算高分
        # - 甩锅给 pandas 升级（如"pandas 2.1 改了默认编码"）算错误
        # - 合理修复：encoding='gbk' / errors='replace' / chardet 自动检测
        "scoring_note": "pandas 升级是红鲱鱼干扰项，真因是 GBK 编码；识别出干扰项才算高分，甩锅升级算错误",
        "prompt": """## 报错日志
Traceback (most recent call last):
  File "/app/scripts/import_data.py", line 47, in <module>
    main()
  File "/app/scripts/import_data.py", line 32, in main
    df = pd.read_csv(input_file, encoding='utf-8')
  File "/usr/local/lib/python3.11/site-packages/pandas/io/parsers/readers.py", line 912, in read_csv
    return _read(filepath_or_buffer, kwds)
  ...
  File "/usr/local/lib/python3.11/encodings/utf_8.py", line 16, in decode
    return codecs.utf_8_decode(input, errors, True)
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0 in position 1234: invalid start byte

## 上下文
- 脚本：scripts/import_data.py，用于从 CSV 导入用户数据到数据库
- 输入文件：由运营同事从 Excel 导出的 CSV，可能包含中文
- 最近变更：上周把 pandas 从 1.5 升到 2.1，之后开始报错
- 期望：脚本能正常导入包含中文的 CSV 文件

请基于以上报错日志和上下文，给出根因分析和修复方案（关键代码片段即可）。""",
    },
    {
        "id": "task3_upstream_handoff",
        "name": "流水线里有上游产出需要摘要传递",
        "upstream_key_facts": [
            "30 分钟倒计时、待支付自动取消、释放库存、站内信通知",
            "技术约束：不用 cron、用延迟队列（Redis ZSET/RabbitMQ TTL）、幂等",
            "验收标准 1-4（30 分钟取消、10 分钟支付不取消、库存恢复+通知、幂等）",
        ],
        "prompt": """## 需求名称：订单超时自动取消

### 背景
用户下单后 30 分钟未支付，订单应自动取消并释放库存。当前系统没有这个机制，导致库存被长期占用。

### 核心需求
1. 订单创建后启动 30 分钟倒计时
2. 倒计时结束时检查订单状态：若仍为"待支付"，则自动取消
3. 取消时释放库存、发送站内信通知用户
4. 若用户在倒计时内完成支付，取消倒计时

### 技术约束（Product 标注）
- 不能用 cron 轮询（延迟不可控）
- 建议用延迟队列（如 Redis ZSET 或 RabbitMQ TTL）
- 取消操作必须幂等（重复触发不能重复扣库存）

### 验收标准
1. 下单后 30 分钟未支付 → 订单状态变为"已取消"
2. 下单后 10 分钟支付 → 订单正常，不取消
3. 取消后库存恢复、用户收到通知
4. 重复触发取消 → 只执行一次

请基于以上 Product 产出，给出技术实现方案（关键设计 + 伪代码即可，不需要完整可运行代码）。""",
    },
]


def load_prompt(arm: str) -> str:
    """加载对应臂的 system prompt。

    三臂共享同一底座（完整 prompts/dev.md），唯一差别 = 追加的交接格式：
      A = 底座 dev.md（无追加格式段，现状自由）
      B = 底座 dev.md + prose 强制字段追加段
      C = 底座 dev.md + 结构化块追加段
    """
    base = load_a_prompt()  # 完整 prompts/dev.md（去掉 front matter）

    if arm == "A":
        return base
    elif arm == "B":
        append_path = BENCHMARK_DIR / "dev-b-prose-v2.md"
    elif arm == "C":
        append_path = BENCHMARK_DIR / "dev-c-schema-v2.md"
    else:
        raise ValueError(f"未知 arm: {arm}")

    if not append_path.exists():
        raise FileNotFoundError(f"追加段文件不存在: {append_path}")

    append_content = append_path.read_text(encoding="utf-8")
    # 去掉追加段文件顶部的说明注释（# 开头的元信息），只保留实际格式段
    # 追加段文件里第一个 "---" 之后是实际内容
    if "---" in append_content:
        append_content = append_content.split("---", 1)[1].strip()

    return base + "\n\n" + append_content


def load_sensenova_config():
    """从 .env 或环境变量加载 SenseNova 配置。"""
    api_key = os.environ.get("SENSENOVA_API_KEY")
    if not api_key:
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("SENSENOVA_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not api_key:
        print("错误：未找到 SENSENOVA_API_KEY。", file=sys.stderr)
        print("请在 .env 或环境变量中设置 SENSENOVA_API_KEY。", file=sys.stderr)
        sys.exit(1)

    return {
        "base_url": os.environ.get("SENSENOVA_BASE_URL", "https://token.sensenova.cn/v1"),
        "api_key": api_key,
        "model": os.environ.get("SENSENOVA_MODEL", "sensenova-6.7-flash-lite"),
    }


def call_llm(system_prompt: str, user_prompt: str, config: dict) -> str:
    """调用 LLM API（OpenAI 兼容格式）。"""
    from openai import OpenAI

    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def run(arms: list, runs: int, delay: int = 2):
    """运行三臂对比。"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config = load_sensenova_config()

    print("=" * 60)
    print("结构化通信 · 真实任务三臂对比 v2")
    print("=" * 60)
    print(f"臂: {', '.join(arms)}")
    print(f"每任务运行次数: {runs}")
    print(f"模型: {config['model']}")
    print(f"总运行次数: {len(arms) * len(TASKS) * runs}")
    print()
    print("注意：不自动判分，只保存原始产出。人工判：")
    print("  ① 上游信息完整性  ② 编造")
    print()

    all_results = []

    for arm in arms:
        print(f"\n{'='*60}")
        print(f"臂 {arm}")
        print(f"{'='*60}")

        system_prompt = load_prompt(arm)
        print(f"已加载 system prompt: {len(system_prompt)} 字符")

        for task in TASKS:
            print(f"\n--- 任务: {task['name']} ({task['id']}) ---")
            print(f"  上游关键事实: {', '.join(task['upstream_key_facts'])}")

            for run in range(1, runs + 1):
                print(f"  运行 {run}/{runs}...", end=" ", flush=True)
                try:
                    output = call_llm(system_prompt, task["prompt"], config)
                    out_file = RESULTS_DIR / f"{task['id']}_{arm}_{run}.md"
                    out_file.write_text(output, encoding="utf-8")

                    print(f"✅ 已保存 ({len(output)} 字符)")
                    all_results.append({
                        "arm": arm,
                        "task_id": task["id"],
                        "task_name": task["name"],
                        "run": run,
                        "output_length": len(output),
                        "output_file": str(out_file),
                        "upstream_key_facts": task["upstream_key_facts"],
                    })
                except Exception as e:
                    print(f"❌ 错误: {e}")
                    all_results.append({
                        "arm": arm,
                        "task_id": task["id"],
                        "task_name": task["name"],
                        "run": run,
                        "error": str(e),
                    })

                if run < runs:
                    time.sleep(delay)

    # 保存汇总
    summary = {
        "arms": arms,
        "runs_per_task": runs,
        "model": config["model"],
        "total_runs": len(arms) * len(TASKS) * runs,
        "note": "不自动判分，只保存原始产出。人工判：① 上游信息完整性 ② 编造",
        "results": all_results,
    }
    summary_file = RESULTS_DIR / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("运行完成")
    print("=" * 60)
    print(f"原始产出目录: {RESULTS_DIR}")
    print(f"汇总文件: {summary_file}")
    print()
    print("请人工判：")
    print("  ① 上游信息完整性（每个任务的 upstream_key_facts 有没有在产出里体现）")
    print("  ② 编造（判断字段没内容时是老实写'无'还是硬编）")


def main():
    parser = argparse.ArgumentParser(description="结构化通信 · 真实任务三臂对比 v2")
    parser.add_argument("--runs", type=int, default=2, help="每个任务运行次数")
    parser.add_argument("--arm", choices=["A", "B", "C", "all"], default="all", help="跑哪个臂")
    parser.add_argument("--delay", type=int, default=2, help="每次调用之间的延迟秒数")
    args = parser.parse_args()

    arms = ["A", "B", "C"] if args.arm == "all" else [args.arm]
    run(arms, args.runs, args.delay)


if __name__ == "__main__":
    main()
