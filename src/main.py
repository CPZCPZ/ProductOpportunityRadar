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
from . import history
from .llm import judge_signals
from .render import render_html, save_html
from .scoring import rank_opportunities, rank_reference, score_all

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

    # 关键词预筛打分（含负向词降权）
    score_all(all_signals, config)

    # 按 kind 拆分：需求候选 vs 趋势参考
    demand_candidates = [s for s in all_signals if s.kind == "demand"]
    reference_items = [s for s in all_signals if s.kind == "reference"]

    # 跨天去重：剔除历史已发送过的条目，保证每天只看到"新增"
    if config.dedupe_across_days:
        seen = history.load_seen()
        before = (len(demand_candidates), len(reference_items))
        demand_candidates = history.filter_unseen(demand_candidates, seen)
        reference_items = history.filter_unseen(reference_items, seen)
        logger.info(
            "跨天去重：需求 %d→%d，参考 %d→%d（历史库 %d 条）",
            before[0], len(demand_candidates),
            before[1], len(reference_items), len(seen),
        )

    logger.info(
        "需求候选 %d / 趋势参考 %d", len(demand_candidates), len(reference_items)
    )

    # 需求候选 -> LLM 智能研判（预筛排序后截断到预算上限以控制成本）
    demand_candidates.sort(key=lambda s: s.score, reverse=True)
    budget = config.llm_max_candidates
    to_judge = demand_candidates[:budget]

    llm_used = False
    if config.llm_ready():
        kept = judge_signals(to_judge, config)
        if kept:
            llm_used = True
            opp_pool = kept
        else:
            logger.warning("LLM 不可用或无结果，降级为关键词模式")
            opp_pool = to_judge
    else:
        logger.info("未配置 DeepSeek，使用关键词模式（建议配置以提升质量）")
        opp_pool = to_judge

    overseas, domestic = rank_opportunities(
        opp_pool, config.top_n_overseas, config.top_n_domestic
    )
    ref_overseas, ref_domestic = rank_reference(
        reference_items, config.top_n_reference
    )
    logger.info(
        "入选机会：海外 %d / 国内 %d；参考：海外 %d / 国内 %d",
        len(overseas), len(domestic), len(ref_overseas), len(ref_domestic),
    )

    html = render_html(
        overseas,
        domestic,
        config,
        ref_overseas=ref_overseas,
        ref_domestic=ref_domestic,
        llm_used=llm_used,
        source_errors=source_errors,
    )

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

    # 发送成功后：归档当日日报 + 记录已发送 URL（供跨天去重与历史回溯）
    sent_items = overseas + domestic + ref_overseas + ref_domestic
    try:
        history.persist(html, sent_items, date_str, config.history_retention_days)
    except Exception as exc:  # noqa: BLE001 - 历史写入失败不影响主流程
        logger.warning("写入历史失败（不影响发信）：%s", exc)
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
