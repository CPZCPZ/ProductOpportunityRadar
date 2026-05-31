"""V2EX 采集器（官方 API v1，合规）。

使用官方公开端点 https://www.v2ex.com/api/topics/show.json?node_name=xxx
抓取指定节点（如 create 分享创造、ideas 奇思妙想）的主题。
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Signal
from .base import Collector

API = "https://www.v2ex.com/api/topics/show.json"


class V2exCollector(Collector):
    name = "V2EX"
    market = "domestic"

    def fetch(self) -> list[Signal]:
        nodes = self.cfg.get("nodes", []) or []
        limit = int(self.cfg.get("limit_per_node", 15))
        recent_hours = self.config.recent_hours
        since_ts = datetime.now(timezone.utc).timestamp() - recent_hours * 3600

        sess = self._session()
        signals: list[Signal] = []
        for node in nodes:
            resp = self._get(API, session=sess, params={"node_name": node})
            topics = resp.json()
            if not isinstance(topics, list):
                continue
            for topic in topics[:limit]:
                created = float(topic.get("created") or 0)
                if created and created < since_ts:
                    continue
                signals.append(
                    Signal(
                        source=self.name,
                        market=self.market,
                        source_type="api",
                        title=f"[{node}] {topic.get('title', '')}",
                        url=topic.get("url", ""),
                        engagement=int(topic.get("replies") or 0),
                        comments=int(topic.get("replies") or 0),
                        created_at=datetime.fromtimestamp(created, tz=timezone.utc)
                        if created
                        else None,
                        summary=(topic.get("content") or "")[:500],
                    )
                )
        return signals
