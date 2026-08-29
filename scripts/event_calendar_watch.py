#!/usr/bin/env python3
"""
可预测事件窗口日历（watchdog 模式）
====================================
2026-08-28 由用户三句话催生：
- 「指数成分变化=价格波动大」（公告→生效两段式，可预测）
- 「上半年确定套利机会=海力士/SPCX/CRBS」（合成股份 IPO 收敛剧本）
- 「赚大钱=监控、通知、枯坐」

覆盖三类可预测事件（都是公告日期已知/可推算的）：
1. 指数再平衡：标普 500（季度，3 月第三个周五生效）／纳斯达克 100（年度 12 月）／罗素（年度 6 月）
   → 生效日前后被动资金流放大 → 币股/相关正股波动窗口
2. IPO 事件：pre-IPO 永续标的上市日（合成股份收敛剧本，上市前 72h 剧烈收敛）
   → 观察清单为人工维护（pre-IPO 标的一年就几次，curated 数据足够）
3. 上币公告：crypto 新币上市由 listing_monitor 单独覆盖（本脚本不重复）

用法：
  python3 scripts/event_calendar_watch.py            # watchdog：未来 30 天有事件才输出
  python3 scripts/event_calendar_watch.py --days 60  # 窗口可调
  python3 scripts/event_calendar_watch.py --all      # 全量输出（调试）

接入：cron 每日 8:30 watchdog（事件稀少，日扫足够）
"""
import argparse
import datetime as dt
import sys

# 指数再平衡（年度固定模式，生效日=第三个周五）
INDEX_REBALANCE = [
    {"name": "标普500 季度再平衡", "months": [3, 6, 9, 12], "note": "生效日前后被动资金流放大；公告约 T-10 天"},
    {"name": "纳斯达克100 年度再平衡", "months": [12], "note": "年度一次，12 月生效，公告 12 月初"},
    {"name": "罗素3000 年度重组", "months": [6], "note": "年度一次，6 月生效（2026 已过，下轮 2027-06）"},
]

# 指数成分关注股（币股线标的，若有成分变更 → 币股双波动）
INDEX_WATCH_STOCKS = ["MSTR", "COIN", "MU", "SNDK", "WDC", "NVDA", "AVGO", "TSLA", "ALAB", "GME"]

# pre-IPO 观察清单（人工维护：常见 pre-IPO 永续标的 + 预期上市窗口）
# 格式: name, ticker(如有), expected_ipo (None=未知/待确认), note
PRE_IPO_WATCH = [
    # 已完成（历史案例，保留供参考）
    {"name": "SpaceX", "ticker": "SPCX", "expected_ipo": dt.date(2026, 6, 12), "note": "已完成：6/12 IPO，HL 当日 $14 亿成交"},
    {"name": "Cerebras", "ticker": "CBRS", "expected_ipo": dt.date(2026, 5, 14), "note": "已完成：5/14 IPO $185→Day1 $311"},
    # 观察中（2026-08-29 核验，预期窗口为粗估/待确认，事件发生时人工更新）
    {"name": "Anthropic", "ticker": None, "expected_ipo": dt.date(2026, 12, 31),
     "note": "S-1 已交 2026-06-01（首家 major AI lab），GS/JPM/MS 承销，$965B 估值(5月$65B轮)；Q4 2026 目标"},
    {"name": "OpenAI", "ticker": None, "expected_ipo": None,
     "note": "confidential S-1 已交 2026-06-08，$852B 估值(3月)；未定时间，Late 2026 或 2027"},
    {"name": "Databricks", "ticker": None, "expected_ipo": None,
     "note": "IPO-ready 无 S-1(截至5月)，预期 S-1 Q3 2026，$134B 估值，年化收入 $5.4B(+65%)；H2 2026 或 early 2027"},
    {"name": "Stripe", "ticker": None, "expected_ipo": None,
     "note": "无 S-1，$159B 估值(2026-02 tender)；Collison 不急上市，2027-2028 窗口（低优先）"},
    {"name": "Figure", "ticker": None, "expected_ipo": None,
     "note": "无 S-1，$39B 估值(2025-09 Series C)；2027-2028 窗口（低优先）"},
    {"name": "Kraken", "ticker": None, "expected_ipo": None,
     "note": "加密交易所，Q3 2026 Filed（用户领域相关，2026-08-29 核验加入）"},
    {"name": "Discord", "ticker": None, "expected_ipo": None,
     "note": "H2 2026 Filed（2026-08-29 核验加入）"},
]


def third_friday(year, month):
    """某月第三个周五（美国东部）"""
    d = dt.date(year, month, 1)
    # 第一个周五
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(days=14)


def upcoming_index_events(today, days):
    evs = []
    for cfg in INDEX_REBALANCE:
        for m in cfg["months"]:
            for y in (today.year, today.year + 1):
                eff = third_friday(y, m)
                if today - dt.timedelta(days=1) <= eff <= today + dt.timedelta(days=days):
                    t_minus = (eff - today).days
                    evs.append({
                        "kind": "指数再平衡",
                        "date": eff,
                        "name": f"{cfg['name']} {y}",
                        "t_minus": t_minus,
                        "note": cfg["note"] + f"；关注成分股 {', '.join(INDEX_WATCH_STOCKS[:6])}…",
                    })
    return evs


def upcoming_ipo_events(today, days):
    evs = []
    for p in PRE_IPO_WATCH:
        if not p["expected_ipo"]:
            continue
        d = p["expected_ipo"]
        if d > today and d <= today + dt.timedelta(days=days):
            evs.append({
                "kind": "IPO",
                "date": d,
                "name": f"{p['name']}" + (f" ({p['ticker']})" if p["ticker"] else ""),
                "t_minus": (d - today).days,
                "note": p["note"] + "；上市前 72h 合成价剧烈收敛（SPCX/CRBS 剧本）",
            })
    return evs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    today = dt.date.today()
    evs = upcoming_index_events(today, args.days) + upcoming_ipo_events(today, args.days)
    evs.sort(key=lambda e: e["date"])

    # 关键日才提醒（防刷屏）：T-14/10/7/3/1/0 —— 其余时间静默（枯坐）
    KEY_DAYS = {14, 10, 7, 3, 1, 0}
    evs = [e for e in evs if args.all or e["t_minus"] in KEY_DAYS]

    if not evs:
        if args.all:
            print(f"[event_calendar] {today} 起 {args.days} 天内无可预测事件（指数再平衡/pre-IPO）")
        return  # watchdog: 空输出 = 静默

    lines = [f"📅 可预测事件窗口（未来 {args.days} 天）@ {today}"]
    for e in evs:
        tag = "🟢" if e["t_minus"] <= 7 else "🔵"
        lines.append(f"{tag} {e['date']} (T-{e['t_minus']}d) {e['kind']} | {e['name']} | {e['note']}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
