#!/usr/bin/env python3
"""OPC 状态管理器 — 任务进度跟踪与中断恢复"""

import json
import os
import sys
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


def ensure_dir():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)


def load():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"events": [], "current_task": None, "history": []}


def save(state):
    ensure_dir()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def log_event(event_type, data):
    state = load()
    state.setdefault("events", []).append({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })
    save(state)


def save_checkpoint(task_name, stage, progress, artifact_path=None):
    state = load()
    state["current_task"] = {
        "name": task_name,
        "current_stage": stage,
        "progress": progress,
        "artifact": artifact_path,
        "updated_at": datetime.now().isoformat()
    }
    save(state)
    print(f"检查点已保存: {task_name} / {stage} / {progress}")


def complete_stage(stage_name, artifact_path=None):
    state = load()
    task = state.get("current_task")
    if not task:
        print("没有活跃任务")
        return

    completed = task.setdefault("stages_completed", [])
    if stage_name not in completed:
        completed.append(stage_name)

    if artifact_path:
        task.setdefault("artifacts", {})[stage_name] = artifact_path

    task["updated_at"] = datetime.now().isoformat()
    save(state)
    print(f"阶段完成: {stage_name}")


def get_resume_info():
    state = load()
    task = state.get("current_task")
    if task:
        completed = task.get("stages_completed", [])
        print(f"任务: {task['name']}")
        print(f"当前阶段: {task['current_stage']}")
        print(f"进度: {task['progress']}")
        print(f"已完成阶段: {', '.join(completed) if completed else '无'}")
        if task.get("artifact"):
            print(f"产出文件: {task['artifact']}")
        print("needs_resume: true")
    else:
        print("没有未完成的任务")
        print("needs_resume: false")


def clear_task():
    state = load()
    task = state.pop("current_task", None)
    if task:
        state.setdefault("history", []).append({
            "task": task,
            "completed_at": datetime.now().isoformat()
        })
        save(state)
        print(f"任务已归档: {task['name']}")
    else:
        print("没有活跃任务")


def show_status():
    state = load()
    events = state.get("events", [])
    task = state.get("current_task")
    history = state.get("history", [])

    print(f"总事件数: {len(events)}")
    print(f"历史任务: {len(history)}")

    if task:
        print(f"活跃任务: {task['name']}")
        print(f"  当前阶段: {task['current_stage']}")
        print(f"  进度: {task['progress']}")
        completed = task.get("stages_completed", [])
        if completed:
            print(f"  已完成: {', '.join(completed)}")
    else:
        print("活跃任务: 无")

    if events:
        last = events[-1]
        print(f"最近事件: {last['type']} @ {last['timestamp']}")


def main():
    if len(sys.argv) < 2:
        print("OPC 状态管理器")
        print()
        print("用法:")
        print("  state-manager.py status              显示状态")
        print("  state-manager.py resume                显示恢复信息")
        print("  state-manager.py checkpoint <任务> <阶段> <进度> [文件]")
        print("  state-manager.py complete <阶段> [文件]")
        print("  state-manager.py clear                 归档当前任务")
        print("  state-manager.py log <类型> <数据>     记录事件")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        show_status()
    elif cmd == "resume":
        get_resume_info()
    elif cmd == "checkpoint" and len(sys.argv) >= 5:
        artifact = sys.argv[5] if len(sys.argv) > 5 else None
        save_checkpoint(sys.argv[2], sys.argv[3], sys.argv[4], artifact)
    elif cmd == "complete" and len(sys.argv) >= 3:
        artifact = sys.argv[3] if len(sys.argv) > 3 else None
        complete_stage(sys.argv[2], artifact)
    elif cmd == "clear":
        clear_task()
    elif cmd == "log" and len(sys.argv) >= 4:
        log_event(sys.argv[2], sys.argv[3])
        print(f"已记录: {sys.argv[2]}")
    else:
        print("参数错误，运行不带参数查看帮助")
        sys.exit(1)


if __name__ == "__main__":
    main()
