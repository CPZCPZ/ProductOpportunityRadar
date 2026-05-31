"""Reddit 采集器（官方 API + OAuth，合规）。

需要在 .env 配置 REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET（script 类型应用）。
未配置则该源自动跳过。使用 application-only OAuth（client_credentials），
只读公开内容，不涉及任何用户数据。
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Signal
from .base import Collector, CollectorError

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"


class RedditCollector(Collector):
    name = "Reddit"
    market = "overseas"

    def fetch(self) -> list[Signal]:
        if not self.config.reddit_ready():
            raise CollectorError("未配置 Reddit API 凭据，跳过")

        token = self._get_token()
        sess = self._session(
            {
                "Authorization": f"bearer {token}",
                "User-Agent": self.config.reddit_user_agent,
            }
        )

        subreddits = self.cfg.get("subreddits", []) or []
        listing = self.cfg.get("listing", "top")
        time_filter = self.cfg.get("time_filter", "day")
        limit = int(self.cfg.get("limit_per_sub", 15))
        recent_hours = self.config.recent_hours
        since_ts = datetime.now(timezone.utc).timestamp() - recent_hours * 3600

        signals: list[Signal] = []
        for sub in subreddits:
            url = f"{API_BASE}/r/{sub}/{listing}"
            params = {"limit": limit}
            if listing == "top":
                params["t"] = time_filter
            resp = self._get(url, session=sess, params=params)
            children = resp.json().get("data", {}).get("children", [])
            for child in children:
                d = child.get("data", {})
                created = float(d.get("created_utc") or 0)
                if created and created < since_ts:
                    continue
                permalink = d.get("permalink", "")
                signals.append(
                    Signal(
                        source=self.name,
                        market=self.market,
                        source_type="api",
                        title=f"[r/{sub}] {d.get('title', '')}",
                        url=f"https://www.reddit.com{permalink}",
                        engagement=int(d.get("score") or 0),
                        comments=int(d.get("num_comments") or 0),
                        created_at=datetime.fromtimestamp(created, tz=timezone.utc)
                        if created
                        else None,
                        summary=(d.get("selftext") or "")[:500],
                    )
                )

        return signals

    def _get_token(self) -> str:
        auth = (self.config.reddit_client_id, self.config.reddit_client_secret)
        headers = {"User-Agent": self.config.reddit_user_agent}
        data = {"grant_type": "client_credentials"}
        resp = self._session().post(
            TOKEN_URL, auth=auth, data=data, headers=headers, timeout=20
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise CollectorError("获取 Reddit access_token 失败")
        return token
