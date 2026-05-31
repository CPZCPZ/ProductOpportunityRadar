"""采集器基类：统一容错、HTTP 会话与合规 User-Agent。"""

from __future__ import annotations

import logging
from typing import Any

import requests

from ..models import Signal

logger = logging.getLogger(__name__)

# 合规的默认 UA：标识工具用途，便于被采集方识别。
DEFAULT_UA = "ProductOpportunityRadar/1.0 (+https://github.com/; personal research)"

# 全局超时（秒）
TIMEOUT = 20


class CollectorError(Exception):
    """采集器内部错误，仅用于日志，不会中断整体流程。"""


class Collector:
    """所有采集器的基类。

    子类实现 ``fetch()`` 返回 ``list[Signal]``；外部统一调用 ``collect()``，
    后者负责异常隔离——任何单源失败都不会影响其他信源。
    """

    name: str = "Collector"
    market: str = "overseas"

    def __init__(self, cfg: dict[str, Any], config) -> None:
        self.cfg = cfg or {}
        self.config = config
        self.market = self.cfg.get("market", self.market)
        self.last_error: str | None = None

    # ---- 子类实现 ----
    def fetch(self) -> list[Signal]:  # pragma: no cover - 抽象
        raise NotImplementedError

    # ---- 外部统一入口（带容错）----
    def collect(self) -> list[Signal]:
        try:
            signals = self.fetch() or []
            logger.info("[%s] 采集到 %d 条", self.name, len(signals))
            return signals
        except Exception as exc:  # noqa: BLE001 - 故意捕获所有异常做降级
            self.last_error = str(exc)
            logger.warning("[%s] 采集失败，已跳过：%s", self.name, exc)
            return []

    # ---- 工具方法 ----
    def _session(self, extra_headers: dict | None = None) -> requests.Session:
        sess = requests.Session()
        headers = {"User-Agent": DEFAULT_UA, "Accept": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        sess.headers.update(headers)
        return sess

    def _get(self, url: str, session: requests.Session | None = None, **kwargs) -> requests.Response:
        sess = session or self._session()
        kwargs.setdefault("timeout", TIMEOUT)
        resp = sess.get(url, **kwargs)
        resp.raise_for_status()
        return resp
