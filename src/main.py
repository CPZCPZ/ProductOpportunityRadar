"""编排入口：采集 → 去重 → 打分 → 排序 → 渲染 → 发信。

用法：
    python -m src.main            # 抓取并发送邮件
    python -m src.main --dry-run  # 仅本地生成 HTML，不发邮件
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from .collectors import build_collectors
from .config import Config
from .dedupe import dedupe
from .render import render_html, save_html
from .scoring import rank_by_market, score_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("radar")


def run(dry_run: bool = False) -> int:
    config = Config()

    collectors = build_collectors(config)
    logger.info("启用采集器：%s", ", ".join(c.name for c in collectors) or "(无)")

    all_signals = []
    source_errors: list[dict] = []
    for collector in collectors:
        signals = collector.collect()
        all_signals.extend(signals)
        if collector.last_error:
            source_errors.append({"name": collector.name, "error": collector.last_error})

    logger.info("原始信号 %d 条", len(all_signals))

    all_signals = dedupe(all_signals)
    logger.info("去重后 %d 条", len(all_signals))

    score_all(all_signals, config)
    overseas, domestic = rank_by_market(
        all_signals, config.top_n_overseas, config.top_n_domestic
    )
    logger.info("入选：海外 %d / 国内 %d", len(overseas), len(domestic))

    html = render_html(overseas, domestic, config, source_errors=source_errors)

    date_str = datetime.now().strftime("%Y-%m-%d")
    if dry_run:
        path = save_html(html, date_str)
        logger.info("已生成本地预览：%s", path)
        return 0

    # 同时保存一份本地副本，方便排查
    save_html(html, date_str)

    from .mailer import send_email

    subject = f"产品机会雷达 {date_str} · {len(overseas) + len(domestic)} 条机会"
    send_email(html, config, subject)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="产品机会雷达")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只生成本地 HTML，不发送邮件",
    )
    args = parser.parse_args()
    try:
        return run(dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        logger.error("运行失败：%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
