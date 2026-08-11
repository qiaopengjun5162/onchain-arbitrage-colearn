#!/usr/bin/env python3
"""Backrun 薄池扫描器 v1（2026-08-11，research-backlog #13 落地 + backrun 模拟器升级）。

核心问题（#13 容量上限验证路径）：
    薄池「价差大但容量浅」——滑点在哪一档吃掉价差？那个档位就是容量边界。
    backrun 视角：受害交易砸穿薄池 → 价格扭曲 → backrun 者从正常池买入、薄池高价卖出。

方法：
    1. 多金额档（0.1/1/10/100/1000/5000 SOL）Jupiter quote 采样 → routePlan 各池腿
    2. 每池独立价格（outAmount/inAmount 实算，腿 inputMint==SOL 才有效）→ 与 Raydium 锚点价差 bps
    3. 每池滑点曲线：跨档价格变化 → 容量边界 = 滑点 ≥ THIN_IMPACT_BPS 的最小档（或路由拆腿点）
    4. backrun 模拟（恒定乘积）：受害交易砸穿薄池 → 扭曲倍数 → 正常池买入/薄池卖出的净利

输出（watchdog 语义）：
    - 默认：一页「低容量可行域」表（池 × 价差 × 容量边界 × backrun 可执行性）
    - --quiet：仅当发现「价差 > 滑点」的可执行薄池才输出（cron watchdog）
    - --json：机器可读

用法：
    python scripts/backrun_thin_pool_scanner.py
    python scripts/backrun_thin_pool_scanner.py --quiet        # watchdog
    python scripts/backrun_thin_pool_scanner.py --json
    python scripts/backrun_thin_pool_scanner.py --max-sol 5000 # 加大扫档
环境变量：PROXY（默认 http://127.0.0.1:7890）
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}

JUPITER_QUOTE = "https://api.jup.ag/swap/v1/quote"
HELIUS_RPC_TMPL = "https://mainnet.helius-rpc.com/?api-key={key}"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
# Raydium SOL-USDC v4 vault（no_arb_corridor_radar 同款，2026-08-11 校准）
SOL_VAULT = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
USDC_VAULT = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"

SAMPLES_SOL = [0.1, 1, 10, 100, 1000, 5000]
SAMPLES_USD = [10, 100, 1000, 10000, 50000]  # 长尾币按美元档扫（币数量档对低价币无意义）
THIN_IMPACT_BPS = 30      # 容量边界阈值：滑点 ≥30bps = 容量触顶
MIN_SPREAD_BPS = 10       # 价差 ≥10bps 才算「有价差可吃」（<10bps 是噪音）
SUSPECT_SPREAD_BPS = 5000 # 价差 >50% = 数据异常（decimals 错/假池/重计价），标 suspect 不算薄池
BACKRUN_FEE = 0.003       # AMM 费率（Raydium 0.30%，实测）
RETRY = 3
RETRY_WAIT = 3
TIMEOUT = 20

FEE_BPS = {  # 与 no_arb_corridor_radar 同表
    "Raydium": 30, "Orca": 30, "Whirlpool": 5, "Phoenix": 0,
    "OpenBook": 0, "Meteora": 5, "Meteora DLMM": 5, "HumidiFi": 30,
    "BisonFi": 30, "Aquifer": 30, "ZeroFi": 30, "Scorch": 30,
    "SolFi V2": 30, "Flux": 30, "TesseraV": 30, "Deriverse": 30,
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get_helius_key() -> str:
    """兜底：从 ~/.hermes/.env 读 key（cron/execute_code 不继承 shell env）。"""
    if os.environ.get("HELIUS_API_KEY"):
        return os.environ["HELIUS_API_KEY"]
    env_path = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export "):
                        line = line[7:]
                    if line.startswith("HELIUS_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def read_raydium_price() -> float:
    """Raydium SOL-USDC vault 直读 → 恒定乘积锚点价（雷达同款，最深处价格可信）。"""
    key = get_helius_key()
    if not key:
        return 0.0
    url = HELIUS_RPC_TMPL.format(key=key)
    try:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getTokenAccountBalance",
                   "params": [SOL_VAULT]}
        r = requests.post(url, json=payload, timeout=TIMEOUT, proxies=PROXIES)
        sol = r.json().get("result", {}).get("value", {}).get("uiAmount") or 0
        payload["params"] = [USDC_VAULT]
        r = requests.post(url, json=payload, timeout=TIMEOUT, proxies=PROXIES)
        usdc = r.json().get("result", {}).get("value", {}).get("uiAmount") or 0
        if sol and usdc:
            return usdc / sol
    except Exception:
        pass
    return 0.0


def quote_legs(amount, base_mint: str = SOL_MINT, base_decimals: int = 9,
               usd_mode: bool = False) -> list:
    """Jupiter quote 一档 → 池腿列表。

    - usd_mode=False（主流币）：inputMint=base（SOL），amount=币数量，price=USDC/base
    - usd_mode=True（长尾币）：inputMint=USDC，amount=美元金额（1e6），price=USDC/base
      只留 inputMint==USDC 的腿（第一跳），price = usdc_in / base_out。
    """
    if usd_mode:
        params = {"inputMint": USDC_MINT, "outputMint": base_mint,
                  "amount": int(amount * 1e6), "slippageBps": 300}
    else:
        params = {"inputMint": base_mint, "outputMint": USDC_MINT,
                  "amount": int(amount * 10 ** base_decimals), "slippageBps": 300}
    for attempt in range(RETRY):
        try:
            r = requests.get(JUPITER_QUOTE, params=params, timeout=TIMEOUT, proxies=PROXIES)
            if r.status_code == 429:
                time.sleep(RETRY_WAIT * (attempt + 1))
                continue
            d = r.json()
            break
        except Exception:
            if attempt == RETRY - 1:
                return []
            time.sleep(RETRY_WAIT * (attempt + 1))
    else:
        return []

    legs = []
    usdc_in = 0.0
    for step in d.get("routePlan", []):
        si = step.get("swapInfo", {})
        if not si:
            continue
        if usd_mode:
            # 完整路由可能是 USDC→中间币→base（如 BONK 走 USDC→SOL→BONK 两跳）。
            # 价格观察点 = 最后输出 base 的腿；price = 全部 USDC 输入 / base 总输出。
            if si.get("outputMint") != base_mint:
                continue
            # 该腿 outAmount 是 base 数量（可能只占总输出的一部分，但 routePlan 单腿
            # 输出即该池贡献；用整笔 quote 的 USDC 输入算价格会低估——用该腿输出 +
            # 整笔输入更接近「该池在该路由下的有效价」；v1 简化：price 用 outAmount
            base_out = int(si.get("outAmount", 0)) / 10 ** base_decimals
            if not base_out:
                continue
            # 该腿输入 = 中间币（如 SOL），不是美元——无法直接得 USDC/base。
            # 用整笔 quote 的 outAmount（base 总输出）与 outAmount/quote 总输入换算：
            # price = 美元总输入 / base 总输出（跨池平均，v1 可接受）
            total_out_raw = int(d.get("outAmount", 0))
            total_in_usd = 0.0
            for st in d.get("routePlan", []):
                s2 = st.get("swapInfo", {})
                if s2 and s2.get("inputMint") == USDC_MINT:
                    total_in_usd = int(s2.get("inAmount", 0)) / 1e6
            if not total_out_raw:
                continue
            base_total = total_out_raw / 10 ** base_decimals
            price = total_in_usd / base_total if base_total else 0.0
            inp = total_in_usd
            out = base_total
            usdc_in = total_in_usd
        else:
            if si.get("inputMint") != base_mint:
                continue  # 第二跳起输入是 USDC 等，非 base 价格观察点
            out = int(si.get("outAmount", 0)) / 1e6
            inp = int(si.get("inAmount", 0)) / 10 ** base_decimals
            if not inp:
                continue
            price = out / inp
        label = si.get("label", "?")
        legs.append({
            "pool": label,
            "sol_in": inp,
            "usdc_out": out,
            "price": price,
            "fee_bps": FEE_BPS.get(label, 30),
            "usd_notional": inp * (out / inp) if not usd_mode else usdc_in,
        })
    return legs


def simulate_backrun(thin_pool_price: float, normal_price: float, attack_usd: float,
                     thin_liq_usd: float, fee: float = BACKRUN_FEE) -> dict:
    """受害交易砸穿薄池 + backrun（复用 backrun_impact_sim 恒定乘积逻辑）。

    thin_liq_usd 是薄池双边流动性近似——从池腿名义量 + 冲击估计。
    """
    half = thin_liq_usd / 2.0
    asset_reserve = half / thin_pool_price   # 薄池资产数量（近似）
    quote_reserve = half                      # 薄池 USDC 数量
    k = asset_reserve * quote_reserve

    # 受害交易：attack_usd USDC 买入资产
    usdc_in = attack_usd
    new_quote = quote_reserve + usdc_in
    new_asset = k / new_quote
    asset_out = (asset_reserve - new_asset) * (1 - fee)
    if asset_out <= 0:
        return {"profit": -1e9, "distortion": 0, "victim_price": 0, "note": "池子被买穿"}
    victim_price = usdc_in / asset_out

    # backrun：正常池价买入 → 薄池卖出
    buy_qty = new_asset * 0.30
    cost = buy_qty * normal_price
    k2 = new_asset * new_quote
    out_usdc = (new_quote - k2 / (new_asset + buy_qty)) * (1 - fee)
    profit = out_usdc - cost
    return {
        "profit": profit,
        "distortion": victim_price / normal_price if normal_price else 0,
        "victim_price": victim_price,
        "note": "ok" if profit > 0 else "利润为负",
    }


def scan(max_sol: float, base_mint: str = SOL_MINT, base_decimals: int = 9,
         base_label: str = "SOL") -> dict:
    anchor = read_raydium_price() if base_mint == SOL_MINT else 0.0
    usd_mode = base_mint != SOL_MINT
    samples = SAMPLES_USD if usd_mode else [s for s in SAMPLES_SOL if s <= max_sol]

    # 1) 多档采样 → 池腿集合
    pool_legs = {}   # pool -> {size: {price, usd_notional}}
    pool_first_size = {}
    for amt in samples:
        legs = quote_legs(amt, base_mint, base_decimals, usd_mode)
        for leg in legs:
            pool_legs.setdefault(leg["pool"], {})[amt] = leg
            pool_first_size.setdefault(leg["pool"], amt)

    # 2) 每池：锚点价差 + 滑点曲线 + 容量边界
    # 容量边界只认「滑点冲击 ≥THIN_IMPACT_BPS」——价格冲击是硬证据；
    # Jupiter 大档拆多腿 ≠ 容量触顶（可能是最优路由比例），不算容量信号。
    # 锚点：SOL 用 Raydium 直读；长尾币用「全池首档价中位数」（无单一权威锚点）。
    pools = []
    first_prices = [legs_by_size[sorted(legs_by_size)[0]]["price"]
                    for legs_by_size in pool_legs.values()]
    median_first = sorted(first_prices)[len(first_prices) // 2] if first_prices else 0.0
    for pool, legs_by_size in sorted(pool_legs.items()):
        sizes = sorted(legs_by_size)
        base_price = legs_by_size[sizes[0]]["price"]
        # 锚点价差（与 Raydium 直读，或跨池中位数）
        ref = anchor if anchor > 0 else (median_first if median_first else base_price)
        spread_bps = abs(base_price - ref) / ref * 10000 if ref else 0
        # 滑点曲线：每档价格 vs 第一档
        impact = {}
        capacity_usd = None
        capacity_sol = None
        max_impact = 0.0
        for s in sizes:
            p = legs_by_size[s]["price"]
            imp = abs(p - base_price) / base_price * 10000 if base_price else 0
            impact[s] = imp
            max_impact = max(max_impact, imp)
            if capacity_usd is None and imp >= THIN_IMPACT_BPS:
                capacity_usd = legs_by_size[s]["usd_notional"]
                capacity_sol = s
        pools.append({
            "pool": pool, "first_size": pool_first_size[pool],
            "price": base_price,  # 池代表价（首档出现价）
            "anchor_spread_bps": round(spread_bps, 1),
            "max_impact_bps": round(max_impact, 1),
            "impact": {str(s): round(v, 1) for s, v in impact.items()},
            "capacity_usd": round(capacity_usd) if capacity_usd else None,
            "capacity_sol": capacity_sol,
            "suspect": spread_bps > SUSPECT_SPREAD_BPS,  # 假信号（重计价/decimals 错）不算薄池
            "thin": (capacity_usd is not None and spread_bps >= MIN_SPREAD_BPS
                     and spread_bps <= SUSPECT_SPREAD_BPS),
        })

    # 3) backrun 模拟：对「价差 > 滑点」的薄池
    # 场景 = 888BMM 同构：受害交易（固定路由/薄池直接交易）砸穿薄池 → 正常池买入 → 薄池卖出
    backruns = []
    for p in pools:
        if not p["thin"] or not p["capacity_usd"]:
            continue
        pool_price = p["price"] or 1.0
        normal = anchor if anchor > 0 else pool_price
        # 薄池双边流动性估计：容量边界（滑点 30bps 处名义量）≈ 单边深度量级
        thin_liq = p["capacity_usd"] * 2
        for attack in [1000, 5000, 10000]:
            if attack >= thin_liq:  # 受害交易超过池子流动性 = 直接买穿，backrun 无意义
                continue
            r = simulate_backrun(pool_price, normal, attack, thin_liq)
            if r["profit"] > 0:
                backruns.append({
                    "pool": p["pool"], "attack_usd": attack,
                    "profit_usd": round(r["profit"], 2),
                    "distortion_x": round(r["distortion"], 1),
                    "victim_price": round(r["victim_price"], 4),
                })
                break

    return {"anchor": anchor, "pools": pools, "backruns": backruns, "ts": now_iso(),
            "base": base_label}


def main():
    ap = argparse.ArgumentParser(description="Backrun 薄池扫描器 v1（#13 容量上限）")
    ap.add_argument("--quiet", action="store_true", help="watchdog：无可执行薄池静默")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--max-sol", type=float, default=5000, help="最大扫描档")
    ap.add_argument("--mint", default=None, help="长尾币 mint（默认扫 SOL/USDC；对任意币扫薄池）")
    ap.add_argument("--symbol", default=None, help="币符号（显示用，默认取 mint 前 6 位）")
    ap.add_argument("--decimals", type=int, default=9, help="币 decimals（BONK=5/WIF=6/多数=9）")
    args = ap.parse_args()

    base_mint = args.mint or SOL_MINT
    base_decimals = args.decimals
    base_label = args.symbol or ("SOL" if base_mint == SOL_MINT else base_mint[:6])

    res = scan(args.max_sol, base_mint, base_decimals, base_label)
    thin_pools = [p for p in res["pools"] if p["thin"]]
    executable = [b for b in res["backruns"]]

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    # watchdog：只有可执行 backrun 或薄池才输出
    if args.quiet and not thin_pools:
        return

    print(f"=== Backrun 薄池扫描 {res['base']}（{res['ts']}）===")
    if res["anchor"]:
        print(f"Raydium 锚点价: ${res['anchor']:.4f}/SOL | ", end="")
    print(f"池数: {len(res['pools'])} | 薄池: {len(thin_pools)}")
    if res["pools"]:
        print(f"\n{'池':<14}{'首档':<6}{'价差bps':<9}{'最大滑点bps':<12}{'容量边界':<12}{'判定'}")
        for p in res["pools"]:
            cap = f"~${p['capacity_usd']:,.0f} ({p['capacity_sol']}档)" if p["capacity_usd"] else "未触顶"
            if p["suspect"]:
                tag = "🚫 suspect"  # 数据异常（重计价/decimals 错），不算薄池
            elif p["thin"]:
                tag = "🟢 薄池"
            elif p["max_impact_bps"] >= THIN_IMPACT_BPS:
                tag = "🟡 观察"
            else:
                tag = "⚪ 深池"
            print(f"{p['pool']:<14}{p['first_size']:<6}{p['anchor_spread_bps']:<9}"
                  f"{p['max_impact_bps']:<12}{cap:<12}{tag}")
    if executable:
        print(f"\n🔥 可执行 backrun {len(executable)} 条：")
        for b in executable:
            print(f"  {b['pool']}: 受害 ${b['attack_usd']:,.0f} → 扭曲 {b['distortion_x']}× "
                  f"→ backrun 净利 ${b['profit_usd']:,.2f}")
    else:
        print("\n无可执行 backrun（薄池价差未覆盖滑点+费率）")


if __name__ == "__main__":
    main()
