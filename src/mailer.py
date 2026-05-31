"""SMTP 发送日报邮件。

默认发送 HTML 正文（手机邮件客户端原生渲染，点开即看）。
当 config.attach_file=True 时，额外附带一份日报文件（html/md），便于归档。
"""

from __future__ import annotations

import logging
import smtplib
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from .config import Config

logger = logging.getLogger(__name__)


def _html_to_markdown_like(html: str) -> str:
    """非常轻量的兜底：附件用 md 时给一个纯文本版（避免再引依赖）。"""
    import re

    text = re.sub(r"(?is)<br\s*/?>", "\n", html)
    text = re.sub(r"(?is)</(p|div|li|h[1-6])>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def send_email(html: str, config: Config, subject: str) -> None:
    if not config.smtp_ready():
        raise RuntimeError(
            "SMTP 配置不完整：请在 .env / Secrets 设置 SMTP_HOST/USER/PASS 与 MAIL_TO"
        )

    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(config.mail_from_name, "utf-8")), config.smtp_user))
    msg["To"] = ", ".join(config.mail_to)

    # 正文（HTML）
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(_html_to_markdown_like(html), "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    # 可选附件
    if config.attach_file:
        if config.attach_format == "md":
            content = _html_to_markdown_like(html).encode("utf-8")
            filename = "radar.md"
            subtype = "markdown"
        else:
            content = html.encode("utf-8")
            filename = "radar.html"
            subtype = "html"
        part = MIMEApplication(content, _subtype=subtype)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    _deliver(msg, config)
    logger.info("邮件已发送给：%s", ", ".join(config.mail_to))


def _deliver(msg: MIMEMultipart, config: Config) -> None:
    if config.smtp_port == 465:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=30) as server:
            server.login(config.smtp_user, config.smtp_pass)
            server.sendmail(config.smtp_user, config.mail_to, msg.as_string())
    else:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(config.smtp_user, config.smtp_pass)
            server.sendmail(config.smtp_user, config.mail_to, msg.as_string())
