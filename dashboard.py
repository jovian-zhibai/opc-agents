#!/usr/bin/env python3
"""RevHive metrics dashboard — HTTP server rendering a live metrics page."""

from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

from monitor import get_github_stars, get_github_forks, get_pypi_downloads, get_cache_timestamp

GITHUB_REPO = "Jansen003/RevHive"
PYPI_PACKAGE = "revhive-ai"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>RevHive 监控面板</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .card h2 {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 16px;
        }
        .card .value {
            font-size: 48px;
            font-weight: bold;
            color: #333;
        }
        .card .label {
            color: #999;
            font-size: 14px;
            margin-top: 10px;
        }
        .status {
            text-align: center;
            margin-top: 30px;
            color: #666;
        }
        .refresh-btn {
            display: block;
            margin: 20px auto;
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .refresh-btn:hover {
            background: #0056b3;
        }
        .debug {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 10px;
            margin-top: 20px;
            font-family: monospace;
            font-size: 12px;
        }
    </style>
    <script>
        function refreshData() {
            location.reload();
        }
        setTimeout(refreshData, 300000);
    </script>
</head>
<body>
    <div class="container">
        <h1>📊 RevHive 监控面板</h1>

        <div class="cards">
            <div class="card">
                <h2>⭐ GitHub Stars</h2>
                <div class="value">__STARS__</div>
                <div class="label">用户认可度</div>
            </div>

            <div class="card">
                <h2>🍴 GitHub Forks</h2>
                <div class="value">__FORKS__</div>
                <div class="label">用户参与度</div>
            </div>

            <div class="card">
                <h2>📦 PyPI 今日下载</h2>
                <div class="value">__DOWNLOADS_TODAY__</div>
                <div class="label">今日下载量</div>
            </div>

            <div class="card">
                <h2>📦 PyPI 总下载量</h2>
                <div class="value">__DOWNLOADS_TOTAL__</div>
                <div class="label">历史总下载量</div>
            </div>
        </div>

        <div class="status">
            <p>最后更新: __TIMESTAMP__</p>
            <button class="refresh-btn" onclick="refreshData()">刷新数据</button>
        </div>

        <div class="debug">
            <strong>调试信息:</strong><br>
            GitHub Stars 原始值: __DEBUG_STARS__<br>
            GitHub Forks 原始值: __DEBUG_FORKS__<br>
            PyPI 今日下载原始值: __DEBUG_DOWNLOADS_TODAY__<br>
            PyPI 总下载原始值: __DEBUG_DOWNLOADS_TOTAL__<br>
            今日日期: __DEBUG_TODAY__<br>
            缓存状态: __DEBUG_CACHE__
        </div>
    </div>
</body>
</html>"""


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            stars = get_github_stars(GITHUB_REPO)
            forks = get_github_forks(GITHUB_REPO)
            downloads = get_pypi_downloads(PYPI_PACKAGE)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            today = datetime.now().strftime("%Y-%m-%d")

            html = HTML_TEMPLATE
            html = html.replace("__STARS__", str(stars) if stars is not None else "N/A")
            html = html.replace("__FORKS__", str(forks) if forks is not None else "N/A")
            html = html.replace("__DOWNLOADS_TODAY__", str(downloads["today"]) if downloads["today"] is not None else "N/A")
            html = html.replace("__DOWNLOADS_TOTAL__", str(downloads["total"]) if downloads["total"] is not None else "N/A")
            html = html.replace("__TIMESTAMP__", timestamp)

            html = html.replace("__DEBUG_STARS__", str(stars))
            html = html.replace("__DEBUG_FORKS__", str(forks))
            html = html.replace("__DEBUG_DOWNLOADS_TODAY__", str(downloads["today"]))
            html = html.replace("__DEBUG_DOWNLOADS_TOTAL__", str(downloads["total"]))
            html = html.replace("__DEBUG_TODAY__", today)
            html = html.replace("__DEBUG_CACHE__", f"Last update: {get_cache_timestamp()}")

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


def run_server(port: int = 5000) -> None:
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardHandler)
    print("=" * 50)
    print("RevHive 监控网站")
    print("=" * 50)
    print(f"访问: http://localhost:{port}")
    print("=" * 50)
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
