"""
[DEPRECATED 2026-08-15] 被 no_arb_corridor_radar.py 取代（2026-08-15 体检）
"""
#!/usr/bin/env python3
"""Solana DEX 价差监控 v0（D4 主线，只读）。

原理（来自 notes/solana/datasource-direct-pool-reading.md）：
- 直接读链上池子优于聚合器报价：池子状态是自己可验证的事实，聚合器是"市场共识价"，共识之内无价差
- 同链跨 DEX 价差 = 同链原子套利的基础（第 2 周 Jito 衔接）

数据源：
1. Helius RPC 直读 Raydium SOL-USDC 池 vault 余额（恒定乘积定价）
2. Jupiter Swap API 不同金额采样 → 观察路由选择的 AMM（Quantum/HumidiFi/Deriverse...）

用法：
  python solana_dex_spread_monitor.py --once
  python solana_dex_spread_monitor.py --watch 60
  python solana_dex_spread_monitor.py --quiet

依赖：hermes venv python3.11 + requests；HELIUS_API_KEY 从 ~/.hermes/.env 读（不硬编码）
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")

# Helius key 从环境变量读（安全铁律：凭证不硬编码）
def get_helius_key() -> str:
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("HELIUS_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    # 兜底：solana cli config（本地文件）
    cfg = os.path.expanduser("~/.config/solana/cli/config.yml")
    if os.path.exists(cfg):
        with open(cfg) as f:
            for line in f:
                if "helius-rpc" in line and "api-key=" in line:
                    return line.split("api-key=", 1)[1].split("&")[0].strip().strip('"')
    return ""


HELIUS_KEY = get_helius_key()
RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}"

# Raydium SOL-USDC 池（D1 已验证）
RAYDIUM_SOL_USDC = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
SOL_VAULT = "DQyrAcCrDXQ7NeoqGgDCZwBvWDcYmFCjSb9JtteuvPpz"
USDC_VAULT = "HLmqeL62xR1QoZ1HKKbXRrdN1p3phKpxRMb2VVopvBBz"

JUPITER_QUOTE = "https://api.jup.ag/swap/v1/quote"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

SAMPLES_SOL = [0.1, 1, 10, 100]     # 采样金额：不同量级触发不同 AMM
THRESHOLD_BPS = 30                   # 池间价差 ≥30bps 报信号
LOG_PATH = Path(__file__).parent.parent / "data" / "solana_dex_spread_log.csv"


def rpc(method, params):
    if not HELIUS_KEY:
        return None
    resp = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                         timeout=15, proxies={"https": PROXY} if os.environ.get("NO_PROXY") != "1" else None)
    return resp.json().get("result")


def read_raydium_pool() -> dict:
    """直读 Raydium SOL-USDC 池：vault 余额 → 价格 + 模拟 swap 输出。"""
    if not HELIUS_KEY:
        return {}
    sol = rpc("getTokenAccountBalance", [SOL_VAULT])
    usdc = rpc("getTokenAccountBalance", [USDC_VAULT])
    if not sol or not usdc or not sol.get("value") or not usdc.get("value"):
        return {}
    sol_amt = sol["value"]["uiAmount"]
    usdc_amt = usdc["value"]["uiAmount"]
    if not sol_amt or not usdc_amt:
        return {}
    price = usdc_amt / sol_amt
    # 模拟 1 SOL swap（0.3% 手续费池）
    k = sol_amt * usdc_amt
    new_sol = sol_amt + 1
    new_usdc = k / new_sol
    out = (usdc_amt - new_usdc) * 0.997
    return {"pool": "Raydium", "sol": sol_amt, "usdc": usdc_amt,
            "price": price, "sim_out_1sol": out}


def jupiter_sample() -> list:
    """Jupiter 多金额采样：记录每次路由选的 AMM 和价格。

    坑（2026-08-10 实测）：第二跳起 inputMint 是 USDC（6 位小数），一律按
    SOL 9 位除会让价格虚高 1000 倍——只统计 inputMint==SOL 的腿。
    """
    rows = []
    for amt in SAMPLES_SOL:
        try:
            params = {
                "inputMint": SOL_MINT, "outputMint": USDC_MINT,
                "amount": int(amt * 1e9),
            }
            resp = requests.get(JUPITER_QUOTE, params=params, timeout=15,
                                proxies={"https": PROXY} if os.environ.get("NO_PROXY") != "1" else None)
            d = resp.json()
            for step in d.get("routePlan", []):
                si = step.get("swapInfo", {})
                if si:
                    if si.get("inputMint") != SOL_MINT:
                        continue  # 第二跳起输入非 SOL，价格无意义
                    out = int(si.get("outAmount", 0)) / 1e6
                    inp = int(si.get("inAmount", 0)) / 1e9  # 该腿实际输入 SOL
                    rows.append({
                        "sample_sol": amt,
                        "amm": si.get("label", "?"),
                        "amm_key": si.get("ammKey", "")[:16],
                        "out_usdc": out,
                        "price": out / inp if inp else 0,  # 该腿价格
                        "leg_in_sol": inp,
                    })
        except Exception:
            continue
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not HELIUS_KEY:
        print("ERROR: 未找到 HELIUS_API_KEY（~/.hermes/.env 或 solana cli config）", file=sys.stderr)
        return 1

    def tick():
        raydium = read_raydium_pool()
        samples = jupiter_sample()
        # 组装行
        rows = []
        if raydium:
            rows.append({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source": "Raydium直读", "pool": "Raydium SOL-USDC",
                "price": round(raydium["price"], 6),
                "sim_out_1sol": round(raydium["sim_out_1sol"], 6),
            })
        for s in samples:
            rows.append({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source": f"Jupiter {s['sample_sol']} SOL", "pool": s["amm"],
                "price": round(s["price"], 6),
                "sim_out_1sol": round(s["out_usdc"], 6),
            })
        # 价差检测：Raydium 直读价 vs Jupiter 采样价
        signals = []
        if raydium and samples:
            jup_price = samples[0]["price"]  # 0.1 SOL 的最优路由
            spread_bps = (jup_price - raydium["price"]) / raydium["price"] * 10000
            if abs(spread_bps) >= THRESHOLD_BPS:
                signals.append({
                    "ts": rows[0]["ts"], "pair": "SOL/USDC",
                    "raydium": round(raydium["price"], 6), "jupiter": round(jup_price, 6),
                    "spread_bps": round(spread_bps, 1),
                })
        # 落盘
        if rows:
            new = not LOG_PATH.exists()
            with open(LOG_PATH, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                if new:
                    w.writeheader()
                w.writerows(rows)
        # 输出
        if rows and (signals or not args.quiet):
            print(f"\n=== {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC Solana DEX 报价 ===")
            print(f"{'来源':<20}{'池/AMM':<20}{'价格(USDC/SOL)':>16}{'1SOL输出':>12}")
            for r in rows:
                print(f"{r['source']:<20}{r['pool']:<20}{r['price']:>16.4f}{r['sim_out_1sol']:>12.4f}")
            if signals:
                print("\n⚠️ 价差信号:")
                for s in signals:
                    print(f"  {s['pair']}: Raydium={s['raydium']} vs Jupiter={s['jupiter']} = {s['spread_bps']}bps")
        elif not args.quiet:
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] Solana DEX 无数据")

    tick()
    if args.watch and not args.once:
        while True:
            time.sleep(args.watch)
            tick()


if __name__ == "__main__":
    import sys
    sys.exit(main())
