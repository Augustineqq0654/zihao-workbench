#!/usr/bin/env python3
"""
Zihao 工作台启动脚本
- 启动本地 HTTP 服务器 (支持静态文件 + API)
- 提供 /api/refresh-hot 接口（运行爬虫并返回最新数据）
- 自动打开浏览器
"""

import http.server
import json
import os
import sys
import webbrowser
import threading
import socket
import subprocess
import time
import traceback
from urllib.parse import urlparse

# ============ 配置 ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKBENCH_DIR = SCRIPT_DIR
DATA_DIR = os.path.join(WORKBENCH_DIR, "data")
CRAWLER_SCRIPT = os.path.join(WORKBENCH_DIR, "scripts", "douyin_crawler.py")
PORT = 8767
PYTHON_EXE = sys.executable


def kill_port_processes(port):
    """杀掉占用指定端口的所有旧进程（Windows）

    解决问题：直接关闭终端窗口时 Python 进程不会退出，变成僵尸进程
    霸占端口，导致下次启动只能换端口。启动前自动清理即可固定端口。
    """
    if sys.platform != "win32":
        return
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, encoding="gbk", errors="ignore",
        )
        pids = set()
        my_pid = os.getpid()
        lines = (result.stdout or "").splitlines()
        for line in lines:
            # 匹配形如 "  TCP    0.0.0.0:8767   ...  LISTENING   30004"
            if f":{port}" in line and "LISTENING" in line.upper():
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) != my_pid:
                        pids.add(pid)

        for pid in pids:
            subprocess.run(
                ["taskkill", "/F", "/PID", pid],
                capture_output=True, text=True, encoding="gbk", errors="ignore",
            )
            print(f"[clean] killed zombie PID {pid} on port {port}", flush=True)

        if pids:
            time.sleep(0.5)  # 等端口释放
            print(f"[clean] port {port} freed, {len(pids)} process(es) removed", flush=True)
    except Exception as e:
        print(f"[warn] port cleanup skipped: {e}", flush=True)

# MIME 类型映射
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class WorkbenchHandler(http.server.BaseHTTPRequestHandler):
    """自定义请求处理器：静态文件 + API"""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            # API: 刷新热榜
            if path == "/api/refresh-hot":
                return self._handle_refresh_hot()

            # 默认路由到 index.html
            if path == "/":
                path = "/index.html"

            # 构建本地文件路径
            # 去掉开头的 /，转为相对路径
            relative = path.lstrip("/")
            # 安全检查：防止目录遍历攻击
            relative = os.path.normpath(relative)
            if relative.startswith(".."):
                return self._send_error(403, "Forbidden")

            filepath = os.path.join(WORKBENCH_DIR, relative)

            if not os.path.isfile(filepath):
                # 404 时也返回 index.html（SPA 回退）
                filepath = os.path.join(WORKBENCH_DIR, "index.html")

            self._serve_file(filepath)

        except Exception:
            traceback.print_exc()
            self._send_error(500, "Internal Server Error")

    def _serve_file(self, filepath):
        """读取并发送文件"""
        ext = os.path.splitext(filepath)[1].lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")

        with open(filepath, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def _send_error(self, code, message):
        """发送错误响应"""
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data, code=200):
        """发送 JSON 响应"""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_refresh_hot(self):
        """运行爬虫脚本，返回最新数据"""
        try:
            result = subprocess.run(
                [PYTHON_EXE, CRAWLER_SCRIPT],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="gbk", errors="ignore",
            )
            print(result.stdout.strip()[-200:] if result.stdout else "(no stdout)", flush=True)

            hot_file = os.path.join(DATA_DIR, "hot_videos.json")
            if os.path.exists(hot_file):
                with open(hot_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._send_json(data)
            else:
                return self._send_error(500, "no data file generated")
        except Exception as e:
            traceback.print_exc()
            return self._send_error(500, str(e))

    def log_message(self, format, *args):
        msg = format % args
        print(f"  {msg}", flush=True)


def get_lan_ip():
    """获取局域网 IPv4 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def check_data():
    """检查热榜数据是否需要更新（文件不存在或不是今天的数据就重新爬取）"""
    from datetime import date as _date
    hot_file = os.path.join(DATA_DIR, "hot_videos.json")

    need_crawl = False
    if not os.path.exists(hot_file):
        print("[init] first run, crawling...", flush=True)
        need_crawl = True
    else:
        try:
            with open(hot_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            file_date = data.get("date", "")
            today = _date.today().isoformat()
            if file_date != today:
                print(f"[update] data is {file_date}, today is {today}, refreshing...", flush=True)
                need_crawl = True
            else:
                print(f"[ok] data is up-to-date ({file_date})", flush=True)
        except Exception:
            print("[warn] failed to read data file, re-crawling...", flush=True)
            need_crawl = True

    if need_crawl:
        subprocess.run([PYTHON_EXE, CRAWLER_SCRIPT], encoding="gbk", errors="ignore")


def main():
    print("=" * 55, flush=True)
    print("   Zihao Workbench - starting...", flush=True)
    print("=" * 55, flush=True)

    # 启动前清理占用端口的僵尸进程，确保端口可固定复用
    kill_port_processes(PORT)

    check_data()

    # 使用 ThreadingHTTPServer 支持并发
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), WorkbenchHandler)
    server.daemon_threads = True

    # 延迟打开浏览器
    def _open():
        time.sleep(1.5)
        url = f"http://127.0.0.1:{PORT}"
        print(f"[ready] opening {url}", flush=True)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()

    lan_ip = get_lan_ip()
    print(f"[ready] local: http://127.0.0.1:{PORT}", flush=True)
    if lan_ip:
        print(f"[mobile] 手机访问: http://{lan_ip}:{PORT}", flush=True)
    print("[tip] Ctrl+C to stop", flush=True)
    print(flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[stop] server closed", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
