"""可选的邮件推送（默认关闭）。

启用方式（PowerShell 示例）：

    $env:PRICERADAR_SMTP_HOST = "smtp.qq.com"
    $env:PRICERADAR_SMTP_PORT = "465"
    $env:PRICERADAR_SMTP_USER = "you@qq.com"
    $env:PRICERADAR_SMTP_PASS = "授权码"      # 注意：不是登录密码
    $env:PRICERADAR_MAIL_TO   = "you@qq.com"
    python -m priceradar run --email

没有配置时只会打印一行提示，不影响日报生成。
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from .render import render_markdown


def _cfg() -> dict:
    return {
        "host": os.environ.get("PRICERADAR_SMTP_HOST", "").strip(),
        "port": int(os.environ.get("PRICERADAR_SMTP_PORT", "465") or 465),
        "user": os.environ.get("PRICERADAR_SMTP_USER", "").strip(),
        "password": os.environ.get("PRICERADAR_SMTP_PASS", "").strip(),
        "to": [
            x.strip()
            for x in os.environ.get("PRICERADAR_MAIL_TO", "").replace(";", ",").split(",")
            if x.strip()
        ],
        "sender": os.environ.get("PRICERADAR_MAIL_FROM", "").strip(),
    }


def send_digest(digest: dict, out_dir: Path) -> tuple[bool, str]:
    cfg = _cfg()
    missing = [k for k in ("host", "user", "password") if not cfg[k]]
    if missing or not cfg["to"]:
        return False, (
            "未配置邮件环境变量（缺少 "
            + "、".join(missing + ([] if cfg["to"] else ["PRICERADAR_MAIL_TO"]))
            + "），已跳过。"
        )

    date = digest["date"]
    msg = EmailMessage()
    msg["Subject"] = f"价格研究日报 · {date}（{digest['stats']['pushed']} 篇）"
    msg["From"] = cfg["sender"] or cfg["user"]
    msg["To"] = ", ".join(cfg["to"])
    msg.set_content(render_markdown(digest))

    html_path = out_dir / f"{date}.html"
    if html_path.exists():
        msg.add_alternative(html_path.read_text(encoding="utf-8"), subtype="html")

    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(
                cfg["host"], cfg["port"], context=ssl.create_default_context(), timeout=45
            ) as server:
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=45) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
    except Exception as exc:
        return False, f"发送失败：{exc}"
    return True, "、".join(cfg["to"])
