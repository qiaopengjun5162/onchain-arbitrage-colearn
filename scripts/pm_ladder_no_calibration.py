#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PM 月度阶梯盘「卖 No」定价校准（pm_ladder_no_calibration.py）— 2026-08-24

触发：群分享四连发③（@jnstrtprdctnmrkts 卖 No 机器人 $10K→$978K/90.2%，转述未核验）
→ 用已结算阶梯盘数据校准「人群过度支付远端目标」假设（RN1 笔记053 机制互证）

方法：
- 事件：what-price-will-bitcoin-hit-in-{april..august}（2025 年 5 个月度 BTC 阶梯盘）
- 每个市场：生命中期 No 价（CLOB prices-history fidelity=1440 取中位点）vs 最终结果
- 分带统计：真实 No 胜率 vs 隐含（No 均价）→ 偏差 → EV（毛/净，含 taker 费 0.07×p×(1-p)）

坑（已踩）：
- Gamma outcomePrices/clobTokenIds 是 JSON **字符串**（'["0","1"]'），要 json.loads，float() 直接炸
- CLOB prices-history 用 **token_id**（不是事件/市场 id）；fidelity=1440 才有月度粒度
- 每市场请求间隔 ≥0.3s 防限流（无 sleep 会静默丢样本）

用法：hermes venv python3 scripts/pm_ladder_no_calibration.py [--months june,august]

2026-08-24 实测（2025-04~08，63 样本/36 在带）：
- 0.85-0.90 带：真实 80.0% vs 隐含 88.3% → 偏差 -8.3% → 负 EV（尾部风险集中区）
- 0.90-0.95 带：真实 100% vs 隐含 92.6% → 偏差 +7.4% → 正 EV +7¢/股
- 0.95-0.995 带：真实 100% vs 隐含 98.1% → 偏差 +1.9% → 正 EV +2¢/股（薄）
- 合计：97.2% vs 95.9% → +1.3% → 净 ~+2¢/$1（薄利+容量游戏）
- 8 月 90%（$120K 真被触达）→ 牛市里远端目标会实现，0.85-0.90 不可碰
"""
import argparse
import json
import sys
import time
import urllib.request

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
UA = "Mozilla/5.0"
DEFAULT_MONTHS = ["april", "may", "june", "july", "august"]
BANDS = [(0.80, 0.85), (0.85, 0.90), (0.90, 0.95), (0.95, 0.995)]
FEE = 0.07


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", default=",".join(DEFAULT_MONTHS),
                    help="月度事件 slug 后缀（逗号分隔）")
    ap.add_argument("--asset", default="bitcoin", choices=["bitcoin", "ethereum"],
                    help="标的（bitcoin/ethereum，决定阶梯盘 slug 前缀）")
    args = ap.parse_args()
    months = args.months.split(",")
    prefix = "what-price-will-ethereum-hit-in" if args.asset == "ethereum" else "what-price-will-bitcoin-hit-in"

    rows = []
    for m in months:
        d = get(f"{GAMMA}/events?slug={prefix}-{m}")
        if not d:
            print(f"[!] {m}: 事件未找到")
            continue
        for mk in d[0].get("markets") or []:
            try:
                op = json.loads(mk.get("outcomePrices") or '["0","0"]')
                yes_won = float(op[0]) > 0.5
                tids = json.loads(mk.get("clobTokenIds") or "[]")
                if len(tids) < 2:
                    continue
                h = get(f"{CLOB}/prices-history?market={tids[0]}&interval=max&fidelity=1440")
                time.sleep(0.3)
                hist = (h or {}).get("history") or []
                if len(hist) < 3:
                    continue
                no_mid = 1 - hist[len(hist) // 2]["p"]
                rows.append({"month": m, "no_mid": no_mid, "no_won": not yes_won})
            except Exception:
                continue
        time.sleep(0.4)

    inband = [r for r in rows if 0.80 <= r["no_mid"] <= 0.995]
    print(f"总样本 {len(rows)}，No 价带 0.80-0.995 内 {len(inband)} 个\n")
    print(f"{'No价带':<12}{'样本':>5}{'No胜率(真实)':>13}{'隐含(均价)':>11}{'偏差':>8}{'毛EV/股':>9}{'净EV(含费)':>10}")
    for lo, hi in BANDS:
        band = [r for r in inband if lo <= r["no_mid"] < hi]
        if not band:
            print(f"{lo:.2f}-{hi:.3f}: 无样本")
            continue
        n = len(band)
        real = sum(1 for r in band if r["no_won"]) / n
        implied = sum(r["no_mid"] for r in band) / n
        fee = FEE * implied * (1 - implied)
        print(f"{lo:.2f}-{hi:.3f}{n:>6}{real:>12.1%}{implied:>11.1%}{real-implied:>+8.1%}"
              f"{real - implied:>+9.2f}{real - implied - fee:>+10.2f}")
    if inband:
        n = len(inband)
        real = sum(1 for r in inband if r["no_won"]) / n
        implied = sum(r["no_mid"] for r in inband) / n
        print(f"\n合计 {n}: 真实 {real:.1%} vs 隐含 {implied:.1%} → 偏差 {real-implied:+.1%}")
        for m in months:
            mm = [r for r in inband if r["month"] == m]
            if mm:
                r2 = sum(1 for r in mm if r["no_won"]) / len(mm)
                print(f"  {m}: {len(mm)} 样本, No 胜率 {r2:.0%}")


if __name__ == "__main__":
    sys.exit(main())
