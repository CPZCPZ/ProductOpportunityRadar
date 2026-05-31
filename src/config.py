"""配置加载：从环境变量(.env / GitHub Secrets) 与 yml 文件读取设置。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# 项目根目录（本文件位于 src/ 下）
ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_yaml(name: str) -> dict[str, Any]:
    path = ROOT / name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


class Config:
    """集中管理所有运行期配置。"""

    def __init__(self) -> None:
        # ---- 信源 / 关键词 / 推广映射 ----
        self.sources: dict[str, Any] = _load_yaml("sources.yml")
        self.keywords: dict[str, Any] = _load_yaml("keywords.yml")
        self.promotion: dict[str, Any] = _load_yaml("promotion.yml")

        # ---- 邮件 ----
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465") or "465")
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.mail_to = [
            addr.strip()
            for addr in os.getenv("MAIL_TO", "").split(",")
            if addr.strip()
        ]
        self.mail_from_name = os.getenv("MAIL_FROM_NAME", "产品机会雷达")
        self.attach_file = _bool(os.getenv("ATTACH_FILE"), False)
        self.attach_format = os.getenv("ATTACH_FORMAT", "html").strip().lower()

        # ---- Reddit ----
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
        self.reddit_user_agent = os.getenv(
            "REDDIT_USER_AGENT",
            "python:product-opportunity-radar:v1.0",
        ).strip()

        # ---- Product Hunt ----
        self.producthunt_token = os.getenv("PRODUCTHUNT_TOKEN", "").strip()

        # ---- 可选 ----
        self.enable_google_trends = _bool(os.getenv("ENABLE_GOOGLE_TRENDS"), False)

        # ---- 通用参数 ----
        self.top_n_overseas = int(self.sources.get("top_n_overseas", 12))
        self.top_n_domestic = int(self.sources.get("top_n_domestic", 8))
        self.recent_hours = int(self.sources.get("recent_hours", 72))

    @property
    def collectors(self) -> dict[str, Any]:
        return self.sources.get("collectors", {})

    def keyword_list(self) -> list[str]:
        """把 keywords.yml 各分组拍平成一个列表（全部小写）。"""
        out: list[str] = []
        for group in self.keywords.values():
            if isinstance(group, list):
                out.extend(str(k).lower() for k in group)
        return out

    def smtp_ready(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_pass and self.mail_to)

    def reddit_ready(self) -> bool:
        return bool(self.reddit_client_id and self.reddit_client_secret)

    def producthunt_ready(self) -> bool:
        return bool(self.producthunt_token)
