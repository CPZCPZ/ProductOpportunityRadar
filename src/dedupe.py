"""去重：按 URL 与标题归一化去重，保留热度较高的一条。"""

from __future__ import annotations

import re

from .models import Signal


def _normalize_title(title: str) -> str:
    # 去掉前缀标签如 [r/SaaS] / [create] / #1 等，仅用于比较
    t = re.sub(r"^\s*[\[#][^\]]*\]?\s*", "", title)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def dedupe(signals: list[Signal]) -> list[Signal]:
    by_key: dict[str, Signal] = {}
    for sig in signals:
        url_key = (sig.url or "").strip().lower()
        title_key = _normalize_title(sig.title)
        key = url_key or title_key
        if not key:
            continue
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = sig
        else:
            # 保留互动更高的
            if (sig.engagement + sig.comments) > (
                existing.engagement + existing.comments
            ):
                by_key[key] = sig

    # 再按标题做一次软去重
    seen_titles: dict[str, Signal] = {}
    for sig in by_key.values():
        tkey = _normalize_title(sig.title)
        if tkey and tkey in seen_titles:
            prev = seen_titles[tkey]
            if (sig.engagement + sig.comments) > (prev.engagement + prev.comments):
                seen_titles[tkey] = sig
        else:
            seen_titles[tkey or sig.url] = sig

    return list(seen_titles.values())
