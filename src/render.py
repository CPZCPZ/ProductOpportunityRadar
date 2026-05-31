"""渲染日报为 HTML（手机友好）。

为每条信号附加来源对应的推广提示（来自 promotion.yml），并生成
邮件底部的"推广渠道总表"与"冷启动 7 步"。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import ROOT, Config
from .models import Signal

TEMPLATE_DIR = ROOT / "templates"

COLD_START_STEPS = [
    "锁定一条机会，去原帖把需求读懂（用户到底卡在哪）。",
    "在原帖下真诚回复，确认需求是否真实、高频、愿意付费。",
    "做一个最小可用版本(MVP) + 一个简单落地页（说清解决什么问题）。",
    "回到来源社区/同类人群处分享，收集邮箱或微信，别硬广。",
    "给前 10 个用户手动免费服务，换取真实反馈与口碑。",
    "把反馈做成案例/体验文，在对应渠道（见每条提示）持续输出。",
    "跑通一笔付费后再考虑放大投放，先验证再花钱。",
]


def _promo_for(signal: Signal, promotion: dict) -> dict:
    key = (signal.source or "").lower()
    # 精确匹配 -> 模糊包含匹配 -> default
    if key in promotion:
        return promotion[key]
    for k, v in promotion.items():
        if k == "default":
            continue
        if k in key or key in k:
            return v
    return promotion.get("default", {})


def _build_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_html(
    overseas: list[Signal],
    domestic: list[Signal],
    config: Config,
    source_errors: list[dict] | None = None,
) -> str:
    promotion = config.promotion or {}
    for sig in overseas + domestic:
        sig.promo_hint = _promo_for(sig, promotion)

    env = _build_env()
    template = env.get_template("email.html.j2")
    promo_table = {
        k: v for k, v in promotion.items() if k != "default"
    }
    return template.render(
        date_str=datetime.now().strftime("%Y-%m-%d"),
        overseas=overseas,
        domestic=domestic,
        cold_start_steps=COLD_START_STEPS,
        promo_table=promo_table,
        source_errors=source_errors or [],
        total=len(overseas) + len(domestic),
    )


def save_html(html: str, date_str: str | None = None) -> Path:
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"radar-{date_str}.html"
    path.write_text(html, encoding="utf-8")
    return path
