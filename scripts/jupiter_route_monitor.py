#!/usr/bin/env python3
"""Jupiter 路由变化监控：route snapshot 对比（只读）。

对应 notes/solana/README.md 研究线二阶段「数据：路由变化」：
- Jupiter 聚合路由（routePlan）会随池子流动性/费率变化而改变
- 路由变化 = 市场结构变化信号（新池上线/流动性迁移/费率调整）
- 对套利的意义：监控 SOL→USDC 主路径的路由，发现「路由跳变」时往往伴随价差窗口

实现：定时拉 Jupiter quote 的 routePlan → 哈希对比 → 变化时记录。
数据源：api.jup.ag/swap/v1/quote（Metis 路由引擎，走代理；v6 已弃用）

用法：
    python scripts/jupiter_route_monitor.py              # 单次快照
    python scripts/jupiter_route_monitor.py --watch 3600
    python scripts/jupiter_route_monitor.py --watchdog   # cron：静默，路由变化才报

依赖：hermes venv python3.11（requests）
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 15
QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "jupiter_route_state.json"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "jupiter_route_changes.csv"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
AMOUNT = 1_000_000_000  # 1 SOL（lamports）
CONFIRM_N = 2           # 同一新路由连续 N 次才算「稳定变化」（防秒级跳变噪音）


def get_route() -> dict:
    params = {"inputMint": SOL_MINT, "outputMint": USDC_MINT,
              "amount": AMOUNT, "slippageBps": 100}
    r = requests.get(QUOTE_URL, params=params, timeout=TIMEOUT, proxies=PROXIES)
    r.raise_for_status()
    q = r.json()
    route = q.get("routePlan", [])
    labels = [f"{p.get('swapInfo', {}).get('label', '?')}" for p in route]
    # 路由签名 = 标签序列 + 输出金额（变化检测用）
    out_amount = q.get("outAmount", "0")
    sig_input = "|".join(labels) + "|" + out_amount
    sig = hashlib.md5(sig_input.encode()).hexdigest()[:12]
    return {"labels": labels, "out_amount": int(out_amount), "sig": sig, "ts": int(time.time())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--watchdog", action="store_true")
    args = ap.parse_args()

    def tick():
        try:
            cur = get_route()
        except Exception as e:
            if not args.watchdog:
                print(f"[err] {e}")
            return 1

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        # 读上次状态
        prev = {}
        prev_sig = None
        prev_labels = []
        prev_out = 0
        if STATE_PATH.exists():
            try:
                with open(STATE_PATH) as f:
                    prev = json.load(f)
                prev_sig = prev.get("sig")
                prev_labels = prev.get("labels", [])
                prev_out = prev.get("out_amount", 0)
            except Exception:
                pass

        changed = prev_sig is not None and prev_sig != cur["sig"]

        # 稳定确认：新路由要连续 CONFIRM_N 次才算变化
        confirmed_change = False
        prev_pending = prev.get("pending", 0) if prev_sig is not None else 0
        if changed:
            pending = prev_pending + 1
            if pending >= CONFIRM_N:
                confirmed_change = True
                pending = 0
            cur["pending"] = pending
        else:
            cur["pending"] = 0

        # 存当前状态
        try:
            STATE_PATH.parent.mkdir(exist_ok=True)
            with open(STATE_PATH, "w") as f:
                json.dump(cur, f)
            # 变化时落盘
            if confirmed_change:
                new = not LOG_PATH.exists()
                with open(LOG_PATH, "a") as f:
                    if new:
                        f.write("ts,old_route,new_route,old_out,new_out\n")
                    f.write(f"{ts},\"{'->'.join(prev_labels)}\",\"{'->'.join(cur['labels'])}\","
                            f"{prev_out},{cur['out_amount']}\n")
        except Exception:
            pass

        if args.watchdog:
            if confirmed_change:
                print(f"⚠️ Jupiter 路由稳定变化 @ {ts}：{'->'.join(prev_labels)} → {'->'.join(cur['labels'])}")
            return 0

        print(f"\n=== Jupiter 路由快照 @ {ts} ===")
        print(f"路由: {' → '.join(cur['labels'])}")
        print(f"输出: {cur['out_amount']/1e6:.4f} USDC（1 SOL）")
        if prev_sig is None:
            print("（首次快照，无对比基线）")
        elif confirmed_change:
            print(f"⚠️ 路由稳定变化！上次: {' → '.join(prev_labels)}")
        elif changed:
            print(f"🔄 路由跳变观察中（{cur.get('pending', 0)}/{CONFIRM_N}，需稳定确认）")
        else:
            print("✅ 路由稳定（与上次一致）")
        return 0

    code = tick()
    if args.watch and not args.watchdog:
        while True:
            time.sleep(args.watch)
            tick()
    return code


if __name__ == "__main__":
    sys.exit(main())
