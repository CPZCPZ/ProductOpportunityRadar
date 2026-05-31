"""通用 RSS 采集器。

消费各平台官方对外发布的 RSS（RSS 本就是供订阅的，合规）。
通过 sources.yml 的 feeds 列表配置：[{name, url}, ...]。
"""

from __future__ import annotations

from datetime import datetime, timezone
from time import mktime

import feedparser

from ..models import Signal
from .base import Collector, DEFAULT_UA


class RSSCollector(Collector):
    market = "overseas"

    def __init__(self, cfg, config, name: str = "RSS") -> None:
        super().__init__(cfg, config)
        self.name = name

    def fetch(self) -> list[Signal]:
        feeds = self.cfg.get("feeds", []) or []
        recent_hours = self.config.recent_hours
        now = datetime.now(timezone.utc)

        signals: list[Signal] = []
        for feed in feeds:
            url = feed.get("url")
            label = feed.get("name", self.name)
            if not url:
                continue
            parsed = feedparser.parse(url, agent=DEFAULT_UA)
            for entry in parsed.entries:
                created = self._entry_time(entry)
                if created is not None:
                    age_h = (now - created).total_seconds() / 3600
                    if age_h > recent_hours:
                        continue
                title = getattr(entry, "title", "") or ""
                if not title:
                    continue
                summary = getattr(entry, "summary", "") or ""
                # 去掉 RSS 摘要里的 HTML 标签的简单处理
                summary = _strip_html(summary)[:500]
                signals.append(
                    Signal(
                        source=label,
                        market=self.market,
                        source_type="rss",
                        title=title,
                        url=getattr(entry, "link", "") or "",
                        engagement=0,
                        comments=0,
                        created_at=created,
                        summary=summary,
                    )
                )
        return signals

    @staticmethod
    def _entry_time(entry) -> datetime | None:
        for key in ("published_parsed", "updated_parsed"):
            value = getattr(entry, key, None)
            if value:
                return datetime.fromtimestamp(mktime(value), tz=timezone.utc)
        return None


def _strip_html(text: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
