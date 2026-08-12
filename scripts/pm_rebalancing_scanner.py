#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PM Rebalancing Scanner v1（2026-08-12）
=====================================
Polymarket「Market Rebalancing Arbitrage」盘口级扫描器原型。

口径（与 arXiv 2508.03474 的区别 = 本脚本的核心价值）：
- 论文用「成交 VWAP 均价」检测 ΣYES≠1 —— 跨过盘口价差，高估可捕获性
  （Helios 127 已证明 CLOB 是硬镜像：YES_ask+NO_ask ≥ 1+spread）
- 本脚本扫「盘口可执行组合」：YES 最优 ask 之和（Long）/ YES 最优 bid 之和（Short），
  扣 taker 费、要求容量 ≥ 最小下单量，才出信号 —— 扫得到 = 吃得到 才算数。

哲学（Paxon 天气市场教训）：
- rebalancing 是一次性策略：建仓即持有到结算，不需要平仓、不需要止损
  —— 与「在 PM 只做一次性策略」原则天然一致。
- 只读扫描 + 人扣扳机；官方改规则最多让扫描结果变空，不会让脚本亏钱。
- 幽灵订单警示：最佳档位 size 异常大（≥1000 股且 ≥10× 次档）标记 suspect_wall，
  盘口定价因子可能被扭曲 —— 信号降级为观察，不直接可用。

用法：
  uv run --with requests python scripts/pm_rebalancing_scanner.py [--max-events 100] [--min-profit 0.02] [--loop 0]
  （或 hermes venv python；本脚本只用标准库，无第三方依赖）

输出：
  stdout 表格 + data/pm_rebalancing_scan.jsonl 追加审计日志（033 状态机风格：每条带决策与拒绝原因）
"""

import json
import sys
import time
import urllib.request
import urllib.parse

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

FEE_RATE = 0.07          # taker 费系数：size × rate × p × (1-p)（crypto 类 0.07，可配置）
MIN_PROFIT = 0.02        # 每 $1 名义的最小净利（论文下限 $0.05，这里放宽到 $0.02 便于观察）
MIN_SHARES = 20          # 最小可执行容量（股）
MAX_EVENTS = 100
LOG_PATH = "data/pm_rebalancing_scan.jsonl"


def get(url, retries=2, timeout=20):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pm-rebal-scan/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries:
                raise
            time.sleep(1.5 * (i + 1))


def fetch_book(token_id):
    """book 请求：短超时 + 少重试（404 的 token 快速失败，别拖慢整轮）。"""
    return get(f"{CLOB}/book?token_id={token_id}", retries=1, timeout=8)


def fetch_events(limit=MAX_EVENTS):
    """按 volume 取活跃事件（含 markets 数组）。"""
    q = urllib.parse.urlencode({
        "active": "true", "closed": "false",
        "order": "volume", "ascending": "false", "limit": limit,
    })
    return get(f"{GAMMA}/events?{q}")


def taker_fee_per_share(price):
    """单腿每股 taker 费 = rate × p × (1-p)。"""
    p = float(price)
    return FEE_RATE * p * (1 - p)


def best_level(book):
    """book -> (best_price, best_size, top3)。bids 降序、asks 升序。"""
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    top_bid = (float(bids[0]["price"]), float(bids[0]["size"])) if bids else (0.0, 0.0)
    top_ask = (float(asks[0]["price"]), float(asks[0]["size"])) if asks else (1.0, 0.0)
    top3 = {
        "bid3": [(float(b["price"]), float(b["size"])) for b in bids[:3]],
        "ask3": [(float(a["price"]), float(a["size"])) for a in asks[:3]],
    }
    return top_bid, top_ask, top3


def wall_flag(book, threshold_size=1000.0, ratio=10.0):
    """幽灵订单启发式：最佳档 size 巨大且远超次档 → suspect_wall。"""
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    for side in (bids, asks):
        if len(side) >= 2:
            s0 = float(side[0]["size"])
            s1 = float(side[1]["size"])
            if s0 >= threshold_size and (s1 <= 0 or s0 / s1 >= ratio):
                return True
    return False


def scan_single(market, token_ids):
    """单条件（含天气类）：YES+NO 与 1 的偏差。"""
    yes_book = fetch_book(token_ids[0])
    no_book = fetch_book(token_ids[1])
    (y_bid_p, y_bid_s), (y_ask_p, y_ask_s), _ = best_level(yes_book)
    (n_bid_p, n_bid_s), (n_ask_p, n_ask_s), _ = best_level(no_book)
    wall = wall_flag(yes_book) or wall_flag(no_book)

    # Long: 买 YES@ask + NO@ask，总成本 < 1 → 净利 = 1 - (y_ask+n_ask) - fees
    long_gross = 1.0 - (y_ask_p + n_ask_p)
    long_fee = taker_fee_per_share(y_ask_p) + taker_fee_per_share(n_ask_p)
    long_net = long_gross - long_fee
    long_cap = min(y_ask_s, n_ask_s)

    # Short: 1 USDC Split 得 YES+NO，按 bid 全卖 → 净利 = (y_bid+n_bid) - 1 - fees
    short_gross = (y_bid_p + n_bid_p) - 1.0
    short_fee = taker_fee_per_share(y_bid_p) + taker_fee_per_share(n_bid_p)
    short_net = short_gross - short_fee
    short_cap = min(y_bid_s, n_bid_s)

    return {
        "type": "single", "question": market.get("question"),
        "yes": (y_bid_p, y_ask_p), "no": (n_bid_p, n_ask_p),
        "long": (long_gross, long_net, long_cap), "short": (short_gross, short_net, short_cap),
        "wall": wall,
    }


def scan_set(event, markets):
    """NegRisk 多条件集：ΣYES 与 1 的偏差（需要 n 个 YES book）。"""
    legs = []
    for m in markets:
        token_ids = json.loads(m["clobTokenIds"])
        book = fetch_book(token_ids[0])  # YES 侧
        legs.append({"market": m, "book": book})

    sum_ask = sum(float(best_level(l["book"])[1][0]) for l in legs)   # Σ best YES ask
    sum_bid = sum(float(best_level(l["book"])[0][0]) for l in legs)   # Σ best YES bid
    caps_ask = [best_level(l["book"])[1][1] for l in legs]
    caps_bid = [best_level(l["book"])[0][1] for l in legs]
    walls = [wall_flag(l["book"]) for l in legs]
    n = len(legs)

    # Long: 买 n 个 YES，总成本 < 1
    long_gross = 1.0 - sum_ask
    long_fee = sum(taker_fee_per_share(best_level(l["book"])[1][0]) for l in legs)
    long_net = long_gross - long_fee
    long_cap = min(caps_ask)

    # Short: Split n 次后按 bid 卖 YES（等价 ΣNO_bid > n-1）
    short_gross = sum_bid - 1.0
    short_fee = sum(taker_fee_per_share(best_level(l["book"])[0][0]) for l in legs)
    short_net = short_gross - short_fee
    short_cap = min(caps_bid)

    return {
        "type": "set", "n": n, "event": event.get("title"),
        "sum_ask": sum_ask, "sum_bid": sum_bid,
        "long": (long_gross, long_net, long_cap), "short": (short_gross, short_net, short_cap),
        "wall": any(walls),
    }


def y_ask_size_of(book):
    return best_level(book)[1][1]


def n_ask_size_of(book):
    return best_level(book)[1][1]


def y_bid_size_of(book):
    return best_level(book)[0][1]


def n_bid_size_of(book):
    return best_level(book)[0][1]


def decide(res, min_profit, min_shares):
    for label in ("long", "short"):
        gross, net, cap = res[label]
        if net >= min_profit and cap >= min_shares:
            return label.upper(), round(net * 100, 2), cap, ""
    # 拒绝原因（结构化，供统计）
    best = max(res["long"][1], res["short"][1])
    if best < 0:
        reason = "negative_after_fee"
    elif best < min_profit:
        reason = "below_min_profit"
    else:
        reason = "too_shallow"
    return "NONE", round(max(res["long"][1], res["short"][1]) * 100, 2), max(res["long"][2], res["short"][2]), reason


def main():
    max_events = MAX_EVENTS
    min_profit = MIN_PROFIT
    min_shares = MIN_SHARES
    loop = 0
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--max-events" and i + 1 < len(args):
            max_events = int(args[i + 1])
        elif a == "--min-profit" and i + 1 < len(args):
            min_profit = float(args[i + 1])
        elif a == "--loop" and i + 1 < len(args):
            loop = int(args[i + 1])

    while True:
        run_once(max_events, min_profit, min_shares)
        if loop <= 0:
            break
        time.sleep(loop)


def run_once(max_events, min_profit, min_shares):
    print(f"== PM rebalancing scan {time.strftime('%Y-%m-%d %H:%M:%S')} ==")
    deadline = time.time() + 100  # 全局时间预算：100s 内扫不完就停
    try:
        events = fetch_events(max_events)
    except Exception as e:
        print("  fetch events failed:", e)
        return
    print(f"  events: {len(events)}")

    hits = []
    scanned = skipped = 0
    for ev in events:
        if time.time() > deadline:
            print("  [time budget exceeded, stopping]")
            break
        markets = ev.get("markets") or []
        if not markets:
            continue
        active_markets = [m for m in markets if m.get("active")]
        if not active_markets:
            continue
        if len(active_markets) > 12:
            skipped += 1
            continue
        try:
            if len(active_markets) == 1:
                m = active_markets[0]
                token_ids = json.loads(m["clobTokenIds"])
                if len(token_ids) < 2:
                    continue
                res = scan_single(m, token_ids)
            else:
                # 多条件事件：Gamma 的 marketType 经常为空字符串，不能当过滤条件。
                # 2-12 个活跃条件视为候选互斥集（assumed_set），>12 跳过（v1 容量上限）。
                if len(active_markets) > 12:
                    continue
                res = scan_set(ev, active_markets)
            scanned += 1
        except Exception:
            continue

        sig, net, cap, reason = decide(res, min_profit, min_shares)
        if sig != "NONE":
            hits.append((ev, res, sig, net, cap))
        # 审计日志
        log = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": ev.get("title"), "type": res["type"],
            "long_gross_bps": round(res["long"][0] * 10000), "long_net_bps": round(res["long"][1] * 10000),
            "short_gross_bps": round(res["short"][0] * 10000), "short_net_bps": round(res["short"][1] * 10000),
            "capacity": max(res["long"][2], res["short"][2]), "wall": res.get("wall", False),
            "decision": sig, "reject_reason": reason,
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")

    print(f"  signals: {len(hits)}  (scanned {scanned}, skipped big sets {skipped})")
    for ev, res, sig, net, cap in hits:
        q = ev.get("title") or ev.get("slug")
        wall = " ⚠️wall" if res.get("wall") else ""
        print(f"  [{sig}] {q}  net={net}bps cap~{cap:.0f}sh{wall}")
        if res["type"] == "set":
            print(f"        ΣYES_ask={res['sum_ask']:.4f} ΣYES_bid={res['sum_bid']:.4f} n={res['n']}")
        else:
            print(f"        Y({res['yes'][0]:.3f}/{res['yes'][1]:.3f}) N({res['no'][0]:.3f}/{res['no'][1]:.3f})")


if __name__ == "__main__":
    main()
