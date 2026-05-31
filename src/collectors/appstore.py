"""App Store 榜单采集器（Apple 官方 iTunes RSS，合规）。

使用 Apple 官方 RSS 生成器：
https://itunes.apple.com/{country}/rss/{feed}/limit={n}/json
抓取免费榜，用于观察热门 App 与赛道，研究同类差评里的产品机会。
"""

from __future__ import annotations

from ..models import Signal
from .base import Collector


class AppStoreCollector(Collector):
    name = "App Store"
    market = "domestic"

    def fetch(self) -> list[Signal]:
        country = self.cfg.get("country", "cn")
        feed = self.cfg.get("feed", "topfreeapplications")
        limit = int(self.cfg.get("limit", 20))

        url = (
            f"https://itunes.apple.com/{country}/rss/{feed}/limit={limit}/json"
        )
        sess = self._session()
        resp = self._get(url, session=sess)
        entries = resp.json().get("feed", {}).get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]

        signals: list[Signal] = []
        for idx, entry in enumerate(entries):
            name = entry.get("im:name", {}).get("label", "")
            category = entry.get("category", {}).get("attributes", {}).get("label", "")
            summary = entry.get("summary", {}).get("label", "")
            link = entry.get("id", {}).get("label", "")
            # 用排名反推一个"热度"分（榜首最高）
            rank_score = max(limit - idx, 1)
            signals.append(
                Signal(
                    source=self.name,
                    market=self.market,
                    source_type="rss",
                    title=f"#{idx + 1} {name}（{category}）",
                    url=link,
                    engagement=rank_score,
                    comments=0,
                    created_at=None,
                    summary=summary[:500],
                )
            )
        return signals
