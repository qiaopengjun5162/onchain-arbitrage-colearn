#!/usr/bin/env python3
"""无套利带雷达 v1（只读）：价差矩阵 → 走廊宽度 → 出轨检测。

原理（notes/colearn-incremental-137-digest-20260810.md，群友 110 笔记）：
- 无套利带 = 两腿费率和走廊：同一资产在两个池子之间往返，
  只要价差 < 两腿手续费之和（+冲击+gas），套利者无法盈利 → 价差被压在走廊内
- 「价差稳定在走廊内」恰恰是套利者高效收割完毕的证明（市场有效）
- 机会 = 走廊外出轨（大单冲击后的瞬间、新池上线、流动性迁移）
- 低费率池走廊窄 → 出轨频率高 → 机会频率高
- 深度枯竭池按深度过滤（避免假出轨：报价虚高）

实现：
- 价格源：Raydium SOL-USDC 直读（vault 余额恒定乘积）+ Jupiter quote 各金额档路由腿
- 走廊宽度 = fee_A + fee_B（协议费率查表）+ 冲击项（金额档间价格差估算）
- 出轨 = |spread_bps| > corridor_bps（超出走廊）
- 配对矩阵：同金额档下不同池两两配对，输出 spread/corridor/exit

用法：
  python scripts/no_arb_corridor_radar.py            # 单次扫描
  python scripts/no_arb_corridor_radar.py --watch 300
  python scripts/no_arb_corridor_radar.py --watchdog # cron：静默，出轨才报

依赖：python3 + requests；HELIUS_API_KEY 从 ~/.hermes/.env 读
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 15

RPC_URL_TMPL = "https://mainnet.helius-rpc.com/?api-key={key}"
JUPITER_QUOTE = "https://api.jup.ag/swap/v1/quote"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Raydium SOL-USDC 池（D1 已验证）
RAYDIUM_SOL_USDC = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
SOL_VAULT = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
USDC_VAULT = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"

SAMPLES_SOL = [0.1, 1, 10, 100]
EXIT_BPS_MIN = 20        # 出轨超出走廊 ≥20bps 才算信号（防测量噪音）
STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "corridor_radar_state.json"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "corridor_exits.csv"
SERIES_PATH = Path(__file__).resolve().parent.parent / "data" / "corridor_series.csv"

# AMM 标签 → 单腿费率（bps）。未知协议按 30 保守（Orca/Raydium 常见档）
FEE_BPS = {
    "Raydium": 25, "Raydium CLMM": 5, "Raydium CPMM": 25,
    "Orca": 30, "Orca Whirlpool": 5,
    "Meteora": 25, "Meteora DLMM": 25,
    "Phoenix": 0, "OpenBook": 2,
    "Pump.fun": 100, "PumpSwap": 25,
    "Jupiter": 0, "Aquifer": 30, "HumidiFi": 30, "Scorch": 30,
    "Byreal": 30, "Deriverse": 30, "Flux": 30, "BisonFi": 30, "AlphaQ": 30,
    "Whirlpool": 5, "Cropper": 25,
}


def get_helius_key() -> str:
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("HELIUS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


HELIUS_KEY = get_helius_key()


def rpc(method, params):
    if not HELIUS_KEY:
        return None
    resp = requests.post(RPC_URL_TMPL.format(key=HELIUS_KEY),
                         json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                         timeout=TIMEOUT, proxies=PROXIES)
    return resp.json().get("result")


def read_raydium():
    """Raydium SOL-USDC：vault 余额 → 价格；0.25% 费率恒定乘积模拟各金额档输出。"""
    sol = rpc("getTokenAccountBalance", [SOL_VAULT])
    usdc = rpc("getTokenAccountBalance", [USDC_VAULT])
    if not sol or not usdc or not sol.get("value") or not usdc.get("value"):
        return None
    sol_amt = sol["value"]["uiAmount"]
    usdc_amt = usdc["value"]["uiAmount"]
    if not sol_amt or not usdc_amt:
        return None
    k = sol_amt * usdc_amt
    rows = []
    for amt in SAMPLES_SOL:
        new_sol = sol_amt + amt
        new_usdc = k / new_sol
        out = (usdc_amt - new_usdc) * 0.997  # 0.3% 费（v4 池实测口径，保守用 30bps）
        rows.append({
            "pool": "Raydium", "sample_sol": amt, "price": out / amt,
            "out_usdc": out, "fee_bps": 30, "leg_in_usdc": amt * (usdc_amt / sol_amt),
        })
    return rows


def jupiter_rows() -> list:
    """Jupiter 多金额档采样：每条「SOL 输入腿」= 一个池价格观察点。

    坑（2026-08-10 实测）：路由第二跳起的 inputMint 是 USDC（6 位小数），
    不能一律按 SOL 9 位除——否则价格虚高 1000 倍（Manifest 12 万 bps 假信号）。
    只保留 inputMint==SOL 的腿（第一跳），USDC→USDC 稳定腿无 SOL 价格意义，跳过。
    """
    rows = []
    for amt in SAMPLES_SOL:
        try:
            params = {"inputMint": SOL_MINT, "outputMint": USDC_MINT,
                      "amount": int(amt * 1e9), "slippageBps": 300}
            resp = requests.get(JUPITER_QUOTE, params=params, timeout=TIMEOUT, proxies=PROXIES)
            d = resp.json()
            for step in d.get("routePlan", []):
                si = step.get("swapInfo", {})
                if not si:
                    continue
                if si.get("inputMint") != SOL_MINT:
                    continue  # 第二跳起输入是 USDC 等，非 SOL 价格观察点
                out = int(si.get("outAmount", 0)) / 1e6
                inp = int(si.get("inAmount", 0)) / 1e9
                if not inp:
                    continue
                label = si.get("label", "?")
                rows.append({
                    "pool": label, "sample_sol": amt,
                    "price": out / inp, "out_usdc": out,
                    "fee_bps": FEE_BPS.get(label, 30),
                    "leg_in_usdc": inp * (out / inp),  # 该腿名义美元量
                })
        except Exception:
            continue
    return rows


def corridor_width(a: dict, b: dict) -> float:
    """走廊宽度 = 两腿费率 + 冲击余量（同金额档往返的摩擦下限）。"""
    return a["fee_bps"] + b["fee_bps"]


def tick() -> int:
    raydium = read_raydium() or []
    jup = jupiter_rows()
    obs = raydium + jup
    if not obs:
        print("[err] 无价格观察点", file=sys.stderr)
        return 1

    # 配对矩阵：同金额档内两两配对（同池跳过）
    # 说明：同 quote 内多腿互配 = 同一时刻两个活池在卖同一资产，最纯的走廊对比；
    # Raydium 直读是独立锚点（最深的池，价格可信）。
    # 深度过滤留待 v2（需读池 TVL；v1 用 EXIT_BPS_MIN + 费率走廊挡噪音）。
    pairs = []
    by_size = {}
    for o in obs:
        by_size.setdefault(o["sample_sol"], []).append(o)
    for size, group in by_size.items():
        for a, b in combinations(group, 2):
            if a["pool"] == b["pool"]:
                continue
            spread_bps = (b["price"] - a["price"]) / a["price"] * 10000
            corr = corridor_width(a, b)
            exit_bps = abs(spread_bps) - corr
            pairs.append({
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "size": size, "pool_a": a["pool"], "pool_b": b["pool"],
                "price_a": round(a["price"], 6), "price_b": round(b["price"], 6),
                "spread_bps": round(spread_bps, 1),
                "corridor_bps": corr, "exit_bps": round(exit_bps, 1),
                "fee_a": a["fee_bps"], "fee_b": b["fee_bps"],
            })

    # 出轨 = 超出走廊且超出量 ≥ EXIT_BPS_MIN
    exits = [p for p in pairs if p["exit_bps"] >= EXIT_BPS_MIN]

    ts = pairs[0]["ts"] if pairs else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    # 状态快照（记录最近出轨集合；连续确认逻辑 v2 再加）
    cur_keys = [f"{e['size']}:{e['pool_a']}<->{e['pool_b']}" for e in exits]
    state = {"exit_keys": cur_keys, "ts": ts}
    try:
        STATE_PATH.parent.mkdir(exist_ok=True)
        with open(STATE_PATH, "w") as f:
            json.dump(state, f)
    except Exception:
        pass

    # 落盘：出轨事件 + 全配对时间序列
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        if exits:
            new = not LOG_PATH.exists()
            with open(LOG_PATH, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(exits[0].keys()))
                if new:
                    w.writeheader()
                w.writerows(exits)
        new2 = not SERIES_PATH.exists()
        with open(SERIES_PATH, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["ts", "size", "pool_a", "pool_b",
                                              "spread_bps", "corridor_bps", "exit_bps"])
            if new2:
                w.writeheader()
            for p in pairs:
                w.writerow({k: p.get(k) for k in
                            ["ts", "size", "pool_a", "pool_b", "spread_bps", "corridor_bps", "exit_bps"]})
    except Exception:
        pass

    if args.watchdog:
        if exits:
            for e in exits:
                print(f"⚠️ 无套利带出轨 @ {e['ts']}：{e['pool_a']}↔{e['pool_b']} "
                      f"@{e['size']}SOL 价差{e['spread_bps']}bps > 走廊{e['corridor_bps']}bps "
                      f"（超{e['exit_bps']}bps）")
        return 0

    print(f"\n=== 无套利带雷达 @ {ts} ===")
    print(f"{'规模':<6}{'池A':<14}{'池B':<14}{'价差bps':>9}{'走廊bps':>9}{'超出bps':>9}")
    for p in sorted(pairs, key=lambda x: -x["exit_bps"]):
        mark = " ⚠️" if p["exit_bps"] >= EXIT_BPS_MIN else ""
        print(f"{p['size']:<6}{p['pool_a']:<14}{p['pool_b']:<14}"
              f"{p['spread_bps']:>9.1f}{p['corridor_bps']:>9.0f}{p['exit_bps']:>9.1f}{mark}")
    if exits:
        print(f"\n🚨 出轨 {len(exits)} 对（超出走廊 ≥{EXIT_BPS_MIN}bps）：")
        for e in exits:
            print(f"  {e['pool_a']}↔{e['pool_b']} @{e['size']}SOL: {e['spread_bps']}bps > 走廊 {e['corridor_bps']}bps")
    else:
        print("\n✅ 全部配对在无套利带内（市场有效，无出轨）")
    # 最窄走廊池排名（低费率=出轨频率高，机会频率图）
    fee_map = {}
    for o in obs:
        if o["pool"] not in fee_map or o["fee_bps"] < fee_map[o["pool"]]:
            fee_map[o["pool"]] = o["fee_bps"]
    if fee_map:
        print("\n池费率排名（低费率=走廊窄=机会频率高）：")
        for pool, fee in sorted(fee_map.items(), key=lambda x: x[1])[:5]:
            print(f"  {pool}: {fee}bps/腿")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--watchdog", action="store_true")
    args = ap.parse_args()
    code = tick()
    if args.watch:
        while True:
            time.sleep(args.watch)
            tick()
    sys.exit(code)
