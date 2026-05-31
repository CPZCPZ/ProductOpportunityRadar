"""Product Hunt 采集器（官方 GraphQL API v2，合规，可选）。

需要在 .env 配置 PRODUCTHUNT_TOKEN（开发者 token）。未配置则自动跳过。
抓取近期热门新品，作为"别人已经在做什么"的灵感与竞品参考。
"""

from __future__ import annotations

from datetime import datetime

from ..models import Signal
from .base import Collector, CollectorError

API = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
query ($n: Int!) {
  posts(order: VOTES, first: $n) {
    edges {
      node {
        name
        tagline
        url
        votesCount
        commentsCount
        createdAt
      }
    }
  }
}
"""


class ProductHuntCollector(Collector):
    name = "Product Hunt"
    market = "overseas"

    def fetch(self) -> list[Signal]:
        if not self.config.producthunt_ready():
            raise CollectorError("未配置 Product Hunt token，跳过")

        limit = int(self.cfg.get("limit", 20))
        headers = {
            "Authorization": f"Bearer {self.config.producthunt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        sess = self._session(headers)
        resp = sess.post(
            API, json={"query": QUERY, "variables": {"n": limit}}, timeout=20
        )
        resp.raise_for_status()
        edges = (
            resp.json().get("data", {}).get("posts", {}).get("edges", [])
        )

        signals: list[Signal] = []
        for edge in edges:
            node = edge.get("node", {})
            created = None
            if node.get("createdAt"):
                try:
                    created = datetime.fromisoformat(
                        node["createdAt"].replace("Z", "+00:00")
                    )
                except ValueError:
                    created = None
            signals.append(
                Signal(
                    source=self.name,
                    market=self.market,
                    source_type="api",
                    title=node.get("name", ""),
                    url=node.get("url", ""),
                    engagement=int(node.get("votesCount") or 0),
                    comments=int(node.get("commentsCount") or 0),
                    created_at=created,
                    summary=node.get("tagline", ""),
                )
            )
        return signals
