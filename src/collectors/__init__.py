"""信源采集器集合（仅使用官方 API / 官方 RSS）。"""

from __future__ import annotations

from .base import Collector
from .hackernews import HackerNewsCollector
from .reddit import RedditCollector
from .producthunt import ProductHuntCollector
from .rss import RSSCollector
from .v2ex import V2exCollector
from .appstore import AppStoreCollector

__all__ = [
    "Collector",
    "HackerNewsCollector",
    "RedditCollector",
    "ProductHuntCollector",
    "RSSCollector",
    "V2exCollector",
    "AppStoreCollector",
    "build_collectors",
]


def build_collectors(config) -> list[Collector]:
    """根据 sources.yml 与 .env 构建启用的采集器列表。"""
    collectors_cfg = config.collectors
    result: list[Collector] = []

    def cfg(name: str) -> dict:
        return collectors_cfg.get(name, {}) or {}

    if cfg("hackernews").get("enabled"):
        result.append(HackerNewsCollector(cfg("hackernews"), config))
    if cfg("reddit").get("enabled"):
        result.append(RedditCollector(cfg("reddit"), config))
    if cfg("producthunt").get("enabled"):
        result.append(ProductHuntCollector(cfg("producthunt"), config))
    if cfg("rss_overseas").get("enabled"):
        result.append(RSSCollector(cfg("rss_overseas"), config, name="RSS(海外)"))
    if cfg("v2ex").get("enabled"):
        result.append(V2exCollector(cfg("v2ex"), config))
    if cfg("appstore").get("enabled"):
        result.append(AppStoreCollector(cfg("appstore"), config))
    if cfg("rss_domestic").get("enabled"):
        result.append(RSSCollector(cfg("rss_domestic"), config, name="RSS(国内)"))

    return result
