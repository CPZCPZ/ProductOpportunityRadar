"""机会打分与分类。

score = w1*log(1+热度) + w2*关键词命中 + w3*时效 + w4*类别权重

- 热度：点赞 + 评论，取对数避免大数压制小数
- 关键词命中：命中 keywords.yml 中的痛点词，越多越高，并据此判定类别
- 时效：越新越高（线性衰减到 0）
- 类别权重：求助 > 新品 > 趋势
"""

from __future__ import annotations

import math

from .config import Config
from .models import Signal

# 权重（可按需调整）
W_HEAT = 1.0
W_KEYWORD = 3.0
W_RECENCY = 2.0
W_CATEGORY = 2.0

CATEGORY_WEIGHT = {
    "求助": 1.0,
    "新品": 0.5,
    "趋势": 0.2,
}


def _detect_category(signal: Signal, matched: list[str]) -> str:
    if matched:
        return "求助"
    if signal.source in {"Product Hunt", "App Store"}:
        return "新品"
    return "趋势"


def _match_keywords(signal: Signal, keywords: list[str]) -> list[str]:
    text = signal.text_for_matching()
    return [kw for kw in keywords if kw and kw in text]


# 命中负向词的惩罚（用于关键词预筛排序，降低个人求助/纯发布的优先级）
W_NEGATIVE = 2.5


def score_signal(
    signal: Signal,
    keywords: list[str],
    recent_hours: int,
    negatives: list[str] | None = None,
) -> Signal:
    matched = _match_keywords(signal, keywords)
    signal.matched_keywords = matched
    signal.category = _detect_category(signal, matched)

    heat = math.log1p(signal.engagement + signal.comments)
    keyword_score = math.log1p(len(matched)) * 1.5

    age = signal.age_hours
    recency = max(0.0, 1.0 - age / float(recent_hours)) if recent_hours > 0 else 0.0

    category_w = CATEGORY_WEIGHT.get(signal.category, 0.2)

    neg_hits = 0
    if negatives:
        text = signal.text_for_matching()
        neg_hits = sum(1 for kw in negatives if kw and kw in text)

    signal.score = round(
        W_HEAT * heat
        + W_KEYWORD * keyword_score
        + W_RECENCY * recency
        + W_CATEGORY * category_w
        - W_NEGATIVE * neg_hits,
        3,
    )
    return signal


def score_all(signals: list[Signal], config: Config) -> list[Signal]:
    keywords = config.keyword_list()
    negatives = config.negative_keywords()
    for signal in signals:
        score_signal(signal, keywords, config.recent_hours, negatives)
    return signals


def rank_reference(
    signals: list[Signal], top_per_market: int
) -> tuple[list[Signal], list[Signal]]:
    """趋势/灵感参考区：按热度+时效排序，不经过 LLM。"""
    overseas = sorted(
        (s for s in signals if s.market == "overseas"),
        key=lambda s: s.score,
        reverse=True,
    )[:top_per_market]
    domestic = sorted(
        (s for s in signals if s.market == "domestic"),
        key=lambda s: s.score,
        reverse=True,
    )[:top_per_market]
    return overseas, domestic


def rank_opportunities(
    signals: list[Signal], top_overseas: int, top_domestic: int
) -> tuple[list[Signal], list[Signal]]:
    """真实需求区：优先按 LLM 需求强度排序，其次关键词分。"""
    def sort_key(s: Signal):
        return (s.demand_strength, s.score)

    overseas = sorted(
        (s for s in signals if s.market == "overseas"),
        key=sort_key,
        reverse=True,
    )[:top_overseas]
    domestic = sorted(
        (s for s in signals if s.market == "domestic"),
        key=sort_key,
        reverse=True,
    )[:top_domestic]
    return overseas, domestic


def rank_by_market(
    signals: list[Signal], top_overseas: int, top_domestic: int
) -> tuple[list[Signal], list[Signal]]:
    overseas = sorted(
        (s for s in signals if s.market == "overseas"),
        key=lambda s: s.score,
        reverse=True,
    )[:top_overseas]
    domestic = sorted(
        (s for s in signals if s.market == "domestic"),
        key=lambda s: s.score,
        reverse=True,
    )[:top_domestic]
    return overseas, domestic
