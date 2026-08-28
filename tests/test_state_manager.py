"""state_manager.py 单元测试：状态读写、备份恢复、文件锁、检查点与任务归档。"""

import json
import os
import time

import pytest

# state-manager.py 文件名带连字符无法常规 import，模块实例由 conftest 加载后注入
import conftest

sm = conftest.sm


# ---------- _try_load_json ----------

class TestTryLoadJson:
    def test_loads_valid_dict(self, sm_isolated, tmp_path):
        f = tmp_path / "ok.json"
        f.write_text('{"a": 1}', encoding="utf-8")
        assert sm._try_load_json(str(f)) == {"a": 1}

    def test_returns_none_for_corrupt_json(self, sm_isolated, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not json", encoding="utf-8")
        assert sm._try_load_json(str(f)) is None

    def test_returns_none_for_missing_file(self, sm_isolated, tmp_path):
        assert sm._try_load_json(str(tmp_path / "missing.json")) is None

    def test_returns_none_for_non_dict_json(self, sm_isolated, tmp_path):
        f = tmp_path / "list.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        assert sm._try_load_json(str(f)) is None


# ---------- load / save 基础 ----------

class TestLoadSave:
    def test_load_returns_empty_state_when_nothing_exists(self, sm_isolated):
        state = sm.load()
        assert state == {"events": [], "current_task": None, "history": []}

    def test_save_then_load_roundtrip(self, sm_isolated):
        sm.save({"events": [], "current_task": {"name": "T"}, "history": []})
        loaded = sm.load()
        assert loaded["current_task"]["name"] == "T"

    def test_save_creates_backup_on_second_write(self, sm_isolated):
        sm.save({"events": [], "current_task": {"name": "v1"}, "history": []})
        sm.save({"events": [], "current_task": {"name": "v2"}, "history": []})
        assert os.path.exists(sm.BACKUP_FILE)
        backup = sm._try_load_json(sm.BACKUP_FILE)
        assert backup["current_task"]["name"] == "v1"

    def test_save_returns_deepcopy_not_mutated_by_caller(self, sm_isolated):
        state = sm.load()
        state["events"].append({"type": "x", "data": "y", "timestamp": "t"})
        # 未 save 前重新 load 不应看到调用方修改
        assert sm.load()["events"] == []


# ---------- 备份恢复 ----------

class TestBackupRecovery:
    def test_load_recovers_from_backup_when_main_corrupt(self, sm_isolated):
        sm.save({"events": [], "current_task": {"name": "good"}, "history": []})
        # 二次写入生成备份（备份在第二次 save 时产生）
        sm.save({"events": [], "current_task": {"name": "good"}, "history": []})
        # 损坏主文件
        with open(sm.STATE_FILE, "w", encoding="utf-8") as f:
            f.write("{corrupt")
        state = sm.load()
        assert state["current_task"]["name"] == "good"
        # 恢复后主文件应被写回为有效 JSON
        assert sm._try_load_json(sm.STATE_FILE)["current_task"]["name"] == "good"

    def test_load_resets_when_main_corrupt_and_no_backup(self, sm_isolated):
        with open(sm.STATE_FILE, "w", encoding="utf-8") as f:
            f.write("{corrupt")
        state = sm.load()
        assert state["events"] == []

    def test_load_resets_when_both_corrupt(self, sm_isolated):
        sm.save({"events": [], "current_task": {"name": "g"}, "history": []})
        with open(sm.STATE_FILE, "w", encoding="utf-8") as f:
            f.write("{corrupt")
        with open(sm.BACKUP_FILE, "w", encoding="utf-8") as f:
            f.write("{also corrupt")
        state = sm.load()
        assert state == {"events": [], "current_task": None, "history": []}


# ---------- log_event ----------

class TestLogEvent:
    def test_log_event_appends_with_timestamp(self, sm_isolated):
        sm.log_event("info", "hello")
        state = sm.load()
        assert len(state["events"]) == 1
        ev = state["events"][0]
        assert ev["type"] == "info"
        assert ev["data"] == "hello"
        assert "timestamp" in ev and ev["timestamp"]

    def test_log_event_accumulates_multiple(self, sm_isolated):
        sm.log_event("a", "1")
        sm.log_event("b", "2")
        state = sm.load()
        assert [e["type"] for e in state["events"]] == ["a", "b"]


# ---------- 检查点与阶段 ----------

class TestCheckpoint:
    def test_save_checkpoint_creates_current_task(self, sm_isolated, capsys):
        sm.save_checkpoint("login", "design", "50%")
        state = sm.load()
        task = state["current_task"]
        assert task["name"] == "login"
        assert task["current_stage"] == "design"
        assert task["progress"] == "50%"
        assert "updated_at" in task
        out = capsys.readouterr().out
        assert "login" in out

    def test_complete_stage_appends_to_task(self, sm_isolated):
        sm.save_checkpoint("login", "design", "50%")
        sm.complete_stage("design")
        task = sm.load()["current_task"]
        assert "design" in task["stages_completed"]

    def test_complete_stage_deduplicates(self, sm_isolated):
        sm.save_checkpoint("login", "design", "50%")
        sm.complete_stage("design")
        sm.complete_stage("design")
        task = sm.load()["current_task"]
        assert task["stages_completed"].count("design") == 1

    def test_complete_stage_with_artifact(self, sm_isolated):
        sm.save_checkpoint("login", "design", "50%")
        sm.complete_stage("design", "work/design.png")
        task = sm.load()["current_task"]
        assert task["artifacts"]["design"] == "work/design.png"

    def test_complete_stage_without_task_does_nothing(self, sm_isolated, capsys):
        sm.complete_stage("design")
        out = capsys.readouterr().out
        assert "没有活跃任务" in out
        assert sm.load()["current_task"] is None


# ---------- resume / clear ----------

class TestResumeClear:
    def test_get_resume_info_with_task(self, sm_isolated, capsys):
        sm.save_checkpoint("login", "dev", "30%")
        sm.complete_stage("design")
        sm.get_resume_info()
        out = capsys.readouterr().out
        assert "needs_resume: true" in out
        assert "login" in out
        assert "design" in out

    def test_get_resume_info_no_task(self, sm_isolated, capsys):
        sm.get_resume_info()
        out = capsys.readouterr().out
        assert "needs_resume: false" in out

    def test_clear_task_archives_to_history(self, sm_isolated, capsys):
        sm.save_checkpoint("login", "done", "100%")
        sm.clear_task()
        state = sm.load()
        assert state.get("current_task") is None
        assert len(state["history"]) == 1
        assert state["history"][0]["task"]["name"] == "login"

    def test_clear_without_task_does_nothing(self, sm_isolated, capsys):
        sm.clear_task()
        out = capsys.readouterr().out
        assert "没有活跃任务" in out
        assert sm.load()["history"] == []


# ---------- 文件锁 ----------

class TestFileLock:
    def test_lock_acquired_and_released(self, sm_isolated):
        with sm.file_lock():
            assert os.path.exists(sm.LOCK_FILE)
        assert not os.path.exists(sm.LOCK_FILE)

    def test_lock_blocks_until_released(self, sm_isolated):
        acquired = []

        def hold_lock():
            with sm.file_lock():
                acquired.append(True)
                time.sleep(0.3)

        import threading

        t = threading.Thread(target=hold_lock)
        t.start()
        time.sleep(0.1)  # 确保持锁线程已进入临界区
        # 主线程尝试获取，应等到持锁线程释放后才成功
        with sm.file_lock():
            pass
        t.join()
        assert acquired == [True]

    def test_stale_lock_removed_after_30s(self, sm_isolated):
        # 模拟一个 40 秒前的僵尸锁
        os.makedirs(os.path.dirname(sm.LOCK_FILE), exist_ok=True)
        with open(sm.LOCK_FILE, "w", encoding="utf-8") as f:
            f.write("12345")
        old = time.time() - 40
        os.utime(sm.LOCK_FILE, (old, old))
        with sm.file_lock():
            assert os.path.exists(sm.LOCK_FILE)
        assert not os.path.exists(sm.LOCK_FILE)

    def test_fresh_lock_times_out(self, sm_isolated, monkeypatch):
        # 制造一个刚创建的锁文件，等待应超时抛 TimeoutError
        os.makedirs(os.path.dirname(sm.LOCK_FILE), exist_ok=True)
        with open(sm.LOCK_FILE, "w", encoding="utf-8") as f:
            f.write("12345")
        # 缩短等待，避免测试跑 10 秒（file_lock 内 import time 用全局 time 模块）
        monkeypatch.setattr(time, "sleep", lambda s: None)
        with pytest.raises(TimeoutError):
            with sm.file_lock():
                pass


# ---------- 主入口 ----------

class TestMain:
    def test_main_no_args_prints_usage(self, sm_isolated, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["state-manager.py"])
        with pytest.raises(SystemExit) as exc:
            sm.main()
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "用法" in out

    def test_main_status(self, sm_isolated, capsys, monkeypatch):
        sm.save_checkpoint("login", "dev", "50%")
        monkeypatch.setattr("sys.argv", ["state-manager.py", "status"])
        sm.main()
        out = capsys.readouterr().out
        assert "活跃任务: login" in out

    def test_main_checkpoint_via_cli(self, sm_isolated, monkeypatch):
        monkeypatch.setattr("sys.argv", ["state-manager.py", "checkpoint", "pay", "design", "20%", "work/x.png"])
        sm.main()
        task = sm.load()["current_task"]
        assert task["name"] == "pay"
        assert task["artifact"] == "work/x.png"

    def test_main_unknown_command(self, sm_isolated, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["state-manager.py", "nonexistent"])
        with pytest.raises(SystemExit) as exc:
            sm.main()
        assert exc.value.code == 1
