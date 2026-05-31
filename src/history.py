"""历史记录与跨天去重。

- seen.json：记录已发送过的条目 URL 及发送日期，用于跨天去重，保证每天只看到"新增"机会。
- history/reports/YYYY-MM-DD.html：每日日报存档，便于回溯查看历史发了哪些内容。
- history/README.md：自动生成的索引（日期 + 数量 + 存档链接）。

这些文件由 GitHub Actions 每次运行后自动提交回仓库——既留存历史，又顺带"保活"
（仓库有提交活动，避免定时任务因 60 天无活动被停用）。
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import ROOT
from .models import Signal

logger = logging.getLogger(__name__)

HISTORY_DIR = ROOT / "history"
REPORTS_DIR = HISTORY_DIR / "reports"
SEEN_FILE = HISTORY_DIR / "seen.json"
INDEX_FILE = HISTORY_DIR / "README.md"


def _ensure_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_seen() -> dict[str, str]:
    """返回 {url: 'YYYY-MM-DD'}。"""
    if not SEEN_FILE.exists():
        return {}
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return data.get("sent", {}) if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取 seen.json 失败，忽略：%s", exc)
        return {}


def filter_unseen(signals: list[Signal], seen: dict[str, str]) -> list[Signal]:
    """剔除 URL 已在历史中出现过的条目。"""
    out = []
    for s in signals:
        url = (s.url or "").strip()
        if url and url in seen:
            continue
        out.append(s)
    return out


def record_sent(
    sent: list[Signal], seen: dict[str, str], retention_days: int = 60
) -> dict[str, str]:
    """把本次发送的条目 URL 记入 seen，并按保留天数裁剪旧记录。"""
    today = date.today().isoformat()
    for s in sent:
        url = (s.url or "").strip()
        if url:
            seen[url] = today

    # 裁剪过期记录，避免文件无限增长
    cutoff = date.today() - timedelta(days=retention_days)
    pruned = {}
    for url, day in seen.items():
        try:
            if datetime.strptime(day, "%Y-%m-%d").date() >= cutoff:
                pruned[url] = day
        except ValueError:
            pruned[url] = day  # 无法解析的保留
    return pruned


def save_seen(seen: dict[str, str]) -> None:
    _ensure_dirs()
    payload = {"updated_at": datetime.now().isoformat(timespec="seconds"), "sent": seen}
    SEEN_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def archive_report(html: str, date_str: str) -> Path:
    """把当天日报 HTML 存档。"""
    _ensure_dirs()
    path = REPORTS_DIR / f"{date_str}.html"
    path.write_text(html, encoding="utf-8")
    return path


def rebuild_index() -> None:
    """扫描 reports/ 重建索引 README.md。"""
    _ensure_dirs()
    files = sorted(REPORTS_DIR.glob("*.html"), reverse=True)
    lines = [
        "# 产品机会雷达 · 历史日报存档",
        "",
        "每天自动生成。点击日期查看当天发送的完整日报。",
        "",
        "| 日期 | 存档 |",
        "| --- | --- |",
    ]
    for f in files:
        day = f.stem
        lines.append(f"| {day} | [查看 reports/{f.name}](reports/{f.name}) |")
    if not files:
        lines.append("| (暂无) | |")
    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def persist(html: str, sent: list[Signal], date_str: str, retention_days: int = 60) -> None:
    """一次性完成：归档当日日报 + 记录已发送 URL + 重建索引。"""
    seen = load_seen()
    seen = record_sent(sent, seen, retention_days)
    save_seen(seen)
    archive_report(html, date_str)
    rebuild_index()
    logger.info("历史已更新：归档 %s，去重库 %d 条", date_str, len(seen))
