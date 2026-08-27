#!/usr/bin/env python3
"""
Firsto TapeOut 跨市场价差扫描（官方市场 vs Firsto 聚合终端）
=============================================================
机制（用户实操验证 2026-08-27）：
- 官方市场只有买单侧（卖单为 0），Firsto 支持双边挂单
- 官方挂买单 → Firsto 聚合簿可见；Firsto 挂单 → 官方不可见
- 套利 = 官方市场低价收（卖家习惯在官方卖）→ Firsto 高价卖
- API: /v1/book/{transistors_addr}/{tokenId} 返回聚合订单簿，每单带 venue=official|ours

用法：
- 手动: python3 scripts/firsto_cross_market_scan.py --once
- cron watchdog: 无报警静默（stdout 空），价差超阈值才输出 → 由 cron 推送

阈值逻辑：
- 净价差 = (Firsto最优买 - 官方最优买)/官方最优买 - 手续费(官方1% + Firsto吃单0.5%)
- 净价差 >= ALERT_BPS(150 = 1.5%) 且可成交量 >= MIN_QTY 才报警
"""
import json
import sys
import urllib.request
from collections import defaultdict

API = "https://api-tapeout.firsto.ai"
WAD = 10**18

# 官方 5 市场（transistors 合约地址 = book 的 marketId）
OFFICIAL_MARKETS = [
    ("TapeOut",       "0xCC42ba5De07f01B472a5b14cF45aBcCA79Eb8087"),
    ("Genesis CPU",   "0x1d23Bf70ec6bAAD95f396Ea38f8A8415119dFDE6"),
    ("Blonskr_No1",   "0xE2DfD802081C7a05341E20b6582b04b908e8550c"),
    ("Bitcoin Miner", "0x140FDD905849a49064f8d366ABE7b21Ff83DAFB5"),
    ("RefBench",      "0xB645572D56E81ca2844fA833ad14f146a10e8330"),
]
TOKENS = [(0, "NAND"), (1, "LATCH")]

# 参数
ALERT_BPS = 150          # 净价差 >= 1.5% 报警（扣手续费后）
MIN_QTY = 3              # 可成交量下限（个）
MIN_VALUE_BNB = 0.1      # 可成交金额下限（BNB，防灰尘级误报；gas+滑点门槛）
TOP_N = 3                # 加权平均取前 N 档
FEE_BPS = 150            # 手续费成本：官方吃单1% + Firsto吃单0.5%


def get(path, proxy=True, timeout=20):
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler(
            {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}))
    else:
        handlers.append(urllib.request.ProxyHandler({}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(API + path, headers={
        "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def depth(orders, venue):
    """按价格聚合剩余量，返回 [(price, qty)] 按价降序"""
    agg = defaultdict(int)
    for o in orders:
        if o["venue"] == venue:
            agg[int(o["priceWei"]) / WAD] += int(o["remaining"])
    return sorted(agg.items(), reverse=True)


def wavg(items, n=TOP_N, min_qty=MIN_QTY):
    """前 n 档加权均价；不足 min_qty 返回 None"""
    usable = [x for x in items if x[1] >= min_qty]
    s = usable[:n]
    tot = sum(q for _, q in s)
    if not tot:
        return None, 0
    return sum(p * q for p, q in s) / tot, tot


def scan():
    alerts = []
    lines = []
    for name, trans in OFFICIAL_MARKETS:
        for tid, sym in TOKENS:
            try:
                book = get(f"/v1/book/{trans}/{tid}")
            except Exception as e:
                lines.append(f"  {name}/{sym}: API失败 {str(e)[:60]}")
                continue
            if book.get("stale"):
                continue
            ob, ob_qty = wavg(depth(book["bids"], "official"))
            fb, fb_qty = wavg(depth(book["bids"], "ours"))
            if ob is None or fb is None or ob <= 0:
                continue
            gross_bps = (fb - ob) / ob * 10_000
            net_bps = gross_bps - FEE_BPS
            lines.append(
                f"  {name}/{sym}: 官方买 {ob:.6f}x{ob_qty:.0f} | "
                f"Firsto买 {fb:.6f}x{fb_qty:.0f} | 毛差 {gross_bps:+.0f}bps | 净 {net_bps:+.0f}bps")
            if net_bps >= ALERT_BPS:
                value = min(ob_qty, fb_qty) * ob
                if value >= MIN_VALUE_BNB:
                    alerts.append(
                        f"🚨 TapeOut {name}/{sym} 跨市场价差 {net_bps:.0f}bps "
                        f"(官方收 {ob:.6f} → Firsto 卖 {fb:.6f}, 可成交 {min(ob_qty, fb_qty):.0f}个 ≈ {value:.2f} BNB)")
    return alerts, lines


def main():
    once = "--once" in sys.argv
    alerts, lines = scan()
    if once:
        print("\n".join(lines))
        print(f"\n[扫描完成 {len(lines)} 行 | 报警 {len(alerts)}]")
        if alerts:
            print("\n".join(alerts))
    else:
        # watchdog 模式：非空 stdout 才推送
        if alerts:
            print(f"TapeOut 跨市场价差 @ {datetime.datetime.now():%m-%d %H:%M}")
            print("\n".join(alerts))
        # debug 日志到 stderr 不推送
        if len(lines) < 8:
            print("⚠️ 扫描异常：市场数据不足", file=sys.stderr)


if __name__ == "__main__":
    import datetime
    main()
