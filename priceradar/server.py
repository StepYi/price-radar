"""本地静态服务器：把日报看板分享给同一局域网里的同事。

只为共享看板而生，不做任何写入。默认绑定 0.0.0.0（局域网可见），
加 --local 才只绑定本机 127.0.0.1。
"""

from __future__ import annotations

import functools
import http.server
import socket
import socketserver
import threading
from pathlib import Path


def lan_ip() -> str:
    """拿到本机在局域网里的 IP。

    连一个外网地址但**不真的发包**（UDP connect 只做路由选择），
    这样能避开虚拟网卡 / VPN 拿到错误的地址。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """加 no-cache 头，避免同事看到的是浏览器缓存的旧日报。"""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        # 默认日志太吵，只留错误
        if args and str(args[1]).startswith(("4", "5")):
            print(f"  [{self.address_string()}] {fmt % args}", flush=True)


class ReusableServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(
    directory: Path,
    *,
    port: int = 8080,
    bind_all: bool = True,
    open_browser: bool = False,
    log=print,
) -> None:
    directory = Path(directory)
    if not directory.exists():
        raise SystemExit(f"目录不存在：{directory}（先运行 python -m priceradar run）")

    handler = functools.partial(QuietHandler, directory=str(directory))

    httpd = None
    for candidate in range(port, port + 20):
        try:
            httpd = ReusableServer(("0.0.0.0" if bind_all else "127.0.0.1", candidate), handler)
            port = candidate
            break
        except OSError:
            log(f"  端口 {candidate} 被占用，试下一个…")
    if httpd is None:
        raise SystemExit(f"端口 {port}–{port + 19} 全部被占用，请用 --port 指定别的端口。")

    local = f"http://127.0.0.1:{port}/"
    log("")
    log("=" * 66)
    log("  PriceRadar 看板已在运行（Ctrl+C 停止）")
    log("=" * 66)
    log(f"  本机打开      {local}")
    if bind_all:
        ip = lan_ip()
        log(f"  分享给同事    http://{ip}:{port}/")
        log("")
        log("  同事需要在同一个局域网（同一个 WiFi / 办公网）里，")
        log("  用上面的地址直接在浏览器打开即可，不需要装任何东西。")
        log("")
        log("  如果同事打不开，多半是 Windows 防火墙拦了。用【管理员】PowerShell 执行：")
        log(
            f'    netsh advfirewall firewall add rule name="PriceRadar {port}" '
            f"dir=in action=allow protocol=TCP localport={port}"
        )
        log("")
        log("  想让不在同一个网络的人也能看 → 见 README「让别人也能看」一节的")
        log("  GitHub Pages / Cloudflare Pages 方案（免费，得到一个公网网址）。")
    log("=" * 66)
    log("")

    if open_browser:
        threading.Timer(0.6, lambda: __import__("webbrowser").open(local)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("\n已停止。")
    finally:
        httpd.server_close()
