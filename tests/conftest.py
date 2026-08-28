"""pytest 公共配置：按文件路径加载 state-manager.py（文件名带连字符，不能常规 import），
并隔离其状态文件路径到临时目录，避免污染真实状态。"""

import importlib.util
import os

import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "scripts")


def _load_state_manager():
    path = os.path.join(SCRIPTS_DIR, "state-manager.py")
    spec = importlib.util.spec_from_file_location("state_manager", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 模块级加载一次，供所有测试共享同一模块实例（路径经 sm_isolated fixture 隔离）
sm = _load_state_manager()


@pytest.fixture()
def sm_isolated(tmp_path, monkeypatch):
    """把 state-manager 的 STATE/BACKUP/LOCK 文件路径指向临时目录。"""
    state = tmp_path / "state.json"
    monkeypatch.setattr(sm, "STATE_FILE", str(state))
    monkeypatch.setattr(sm, "BACKUP_FILE", str(state) + ".bak")
    monkeypatch.setattr(sm, "LOCK_FILE", str(state) + ".lock")
    return sm
