"""统一信号数据模型。

所有采集器都把抓到的内容规范化为 Signal，保证每条机会都能溯源
（source + url + created_at）并携带打分、推广提示等信息。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Signal:
    """一条产品机会信号。"""

    source: str                       # 来源平台，如 "Reddit" / "Hacker News"
    title: str                        # 标题/内容摘要
    url: str                          # 原帖直达链接（溯源用）
    market: str = "overseas"          # overseas / domestic
    source_type: str = "api"          # api / rss
    engagement: int = 0               # 点赞/投票/分数
    comments: int = 0                 # 评论数
    created_at: datetime | None = None  # 原文发布时间 (UTC)
    summary: str = ""                 # 简短摘要/正文片段

    # 以下由打分阶段填充
    matched_keywords: list[str] = field(default_factory=list)
    category: str = "趋势"             # 求助 / 新品 / 趋势
    score: float = 0.0

    # 由渲染阶段填充（来自 promotion.yml）
    promo_hint: dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        """距今小时数；无时间则返回一个较大值（视为较旧）。"""
        if self.created_at is None:
            return 9999.0
        now = datetime.now(timezone.utc)
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        delta = now - created
        return max(delta.total_seconds() / 3600.0, 0.0)

    def text_for_matching(self) -> str:
        """用于关键词匹配的文本。"""
        return f"{self.title}\n{self.summary}".lower()
