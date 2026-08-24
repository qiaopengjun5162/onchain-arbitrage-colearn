#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PM 5-min 涨跌盘双买套利扫描器（pm_binary_dual_buy.py）— 2026-08-24

背景（群分享 0xBinTang，2026-08-24）：
- Polymarket 5 分钟 BTC/ETH/SOL/XRP 涨跌盘：每窗口最终 Up 或 Down 赢，赢家每份兑 $1
- 双买 = 同时买 Up + Down：若 ask_Up + ask_Down < $1，哪边赢都锁差价（无需猜方向）
- 声称案例：Up 22.5¢ + Down 59.8¢ = 82.3¢ → 每对净赚 17.7¢；$5,440 万量/92,344 次/$588,548
  利润（转述未独立核验）——本脚本落地「可执行检测」：ask-ask 实价 + taker 费 + 容量门槛

口径（复用 pm_rebalancing_scanner 纪律）：
- 只看盘口可执行组合（ask 价 + 对应 size），不用 outcomePrices/midpoint（≠可成交）
- 扣 taker 费：每腿 0.07 × p × (1-p)（crypto 类费率，保守按 taker）
- 容量门槛：两腿最优 ask size ≥ MIN_SHARES；幽灵墙（≥1000 股且 ≥10× 次档）降级 suspect
- 只读扫描 + 人扣扳机；官方改规则最多让扫描结果变空

用法：
  python scripts/pm_binary_dual_buy.py              # 全表
  python scripts/pm_binary_dual_buy.py --quiet      # watchdog：仅信号

输出：stdout + data/pm_binary_dual_buy.jsonl
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

ASSETS = [("btc", "BTC"), ("eth", "ETH"), ("sol", "SOL"), ("xrp", "XRP")]
FEE_RATE = 0.07           # taker 费系数（crypto 0.07）：size × rate × p × (1-p)
MIN_PROFIT = 0.01         # 每 $1 名义最小净利（1¢）
MIN_SHARES = 20           # 最小可执行容量（股）
WALL_SHARES = 1000        # 幽灵墙判定：最优档 ≥1000 股且 ≥10× 次档
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "pm_binary_dual_buy.jsonl"
STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "pm_binary_dual_buy_state.json"


def get(url, retries=2, timeout=15):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pm-dualbuy/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == retries:
                return None
            time.sleep(1.0 * (i + 1))


def best_ask(token_id):
    """最优 ask：返回 (price, size, next_size) 或 None。"""
    b = get(f"{CLOB}/book?token_id={token_id}", retries=1, timeout=8)
    if not b or not b.get("asks"):
        return None
    asks = b["asks"]
    a0 = asks[0]
    p, s = float(a0["price"]), float(a0.get("size", 0))
    nxt = float(asks[1].get("size", 0)) if len(asks) > 1 else 0
    return p, s, nxt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="watchdog：仅净利达标的信号才输出")
    ap.add_argument("--window-epoch", type=int, default=0, help="指定窗口（默认当前 5min 窗口）")
    ap.add_argument("--history", type=int, default=0,
                    help="回看最近 N 个窗口（诊断信号频率；当前盘口已闭，ask 为最后状态）")
    args = ap.parse_args()

    now = int(time.time())
    win = args.window_epoch or ((now // 300) * 300)
    windows = [win - 300 * i for i in range(args.history + 1)][::-1] if args.history else [win]
    rows = []
    for w in windows:
        for slug, label in ASSETS:
            ev = get(f"{GAMMA}/events?slug={slug}-updown-5m-{w}")
            if not ev:
                continue
            m = (ev[0].get("markets") or [{}])[0]
            tokens = json.loads(m.get("clobTokenIds") or "[]")
            if len(tokens) < 2:
                continue
            up = best_ask(tokens[0])
            dn = best_ask(tokens[1])
            rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "window": w, "asset": label, "title": ev[0].get("title", "")[:50]}
            if not up or not dn:
                rec.update({"level": "no_book", "ask_up": None, "ask_dn": None, "net": None})
                rows.append(rec)
                continue
            p_up, s_up, n_up = up
            p_dn, s_dn, n_dn = dn
            combo = p_up + p_dn
            fee = FEE_RATE * p_up * (1 - p_up) + FEE_RATE * p_dn * (1 - p_dn)
            net = 1.0 - combo - fee
            # 容量：两腿最优档都够；幽灵墙降级
            wall = (s_up >= WALL_SHARES and s_up >= 10 * n_up) or (s_dn >= WALL_SHARES and s_dn >= 10 * n_dn)
            enough = s_up >= MIN_SHARES and s_dn >= MIN_SHARES
            rec.update({"ask_up": p_up, "ask_dn": p_dn, "size_up": s_up, "size_dn": s_dn,
                        "combo": round(combo, 4), "fee": round(fee, 4), "net": round(net, 4),
                        "level": "SIGNAL" if (net >= MIN_PROFIT and enough and not wall)
                                  else "suspect" if (net >= MIN_PROFIT and (not enough or wall))
                                  else "ok",
                        "wall": wall, "enough": enough})
            rows.append(rec)

    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with open(LOG_PATH, "a") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception:
        pass

    if args.quiet:
        # 窗口级去重：同一 (window, asset) 只报一次（cron 每 2min 扫同一窗口会重复命中）
        state = {}
        try:
            if STATE_PATH.exists():
                state = json.loads(STATE_PATH.read_text())
        except Exception:
            pass
        for r in rows:
            if r["level"] not in ("SIGNAL", "suspect"):
                continue
            key = f"{r['window']}:{r['asset']}"
            if key in state:
                continue
            state[key] = {"ts": time.time(), "level": r["level"]}
            if r["level"] == "SIGNAL":
                print(f"🚨 [PM 5min] {r['asset']} @窗口 {time.strftime('%H:%M', time.gmtime(r['window']))} "
                      f"Up {r['ask_up']:.3f} + Down {r['ask_dn']:.3f} = {r['combo']:.3f} "
                      f"净 {r['net']*100:.1f}¢/股（含 taker 费 {r['fee']*100:.1f}¢，容量 {r['size_up']:.0f}/{r['size_dn']:.0f} 股）")
            else:
                print(f"👀 [PM 5min] {r['asset']} 近信号: combo {r['combo']:.3f} net {r['net']*100:.1f}¢ "
                      f"enough={r['enough']} wall={r['wall']}")
        try:
            STATE_PATH.parent.mkdir(exist_ok=True)
            STATE_PATH.write_text(json.dumps(state))
        except Exception:
            pass
        return 0

    print(f"=== PM 5min 双买扫描 @ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC "
          f"窗口 {time.strftime('%H:%M', time.gmtime(win))}-{time.strftime('%H:%M', time.gmtime(win+300))} ===")
    print(f"{'币':<6}{'ask Up':>8}{'ask Dn':>8}{'合计':>8}{'taker费':>8}{'净¢/股':>8}{'容量':>6}{'级别':>10}")
    for r in rows:
        if r["level"] == "no_book":
            print(f"{r['asset']:<6} 无盘口")
            continue
        cap = f"{r['size_up']:.0f}/{r['size_dn']:.0f}" if r["enough"] else f"<{MIN_SHARES}"
        print(f"{r['asset']:<6}{r['ask_up']:>8.3f}{r['ask_dn']:>8.3f}{r['combo']:>8.3f}"
              f"{r['fee']:>8.3f}{r['net']*100:>8.1f}{cap:>6}{r['level']:>10}")
    sig = [r for r in rows if r["level"] == "SIGNAL"]
    print(f"\nSIGNAL {len(sig)} / suspect {sum(1 for r in rows if r['level']=='suspect')} / "
          f"ok {sum(1 for r in rows if r['level']=='ok')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
