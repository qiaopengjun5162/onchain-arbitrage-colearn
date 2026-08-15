"""
[DEPRECATED 2026-08-15] 手动扫描器，非持续监控；whale_dump_radar 承担持续监控（2026-08-15 体检）
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同构猎物雷达 v1 (prey_radar.py)
扫描 Morpho Blue 市场，找出与 sNUSD 案例同构的「埋雷」市场：
非官方 + 高 LTV + 利用率打满/异常 + 易去锚抵押品

数据源：
  - Morpho 官方 GraphQL API (blue-api.morpho.org/graphql) —— 全市场清单
  - publicnode RPC eth_call —— oracle.price()
  - (可选) GeckoTerminal —— 抵押品 DEX spot 价 → deviation 计算

用法：
  prey_radar.py --scan          全市场扫描，输出高危特征清单（默认）
  prey_radar.py --deviation     对候选市场计算 oracle vs DEX 偏差（需网络通）

输出：stdout 人话版 + data/prey_radar_YYYYMMDD.jsonl（追加）
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from eth_hash.auto import keccak

# ---------- 常量 ----------
GRAPHQL_URL = "https://blue-api.morpho.org/graphql"
RPC_URL = "https://ethereum-rpc.publicnode.com"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SEL_PRICE = "0x" + keccak(b"price()")[:4].hex()  # oracle.price()

# 高危特征阈值（基于 sNUSD 案例校准）
LLTV_MIN = 0.90        # 高抵押率（sNUSD 91.5%）
UTIL_MIN = 0.90        # 利用率打满（100% 冻结 = 第二信号）
STABLECOIN_SYMS = {"USDC", "USDT", "DAI", "USDE", "PYUSD", "FDUSD", "TUSD", "USDS"}

MARKETS_QUERY = """query {
  markets(first: 500, orderBy: SupplyAssetsUsd, orderDirection: Desc) {
    items {
      marketId
      listed
      lltv
      oracle { address }
      loanAsset { address symbol decimals }
      collateralAsset { address symbol decimals }
      state { utilization supplyAssetsUsd borrowAssetsUsd liquidityAssetsUsd }
    }
  }
}"""


# ---------- 网络 ----------
def http_post(url, payload, headers, timeout=40):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def graphql_markets():
    d = http_post(GRAPHQL_URL, {"query": MARKETS_QUERY},
                  {"Content-Type": "application/json", "User-Agent": "curl/8"})
    return d["data"]["markets"]["items"]


def rpc_call(to, data):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": to, "data": data}, "latest"]}).encode()
    req = urllib.request.Request(RPC_URL, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read().decode())
    res = out.get("result")
    return int(res, 16) if res else None


def oracle_price(oracle_addr, loan_dec, coll_dec):
    """返回 float 价格（loan asset 计价）。Morpho 刻度公式：
    raw = price × 10^(36 + loanDec - collDec)，故 price = raw / 10^(36+loanDec-collDec)"""
    v = rpc_call(oracle_addr, SEL_PRICE)
    if v is None:
        return None
    scale = 36 + loan_dec - coll_dec
    return v / (10 ** scale)


def gecko_spot(symbol, addresses):
    """可选：GeckoTerminal 按地址查 USD 价。网络不通返回 None。"""
    try:
        addr_list = ",".join(a for a in addresses[:3])
        url = f"https://api.geckoterminal.com/api/v2/simple/networks/ethereum/token_price/{addr_list}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        prices = d.get("data", {}).get("attributes", {}).get("token_prices", {})
        return prices
    except Exception:
        return None


# ---------- 特征判断 ----------
def is_yieldlike(sym):
    """衍生/质押/锚定类抵押品启发式"""
    s = sym.lower()
    return any(k in s for k in ("st", "s-", "snusd", "susd", "sdeusd", "susde", "ethx",
                                "oseth", "pt-", "paxt", "paxg", "bond", "k-", "solv",
                                "unibtc", "cbeth", "steth", "weeth", "rseth"))


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def classify(m):
    state = m.get("state") or {}
    coll = m.get("collateralAsset") or {"symbol": "?", "address": "?", "decimals": 18}
    loan = m.get("loanAsset") or {"symbol": "?", "address": "?", "decimals": 18}
    lltv = to_float(m.get("lltv")) / 1e18
    util = to_float(state.get("utilization"))
    listed = m.get("listed", False)
    flags = []
    if not listed:
        flags.append("非官方")
    if lltv >= LLTV_MIN:
        flags.append(f"高LTV {lltv*100:.1f}%")
    if util >= UTIL_MIN:
        flags.append(f"利用率{util*100:.0f}%")
    if is_yieldlike(coll["symbol"]):
        flags.append("衍生/锚定抵押品")
    if coll["symbol"] in STABLECOIN_SYMS:
        flags.append("稳定币抵押")
    return lltv, util, flags


# ---------- 主流程 ----------
def scan(do_deviation=False):
    markets = graphql_markets()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    print(f"🔍 Morpho 全市场扫描 @ {ts} | 共 {len(markets)} 个市场\n")

    # 1) 高危特征筛选（按 collateral+loan 去重，保留流动性最高）
    cands = []
    seen = {}
    for m in markets:
        lltv, util, flags = classify(m)
        listed = m.get("listed", False)
        coll = (m.get("collateralAsset") or {}).get("symbol", "?")
        loan = (m.get("loanAsset") or {}).get("symbol", "?")
        # 候选：非官方 + 高LTV + (利用率高 或 衍生抵押品)
        if (not listed and lltv >= LLTV_MIN and (util >= UTIL_MIN or is_yieldlike(coll))):
            key = f"{coll}->{loan}"
            liq = to_float((m.get("state") or {}).get("liquidityAssetsUsd"))
            if key not in seen or liq > seen[key][0]:
                seen[key] = (liq, (m, lltv, util, flags))
    cands = [v[1] for v in seen.values()]
    cands.sort(key=lambda x: -x[2])  # 利用率降序

    print(f"🎯 高危特征候选：{len(cands)} 个\n")
    for m, lltv, util, flags in cands:
        listed = m.get("listed", False)
        coll = (m.get("collateralAsset") or {}).get("symbol", "?")
        loan = (m.get("loanAsset") or {}).get("symbol", "?")
        coll_dec = (m.get("collateralAsset") or {}).get("decimals", 18)
        loan_dec = (m.get("loanAsset") or {}).get("decimals", 18)
        oaddr = (m.get("oracle") or {}).get("address", "")
        state = m.get("state") or {}
        # oracle 价（只对稳定币抵押/衍生类算，避免海量调用）
        oprice = None
        spot = None
        if do_deviation or coll in STABLECOIN_SYMS or is_yieldlike(coll):
            try:
                oprice = oracle_price(oaddr, loan_dec, coll_dec)
            except Exception:
                oprice = None
        row = {
            "ts": ts,
            "market": m["marketId"],
            "collateral": coll,
            "loan": loan,
            "lltv": lltv,
            "utilization": util,
            "listed": listed,
            "oracle": oaddr,
            "flags": "|".join(flags),
            "supply_usd": to_float(state.get("supplyAssetsUsd")),
            "liquidity_usd": to_float(state.get("liquidityAssetsUsd")),
            "oracle_price": oprice,
        }
        rows.append(row)
        spot_str = ""
        if oprice is not None:
            spot_str = f" | oracle价={oprice:.6g}"
            # 稳定币抵押类：oracle 偏离锚 1.0 提示（埋雷信号）
            if coll in STABLECOIN_SYMS or "USD" in coll.upper():
                dev_anchor = abs(oprice - 1.0)
                if dev_anchor > 0.02:
                    spot_str += f" ⚠️oracle偏离$1锚 {dev_anchor*100:.1f}%"
        print(f"  {'🔴' if util >= 0.99 else '🟡'} {coll} → {loan} "
              f"[{', '.join(flags)}]{spot_str} | 流动池 ${row['liquidity_usd']/1e6:.2f}M")

    # 2) deviation 计算（可选）
    if do_deviation and cands:
        print("\n📐 oracle vs DEX 偏差（GeckoTerminal，网络可用时）")
        for m, lltv, util, flags in cands:
            coll = (m.get("collateralAsset") or {}).get("symbol", "?")
            oaddr = (m.get("oracle") or {}).get("address", "")
            coll_dec = (m.get("collateralAsset") or {}).get("decimals", 18)
            loan_dec = (m.get("loanAsset") or {}).get("decimals", 18)
            oprice = oracle_price(oaddr, loan_dec, coll_dec)
            if not oprice:
                continue
            spots = gecko_spot(coll, [(m.get("collateralAsset") or {}).get("address", "")])
            if spots:
                for addr, p in spots.items():
                    dev = abs(oprice - p) / oprice
                    line = f"  {coll}: oracle={oprice:.4f} spot={p:.4f} deviation={dev*100:.1f}%"
                    line += " 🔴" if dev > 0.10 else (" 🟠" if dev > 0.05 else (" 🟡" if dev > 0.02 else " ✅"))
                    print(line)

    # 3) 落盘
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    outfile = DATA_DIR / f"prey_radar_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    with open(outfile, "a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n💾 落盘 {outfile}（追加 {len(rows)} 行）")


if __name__ == "__main__":
    do_dev = "--deviation" in sys.argv
    try:
        scan(do_dev)
    except Exception as e:
        print(f"❌ 失败: {e}")
        sys.exit(1)
