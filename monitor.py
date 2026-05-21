#!/usr/bin/env python3
"""RevHive metrics — shared data layer used by dashboard and CLI monitor."""

import json
import time
from datetime import datetime

import requests

GITHUB_REPO = "Jansen003/RevHive"
PYPI_PACKAGE = "revhive-ai"
METRICS_FILE = "/Users/souljian/code/opc/opc-agents/metrics.json"

_cache: dict[str, object] = {"last_update": 0.0}
_CACHE_TTL = 300  # 5 minutes


def _is_cache_fresh() -> bool:
    return time.time() - _cache["last_update"] < _CACHE_TTL


def get_github_stars(repo: str = GITHUB_REPO) -> int | None:
    if "github_stars" in _cache and _is_cache_fresh():
        return _cache["github_stars"]  # type: ignore[return-value]
    url = f"https://api.github.com/repos/{repo}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        stars = resp.json()["stargazers_count"]
        _cache["github_stars"] = stars
        _cache["last_update"] = time.time()
        return stars
    except Exception as e:
        print(f"Error fetching GitHub stars: {e}")
        return _cache.get("github_stars")  # type: ignore[return-value]


def get_github_forks(repo: str = GITHUB_REPO) -> int | None:
    if "github_forks" in _cache and _is_cache_fresh():
        return _cache["github_forks"]  # type: ignore[return-value]
    url = f"https://api.github.com/repos/{repo}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        forks = resp.json()["forks_count"]
        _cache["github_forks"] = forks
        _cache["last_update"] = time.time()
        return forks
    except Exception as e:
        print(f"Error fetching GitHub forks: {e}")
        return _cache.get("github_forks")  # type: ignore[return-value]


def get_pypi_downloads(package: str = PYPI_PACKAGE) -> dict[str, int | None]:
    if "pypi_downloads" in _cache and _is_cache_fresh():
        return _cache["pypi_downloads"]  # type: ignore[return-value]
    url = f"https://pypistats.org/api/packages/{package}/overall"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        today = datetime.now().strftime("%Y-%m-%d")
        today_data = next(
            (d for d in data["data"] if d["category"] == "without_mirrors" and d["date"] == today),
            None,
        )
        result: dict[str, int | None] = {
            "today": today_data["downloads"] if today_data else 0,
            "total": sum(d["downloads"] for d in data["data"] if d["category"] == "without_mirrors"),
        }
        _cache["pypi_downloads"] = result
        _cache["last_update"] = time.time()
        return result
    except Exception as e:
        print(f"Error fetching PyPI downloads: {e}")
        cached = _cache.get("pypi_downloads")
        return cached if isinstance(cached, dict) else {"today": None, "total": None}


def get_cache_timestamp() -> float:
    return _cache["last_update"]


def save_metrics(metrics: dict, filename: str = METRICS_FILE) -> None:
    with open(filename, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {filename}")


def load_metrics(filename: str = METRICS_FILE) -> dict:
    try:
        with open(filename) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def send_notification(message: str) -> None:
    """Send notification (stdout for now; extend with Slack/email/webhook)."""
    print(f"\n🔔 通知: {message}")


def main() -> None:
    """CLI entry point — fetch, print, save, and check milestones."""
    print("=" * 50)
    print("RevHive 数据监控")
    print("=" * 50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    stars = get_github_stars()
    forks = get_github_forks()
    downloads = get_pypi_downloads()

    print("📊 当前指标:")
    print(f"  GitHub Stars: {stars}")
    print(f"  GitHub Forks: {forks}")
    print(f"  PyPI Downloads (today): {downloads['today']}")
    print()

    metrics: dict = {
        "timestamp": datetime.now().isoformat(),
        "github_stars": stars,
        "github_forks": forks,
        "pypi_downloads": downloads["total"],
    }
    save_metrics(metrics)

    if stars and stars >= 50:
        send_notification(f"🎉 GitHub Stars 达到 {stars}！")
    if stars and stars >= 100:
        send_notification(f"🚀 GitHub Stars 达到 {stars}！")
    if downloads.get("today") and downloads["today"] >= 20:
        send_notification(f"📈 PyPI 下载量达到 {downloads['today']}！")

    print("=" * 50)
    print("监控完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
