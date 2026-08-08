#!/usr/bin/env python3
"""Dune 清算数据分析（D4 遗留任务）— DeFi Sphere 全量历史清算分析

背景：Dune 仪表盘（dune.com/gcm/ethereum-block-building）被 Cloudflare 挡（403），
但清算数据的本质是链上事件——用 DeFi Sphere 公开 API（sphere.data.blockanalitica.com）
做等价的全量历史分析。Dune 能做的是"全量历史"，我们用它补上"全量历史"视角。

分析维度（对齐清算套利研究线）：
1. 全量历史清算分布：按网络/协议/时间
2. 清算人市场格局：谁在清算（清算人地址 top N）
3. 套利机会识别：大额清算（抵押品价值 / 清算奖励）
4. 失败/亏损清算：清算后价格继续下跌的情况（清算人亏损 = 机会信号的另一面）

用法：
    python dune_liquidation_analysis.py --days 30          # 分析最近 30 天
    python dune_liquidation_analysis.py --days 365 --networks ethereum,arbitrum
    python dune_liquidation_analysis.py --output data/liquidation_analysis.json

依赖：hermes venv python3.11 + requests（走 Clash 代理）
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
API = "https://sphere.data.blockanalitica.com/liquidations/"  # 注意尾部斜杠（实测必需）


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def fetch_page(session, params):
    r = session.get(API, params=params, timeout=30)
    r.raise_for_status()
    d = r.json()
    # 响应结构：{"data": {"results": [...]}} 或直接 {"results": [...]}
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    return d


def fetch_liquidations(session, network: str, days: int, page_size: int = 100, max_pages: int = 200) -> list:
    """分页拉取全量历史清算（按网络）"""
    fd = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    td = now_iso()
    all_rows = []
    for page in range(1, max_pages + 1):
        params = {
            "sort": "-datetime", "page": page, "limit": page_size,
            "networks": network, "from_date": fd, "to_date": td,
        }
        try:
            d = fetch_page(session, params)
        except Exception as e:
            print(f"  [{network}] 第 {page} 页失败: {str(e)[:100]}", file=sys.stderr)
            break
        rows = d.get("results", [])
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
    return all_rows


def analyze(rows: list, days: int) -> dict:
    out = {
        "days": days,
        "total": len(rows),
        "by_network": Counter(),
        "by_protocol": Counter(),
        "by_day": Counter(),
        "top_liquidators": Counter(),
        "big_trades": [],
        "big_bonus": [],
        "totals": {"collateral_usd": 0.0, "bonus_usd": 0.0},
    }
    for row in rows:
        net = row.get("network", "?")
        proto = row.get("protocol", "?")
        liq = row.get("wallet_address", "?")   # 被清算钱包（API 无清算人字段，wallet_address = 借款人）
        out["by_network"][net] += 1
        out["by_protocol"][proto] += 1
        out["by_day"][row.get("datetime", "?")[:10]] += 1
        out["top_liquidators"][liq] += 1
        def to_float(v):
            try:
                return float(v) if v is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        collateral = to_float(row.get("collateral_seized_usd"))
        bonus = to_float(row.get("liquidation_bonus_usd"))
        out["totals"]["collateral_usd"] += collateral
        out["totals"]["bonus_usd"] += bonus
        if collateral >= 50_000:
            out["big_trades"].append(row)
        if bonus >= 5_000:
            out["big_bonus"].append(row)
    return out


def format_report(a: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append(f"  DeFi 清算全量分析（最近 {a['days']} 天）")
    lines.append("=" * 60)
    lines.append(f"  总清算数: {a['total']}")
    lines.append(f"  抵押品总额: ${a['totals']['collateral_usd']:,.0f}")
    lines.append(f"  清算奖励总额: ${a['totals']['bonus_usd']:,.0f}")
    lines.append("")
    lines.append("  [按网络]")
    for net, cnt in a["by_network"].most_common():
        lines.append(f"    {net:<12} {cnt}")
    lines.append("  [按协议 Top 10]")
    for proto, cnt in a["by_protocol"].most_common(10):
        lines.append(f"    {proto:<24} {cnt}")
    lines.append("  [被清算钱包 Top 10（API 无清算人字段，wallet_address=借款人）]")
    for liq, cnt in a["top_liquidators"].most_common(10):
        lines.append(f"    {liq[:16]}...  {cnt}")
    lines.append("")
    lines.append(f"  [大额清算（抵押品≥$50K）: {len(a['big_trades'])} 笔]")
    for t in a["big_trades"][:10]:
        try:
            coll = float(t.get('collateral_seized_usd') or 0)
            bonus = float(t.get('liquidation_bonus_usd') or 0)
        except (TypeError, ValueError):
            coll, bonus = 0.0, 0.0
        lines.append(
            f"    {t.get('datetime', '?')[:16]} {t.get('network', '?'):<10} "
            f"{t.get('protocol', '?'):<14} 抵押 ${coll:,.0f} 奖励 ${bonus:,.0f}"
        )
    lines.append("")
    lines.append(f"  [高奖励清算（奖励≥$5K）: {len(a['big_bonus'])} 笔]")
    for t in a["big_bonus"][:10]:
        try:
            bonus = float(t.get('liquidation_bonus_usd') or 0)
        except (TypeError, ValueError):
            bonus = 0.0
        lines.append(
            f"    {t.get('datetime', '?')[:16]} {t.get('network', '?'):<10} "
            f"{t.get('protocol', '?'):<14} 奖励 ${bonus:,.0f}"
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--networks", default="ethereum,arbitrum,base,optimism,polygon")
    ap.add_argument("--output", default=None, help="JSON 输出路径")
    args = ap.parse_args()

    session = requests.Session()
    session.proxies = {"https": PROXY, "http": PROXY} if os.environ.get("NO_PROXY") != "1" else {}

    networks = [n.strip() for n in args.networks.split(",") if n.strip()]
    all_rows = []
    for net in networks:
        print(f"拉取 {net} 最近 {args.days} 天清算...", file=sys.stderr)
        rows = fetch_liquidations(session, net, args.days)
        print(f"  {net}: {len(rows)} 条", file=sys.stderr)
        all_rows.extend(rows)

    if not all_rows:
        print("无数据")
        return 1

    a = analyze(all_rows, args.days)
    print(format_report(a))

    if args.output:
        out_path = BASE_DIR / args.output
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "analysis": a,
                "raw_count": len(all_rows),
                "generated": now_iso(),
            }, f, ensure_ascii=False, indent=1, default=str)
        print(f"\nJSON 已保存: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
