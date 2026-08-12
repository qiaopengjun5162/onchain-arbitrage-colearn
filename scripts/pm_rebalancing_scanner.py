#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PM Rebalancing Scanner v1.1（2026-08-12）
========================================
Polymarket「Market Rebalancing Arbitrage」盘口级扫描器。

口径（与 arXiv 2508.03474 的区别 = 本脚本的核心价值）：
- 论文用「成交 VWAP 均价」检测 ΣYES≠1 —— 跨过盘口价差，高估可捕获性
  （Helios 127 已证明 CLOB 是硬镜像：YES_ask+NO_ask ≥ 1+spread）
- 本脚本扫「盘口可执行组合」：YES 最优 ask 之和（Long）/ YES 最优 bid 之和（Short），
  扣 taker 费、要求容量 ≥ 最小下单量，才出信号 —— 扫得到 = 吃得到 才算数。

数据源：Gamma /markets（紧凑、快；/events 嵌套 128 个 markets 太重，弃用）。
分组：negRiskMarketID 相同的 market = 互斥候选集（如温度区间、候选人）；
      negRisk=false 的单 market = 单条件（天气单日 YES/NO 类）。

哲学（Paxon 天气市场教训，2026-08-12 群聊）：
- rebalancing 是一次性策略：建仓即持有到结算，不需要平仓、不需要止损
  —— 与「在 PM 只做一次性策略」原则天然一致。
- 只读扫描 + 人扣扳机；官方改规则最多让扫描结果变空，不会让脚本亏钱。
- 幽灵订单警示：最佳档位 size 异常大（≥1000 股且 ≥10× 次档）标记 suspect_wall，
  盘口定价因子可能被扭曲 —— 信号降级为观察，不直接可用。
- 结算口径朝令夕改（如「某一刻价格 → 30s TWAP」）不影响本脚本：
  binary outcome 结算仍按 YES/NO，rebalancing 持有到结算，与结算时点无关。

用法：
  python3 scripts/pm_rebalancing_scanner.py [--max-markets 300] [--min-profit 0.02] [--loop 0]

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

FEE_RATE = 0.07          # taker 费系数默认：size × rate × p × (1-p)（crypto 类 0.07）
MIN_PROFIT = 0.02        # 每 $1 名义的最小净利（论文下限 $0.05，这里放宽到 $0.02 便于观察）
MIN_SHARES = 20          # 最小可执行容量（股）
MAX_MARKETS = 300        # 最多拉取的 market 数（分页，每页 100）
TIME_BUDGET = 100        # 全局时间预算（秒）
LOG_PATH = "data/pm_rebalancing_scan.jsonl"


def get(url, retries=2, timeout=15):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pm-rebal-scan/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == retries:
                raise
            time.sleep(1.0 * (i + 1))


def fetch_book(token_id):
    """book 请求：短超时 + 少重试（404 的 token 快速失败，别拖慢整轮）。"""
    return get(f"{CLOB}/book?token_id={token_id}", retries=1, timeout=8)


def fetch_markets(max_markets):
    """分页拉活跃 market（紧凑字段），按 volume 降序。"""
    out, offset = [], 0
    while len(out) < max_markets:
        q = urllib.parse.urlencode({
            "active": "true", "closed": "false",
            "order": "volume", "ascending": "false",
            "limit": "100", "offset": str(offset),
        })
        page = get(f"{GAMMA}/markets?{q}", timeout=25)
        if not page:
            break
        out.extend(page)
        offset += 100
        if len(page) < 100:
            break
    return out[:max_markets]


def taker_fee_per_share(price, rate=FEE_RATE):
    """单腿每股 taker 费 = rate × p × (1-p)。"""
    p = float(price)
    return rate * p * (1 - p)


def best_level(book):
    """book -> (top_bid(price,size), top_ask(price,size), top3)。bids 降序、asks 升序。"""
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    top_bid = (float(bids[0]["price"]), float(bids[0]["size"])) if bids else (0.0, 0.0)
    top_ask = (float(asks[0]["price"]), float(asks[0]["size"])) if asks else (1.0, 0.0)
    return top_bid, top_ask


def wall_flag(book, threshold_size=1000.0, ratio=10.0):
    """幽灵订单启发式：最佳档 size 巨大且远超次档 → suspect_wall。"""
    for side in ((book.get("bids") or []), (book.get("asks") or [])):
        if len(side) >= 2:
            s0 = float(side[0]["size"])
            s1 = float(side[1]["size"])
            if s0 >= threshold_size and (s1 <= 0 or s0 / s1 >= ratio):
                return True
    return False


def market_fee_rate(m):
    """按市场实际费率（feesEnabled/takerBaseFee），缺省 FEE_RATE。"""
    try:
        if m.get("feesEnabled"):
            return float(m.get("takerBaseFee") or FEE_RATE)
    except (TypeError, ValueError):
        pass
    return FEE_RATE


def scan_single(market, token_ids):
    """单条件（天气类）：YES+NO 与 1 的偏差。"""
    yes_book = fetch_book(token_ids[0])
    no_book = fetch_book(token_ids[1])
    (y_bid_p, y_bid_s), (y_ask_p, y_ask_s) = best_level(yes_book)
    (n_bid_p, n_bid_s), (n_ask_p, n_ask_s) = best_level(no_book)
    rate = market_fee_rate(market)
    wall = wall_flag(yes_book) or wall_flag(no_book)

    long_gross = 1.0 - (y_ask_p + n_ask_p)
    long_fee = taker_fee_per_share(y_ask_p, rate) + taker_fee_per_share(n_ask_p, rate)
    long_net = long_gross - long_fee
    long_cap = min(y_ask_s, n_ask_s)

    short_gross = (y_bid_p + n_bid_p) - 1.0
    short_fee = taker_fee_per_share(y_bid_p, rate) + taker_fee_per_share(n_bid_p, rate)
    short_net = short_gross - short_fee
    short_cap = min(y_bid_s, n_bid_s)

    return {
        "type": "single", "question": market.get("question"),
        "yes": (y_bid_p, y_ask_p), "no": (n_bid_p, n_ask_p),
        "long": (long_gross, long_net, long_cap), "short": (short_gross, short_net, short_cap),
        "wall": wall,
    }


def scan_set(group_id, markets):
    """互斥候选集：ΣYES 与 1 的偏差（每腿拉 YES book）。"""
    legs = []
    for m in markets:
        tids = json.loads(m["clobTokenIds"])
        legs.append((m, fetch_book(tids[0])))  # YES 侧

    sum_ask = sum(best_level(b)[1][0] for _, b in legs)
    sum_bid = sum(best_level(b)[0][0] for _, b in legs)
    caps_ask = [best_level(b)[1][1] for _, b in legs]
    caps_bid = [best_level(b)[0][0] and best_level(b)[0][1] or 0 for _, b in legs]
    caps_bid = [best_level(b)[0][1] for _, b in legs]
    n = len(legs)
    rate = market_fee_rate(markets[0])

    long_gross = 1.0 - sum_ask
    long_fee = sum(taker_fee_per_share(best_level(b)[1][0], rate) for _, b in legs)
    long_net = long_gross - long_fee
    long_cap = min(caps_ask)

    short_gross = sum_bid - 1.0
    short_fee = sum(taker_fee_per_share(best_level(b)[0][0], rate) for _, b in legs)
    short_net = short_gross - short_fee
    short_cap = min(caps_bid)

    return {
        "type": "set", "n": n, "group_id": group_id[:18],
        "sum_ask": sum_ask, "sum_bid": sum_bid,
        "long": (long_gross, long_net, long_cap), "short": (short_gross, short_net, short_cap),
        "wall": any(wall_flag(b) for _, b in legs),
    }


def decide(res, min_profit, min_shares):
    for label in ("long", "short"):
        gross, net, cap = res[label]
        if net >= min_profit and cap >= min_shares:
            return label.upper(), round(net * 100, 2), cap, ""
    best = max(res["long"][1], res["short"][1])
    if best < 0:
        reason = "negative_after_fee"
    elif best < min_profit:
        reason = "below_min_profit"
    else:
        reason = "too_shallow"
    return "NONE", round(best * 100, 2), max(res["long"][2], res["short"][2]), reason


def main():
    max_markets, min_profit, min_shares, loop = MAX_MARKETS, MIN_PROFIT, MIN_SHARES, 0
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--max-markets" and i + 1 < len(args):
            max_markets = int(args[i + 1])
        elif a == "--min-profit" and i + 1 < len(args):
            min_profit = float(args[i + 1])
        elif a == "--loop" and i + 1 < len(args):
            loop = int(args[i + 1])

    while True:
        run_once(max_markets, min_profit, min_shares)
        if loop <= 0:
            break
        time.sleep(loop)


def run_once(max_markets, min_profit, min_shares):
    print(f"== PM rebalancing scan {time.strftime('%Y-%m-%d %H:%M:%S')} ==")
    deadline = time.time() + TIME_BUDGET
    try:
        markets = fetch_markets(max_markets)
    except Exception as e:
        print("  fetch markets failed:", e)
        return
    print(f"  markets fetched: {len(markets)}")

    # 分组：negRisk → 按 negRiskMarketID；否则单条件
    groups = {}
    for m in markets:
        if m.get("negRisk") and m.get("negRiskMarketID"):
            gid = m["negRiskMarketID"]
            groups.setdefault(gid, []).append(m)
        else:
            groups.setdefault("SINGLE:" + str(m.get("id")), [m])
    print(f"  groups: {len(groups)}")

    hits, scanned, skipped = [], 0, 0
    for gid, ms in groups.items():
        if time.time() > deadline:
            print("  [time budget exceeded, stopping]")
            break
        try:
            if gid.startswith("SINGLE"):
                m = ms[0]
                tids = json.loads(m["clobTokenIds"])
                if len(tids) < 2:
                    continue
                res = scan_single(m, tids)
                label = m.get("question") or m.get("slug")
            else:
                if len(ms) > 12:
                    skipped += 1
                    continue
                res = scan_set(gid, ms)
                label = f"[set x{len(ms)}] " + (ms[0].get("slug") or gid[:24])
            scanned += 1
        except Exception:
            continue

        sig, net, cap, reason = decide(res, min_profit, min_shares)
        if sig != "NONE":
            hits.append((label, res, sig, net, cap))
        log = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "label": label, "type": res["type"],
            "long_gross_bps": round(res["long"][0] * 10000), "long_net_bps": round(res["long"][1] * 10000),
            "short_gross_bps": round(res["short"][0] * 10000), "short_net_bps": round(res["short"][1] * 10000),
            "capacity": max(res["long"][2], res["short"][2]), "wall": res.get("wall", False),
            "decision": sig, "reject_reason": reason,
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")

    print(f"  signals: {len(hits)}  (scanned {scanned}, skipped big sets {skipped})")
    for label, res, sig, net, cap in hits:
        wall = " ⚠️wall" if res.get("wall") else ""
        print(f"  [{sig}] {label}  net={net}bps cap~{cap:.0f}sh{wall}")
        if res["type"] == "set":
            print(f"        ΣYES_ask={res['sum_ask']:.4f} ΣYES_bid={res['sum_bid']:.4f} n={res['n']}")
        else:
            print(f"        Y({res['yes'][0]:.3f}/{res['yes'][1]:.3f}) N({res['no'][0]:.3f}/{res['no'][1]:.3f})")


if __name__ == "__main__":
    main()
