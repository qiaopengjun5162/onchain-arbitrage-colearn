#!/usr/bin/env python3
"""
TapeOut 矿机线：组装套利扫描器（电路 721 vs 元件 1155）
==========================================================
2026-08-28 修正：电路市场其实有 REST 端点（昨天探 /v1/book 400 是因为路径不同）
- /v1/circuits?limit=N      电路列表（22K+ 条）：每行直接带 minAskBuyerCostWei / maxBidSellerNetWei /
                            bestAsk / bestBid / directNand / directLatch / directGateCount / classification
- /v1/circuit/{coll}/{tid}  电路详情：orders.asksAndOnchainBids + signedAsks + signedBids（bid pools）
- /v1/circuit-trades?limit=N 成交流（buyerCost/sellerNet/feeWei=1%）
- SSE /v1/stream/circuits   只是 generation/健康心跳（sequence/generationId/sourceFreshness），无订单数据

组装套利逻辑（用户大头线，08-27 笔记）：
- 矿机 = NAND + LATCH 元件按 netlist 组装 + 流片
- 元件成本 = directNand×NAND价 + directLatch×LATCH价（官方市场 book，买家即时吃单用 ask，慢收用 bid）
- 矿机卖价 = minAskBuyerCostWei（最便宜签名卖单，买家成本）
- 组装溢价 bps = (矿机卖价 − 元件成本) / 矿机卖价 × 10000 —— 正且大 = 卖矿机者利润空间 / 元件相对低估

用法：
- 手动: python3 scripts/circuit_assembly_scan.py --once [--pages 2]
- cron watchdog: 无报警静默（stdout 空），组装溢价超阈值才输出 → 由 cron 推送

阈值：
- 组装溢价 >= ALERT_BPS(1000=10%) 且矿机价 >= MIN_VALUE_BNB(0.1) 才报警
"""
import json
import sys
import time
import datetime
import urllib.request

API = "https://api-tapeout.firsto.ai"
WAD = 10**18

# 官方 5 市场（transistors 合约地址，与 firsto_cross_market_scan.py 一致）
OFFICIAL_MARKETS = {
    "TapeOut":       "0xCC42ba5De07f01B472a5b14cF45aBcCA79Eb8087",
    "Genesis CPU":   "0x1d23Bf70ec6bAAD95f396Ea38f8A8415119dFDE6",
    "Blonskr_No1":   "0xE2DfD802081C7a05341E20b6582b04b908e8550c",
    "Bitcoin Miner": "0x140FDD905849a49064f8d366ABE7b21Ff83DAFB5",
    "RefBench":      "0xB645572D56E81ca2844fA833ad14f146a10e8330",
}
# 官方挖矿家族（bundle 里 $I set）
MINING_FAMILIES = {"tapeout", "behemoth", "genesis cpu"}
COMPONENT_MARKET = "TapeOut"   # 元件价基准市场（最活跃；v1 用单一市场，后续可按 processor 映射）

ALERT_BPS = 1000        # 组装溢价 >= 10% 报警
MIN_VALUE_BNB = 0.1     # 矿机价下限（BNB，防灰尘级）
TOP_N = 5               # 输出表格条数
PAGES = 1               # --once 默认扫 1 页 (50 条)
TAPEOUT_FEE_BNB = 0.05  # 流片费（链上机制，暂配置值，待核验）


def get(path, proxy=True, timeout=25):
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


def book_levels(market_addr, token_id):
    """返回 (best_ask, best_bid, ask_n) — 元件官方市场价（失败重试一次）"""
    b = None
    for _ in range(2):
        try:
            b = get(f"/v1/book/{market_addr}/{token_id}")
            break
        except Exception:
            time.sleep(1.5)
    if b is None:
        return None, None, 0
    best_ask = best_bid = None
    for o in b.get("asks", []):
        p = int(o["priceWei"]) / WAD
        if best_ask is None or p < best_ask:
            best_ask = p
    for o in b.get("bids", []):
        p = int(o["priceWei"]) / WAD
        if best_bid is None or p > best_bid:
            best_bid = p
    return best_ask, best_bid, len(b.get("asks", []))


def scan(pages=PAGES):
    # 1. 元件价格
    mkt = OFFICIAL_MARKETS[COMPONENT_MARKET]
    nand_ask, nand_bid, nand_n = book_levels(mkt, 0)
    latch_ask, latch_bid, latch_n = book_levels(mkt, 1)
    if nand_ask is None and nand_bid is None:
        return [], f"元件行情失败({COMPONENT_MARKET} NAND)"
    px = f"元件价 {COMPONENT_MARKET}: NAND ask={nand_ask or 0:.6f}/bid={nand_bid or 0:.6f} " \
         f"LATCH ask={latch_ask or 0:.6f}/bid={latch_bid or 0:.6f}"

    # 2. 电路列表（分页）
    rows = []
    for page in range(1, pages + 1):
        try:
            d = get(f"/v1/circuits?limit=50&page={page}")
            rows += d.get("rows", [])
        except Exception as e:
            break
    if not rows:
        return [], "电路列表获取失败"

    # 3. 逐条算组装溢价
    alerts = []
    table: list[dict] = []
    for r in rows:
        if r.get("classification") != "official_mining":
            continue
        ask_w = int(r.get("minAskBuyerCostWei") or 0)
        if ask_w <= 0:
            continue
        try:
            dn = int(r.get("directNand") or 0)
            dl = int(r.get("directLatch") or 0)
        except (TypeError, ValueError):
            continue
        if dn == 0 and dl == 0:
            continue  # 递归电路，元件需求不明，跳过
        circ_ask = ask_w / WAD
        circ_bid = int(r.get("maxBidSellerNetWei") or 0) / WAD
        cost_ask = (dn * (nand_ask or 0) + dl * (latch_ask or 0)) + TAPEOUT_FEE_BNB
        cost_bid = (dn * (nand_bid or 0) + dl * (latch_bid or 0)) + TAPEOUT_FEE_BNB
        margin_bps = (circ_ask - cost_ask) / circ_ask * 10_000 if circ_ask else 0
        # 可执行组装套利：现有买单价 vs 即时组装成本（买元件→组装→卖给当前买单）
        arb_bps = (circ_bid - cost_ask) / cost_ask * 10_000 if cost_ask and circ_bid else 0
        rec = {
            "token": f"{r.get('processorName')}#{r.get('tokenId')}",
            "nand": dn, "latch": dl,
            "ask": circ_ask, "bid": circ_bid,
            "cost_ask": cost_ask, "margin_bps": round(margin_bps, 1),
            "arb_bps": round(arb_bps, 1),
        }
        table.append(rec)
        # 主信号：买单支撑的即时组装套利（真买家 + 正利差）
        if circ_bid >= MIN_VALUE_BNB and arb_bps >= ALERT_BPS:
            alerts.append(
                f"🚨 组装套利(买单支撑) {arb_bps:.0f}bps: {rec['token']} "
                f"有人收 {circ_bid:.4f} vs 组装成本 {cost_ask:.4f} "
                f"({dn}NAND+{dl}LATCH+流片{TAPEOUT_FEE_BNB}) 利差 {circ_bid - cost_ask:+.4f} BNB")
        # 次信号：矿机挂价溢价（信息面，无买单=流动性陷阱，只记录不报警降噪）

    table.sort(key=lambda x: -x["margin_bps"])
    return alerts, px, table


def record_snapshot(px, table, alerts):
    """行情库：每次扫描落一行快照到 data/circuit_market.jsonl"""
    import os
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    top = table[:3] if table else []
    snap = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "px": px,
        "n_circuits": len(table),
        "top_margin_bps": [t["margin_bps"] for t in top],
        "top_arb_bps": [t["arb_bps"] for t in top],
        "n_alerts": len(alerts),
        "alerts": alerts[:5],
    }
    with open(os.path.join(data_dir, "circuit_market.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(snap, ensure_ascii=False) + "\n")


def main():
    pages = PAGES
    args = sys.argv[1:]
    if "--pages" in args:
        pages = int(args[args.index("--pages") + 1])
    once = "--once" in args

    alerts, *rest = scan(pages)
    if once:
        if len(rest) != 2:
            print("⚠️", rest[0] if rest else "扫描失败")
            return
        px, table = rest
        record_snapshot(px, table, alerts)
        print(px)
        print(f"\n[电路 {len(table)} 条 | 组装溢价 TOP{TOP_N}]")
        for t in table[:TOP_N]:
            print(f"  {t['token']:<22} 卖 {t['ask']:.4f} | 元件 {t['nand']}N+{t['latch']}L "
                  f"成本 {t['cost_ask']:.4f} | 溢价 {t['margin_bps']:+.0f}bps | 买单套利 {t['arb_bps']:+.0f}bps")
        print(f"\n[报警 {len(alerts)}]")
        if alerts:
            print("\n".join(alerts))
    else:
        # watchdog 模式：非空 stdout 才推送（行情库照常落盘）
        if len(rest) == 2:
            record_snapshot(rest[0], rest[1], alerts)
        if alerts:
            print(f"TapeOut 矿机组装套利 @ {datetime.datetime.now():%m-%d %H:%M}")
            print("\n".join(alerts))


if __name__ == "__main__":
    main()
