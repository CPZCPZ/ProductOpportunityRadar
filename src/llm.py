"""LLM 智能研判（DeepSeek，OpenAI 兼容接口）。

对每条候选信号判断它是否代表"一个独立开发者/一人公司能做成产品或工具来满足的
真实用户需求/痛点"，并输出需求强度、把需求重述成一句产品机会、建议形态、理由。

设计要点：
- 批量送入（每批 N 条）以省成本；用 JSON 模式输出，便于解析。
- 任何失败都不抛出到主流程：失败的批次保留候选原样、强度记 0（由调用方决定降级策略）。
- 仅用标准库 requests，不引入额外 SDK。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .config import Config
from .models import Signal

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是帮助"一人公司/独立开发者"发现产品机会的资深分析师。
你会收到来自各社区/资讯源的帖子（标题+摘要）。请判断每一条是否代表
"一个独立开发者能做成产品、工具或服务来满足的真实用户需求或痛点"。

判定为机会(keep=true)的典型：
- 用户明确想要某种工具/功能/服务（"有没有工具能…"、"求一个…"）
- 抱怨现有方案太贵/太难用/缺失，想要替代品
- 大量重复的手工劳动，想要自动化
- 同一痛点被多人反复提到

判定为否(keep=false)的典型：
- 纯产品发布、广告、自我推广（Show HN、送码、上线公告等）
- 个人技术求助/客服问题（如系统报错、提审卡住、账号问题）
- 新闻资讯、行业评论、观点讨论、招聘、闲聊
- 没有可被产品解决的明确需求

strength 为 0-100，综合"需求真实度+普遍性+付费可能+独立开发者可行性"打分。
opportunity 用一句中文把需求重述为"做一个X，帮Y解决Z"。
form 给出最合适的产品形态（如：浏览器插件 / 网页SaaS / 命令行脚本 / 手机App / API服务 / 自动化订阅）。
reason 用一句中文说明判断依据。

只输出 JSON 对象，格式：
{"results":[{"index":0,"keep":true,"strength":78,"opportunity":"...","form":"...","reason":"..."}, ...]}
results 必须与输入条目一一对应、index 从输入给定的编号取值。"""


def _client_post(config: Config, messages: list[dict]) -> dict[str, Any]:
    url = f"{config.deepseek_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.deepseek_model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _build_user_prompt(batch: list[Signal]) -> str:
    lines = ["请研判以下条目（保持 index 对应）：", ""]
    for idx, sig in enumerate(batch):
        text = sig.title
        if sig.summary:
            text += f" —— {sig.summary[:200]}"
        lines.append(f"[{idx}] (来源:{sig.source}) {text}")
    return "\n".join(lines)


def _judge_batch(config: Config, batch: list[Signal]) -> None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(batch)},
    ]
    data = _client_post(config, messages)
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    results = parsed.get("results", []) if isinstance(parsed, dict) else []

    by_index: dict[int, dict] = {}
    for item in results:
        try:
            by_index[int(item.get("index"))] = item
        except (TypeError, ValueError):
            continue

    for idx, sig in enumerate(batch):
        item = by_index.get(idx)
        if not item:
            continue
        sig.is_opportunity = bool(item.get("keep"))
        try:
            sig.demand_strength = int(item.get("strength") or 0)
        except (TypeError, ValueError):
            sig.demand_strength = 0
        sig.restated = str(item.get("opportunity") or "").strip()
        sig.suggested_form = str(item.get("form") or "").strip()
        sig.llm_reason = str(item.get("reason") or "").strip()


def judge_signals(signals: list[Signal], config: Config) -> list[Signal]:
    """对候选信号做 LLM 研判，原地填充字段并返回判定为机会的子集。

    若未配置 key 或全部批次失败，返回空列表，由调用方决定降级。
    """
    if not config.llm_ready() or not signals:
        return []

    batch_size = max(1, config.llm_batch_size)
    ok_batches = 0
    total_batches = 0

    for start in range(0, len(signals), batch_size):
        batch = signals[start : start + batch_size]
        total_batches += 1
        try:
            _judge_batch(config, batch)
            ok_batches += 1
        except Exception as exc:  # noqa: BLE001 - 单批失败不影响其他批
            logger.warning("LLM 批次研判失败（已跳过该批）：%s", exc)

    logger.info("LLM 研判完成：%d/%d 批成功", ok_batches, total_batches)
    if ok_batches == 0:
        return []  # 完全失败 -> 交给上层降级

    kept = [
        s
        for s in signals
        if s.is_opportunity and s.demand_strength >= config.llm_min_strength
    ]
    logger.info("LLM 判定为真实需求：%d 条（阈值 %d）", len(kept), config.llm_min_strength)
    return kept
