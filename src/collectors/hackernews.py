"""Hacker News 采集器。

使用 Algolia 官方为 HN 提供的公开 Search API（免 key、免费、合规）：
https://hn.algolia.com/api
按痛点关键词搜索近段时间内的 story / ask。
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Signal
from .base import Collector

API = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNewsCollector(Collector):
    name = "Hacker News"
    market = "overseas"

    def fetch(self) -> list[Signal]:
        queries = self.cfg.get("queries", []) or []
        hits_per_query = int(self.cfg.get("hits_per_query", 20))
        min_points = int(self.cfg.get("min_points", 0))
        recent_hours = self.config.recent_hours

        since_ts = int(datetime.now(timezone.utc).timestamp()) - recent_hours * 3600

        sess = self._session()
        seen: set[str] = set()
        signals: list[Signal] = []

        for query in queries:
            params = {
                "query": query,
                "tags": "(story,ask_hn)",
                "numericFilters": f"created_at_i>{since_ts}",
                "hitsPerPage": hits_per_query,
            }
            resp = self._get(API, session=sess, params=params)
            data = resp.json()
            for hit in data.get("hits", []):
                object_id = str(hit.get("objectID"))
                if object_id in seen:
                    continue
                seen.add(object_id)

                points = int(hit.get("points") or 0)
                if points < min_points:
                    continue

                title = hit.get("title") or hit.get("story_title") or ""
                if not title:
                    continue

                created_i = hit.get("created_at_i")
                created = (
                    datetime.fromtimestamp(created_i, tz=timezone.utc)
                    if created_i
                    else None
                )
                hn_url = f"https://news.ycombinator.com/item?id={object_id}"

                signals.append(
                    Signal(
                        source=self.name,
                        market=self.market,
                        source_type="api",
                        title=title,
                        url=hn_url,
                        engagement=points,
                        comments=int(hit.get("num_comments") or 0),
                        created_at=created,
                        summary=(hit.get("story_text") or "")[:500],
                    )
                )

        return signals
