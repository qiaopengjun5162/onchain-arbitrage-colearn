#!/usr/bin/env python3
"""失败交易监控：知名 Solana 程序/地址的交易失败率（只读）。

对应 notes/solana/README.md 研究线二阶段「数据：失败交易」：
- 失败率 = 执行质量指标（高失败率 = 抢跑/滑点/程序问题）
- 对套利的意义：自己的交易失败率（错误码分布）反映执行质量；程序整体失败率反映生态状态

数据源：Helius RPC getSignaturesForAddress（err 字段 = None 成功，非 None 失败）
监控对象：知名 DEX/MEV 程序（Raydium/Pump.fun/Orca/Meteora/Drift）

用法：
    python scripts/failed_tx_monitor.py              # 单次
    python scripts/failed_tx_monitor.py --watch 3600
    python scripts/failed_tx_monitor.py --watchdog   # cron：静默，失败率异常才报

依赖：hermes venv python3.11（requests）；HELIUS_API_KEY
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 20
SAMPLE = 30  # 每程序采样笔数

# 失败率报警阈值
ALERT_FAIL_RATE = 0.2  # 失败率 >= 20% 报警

# 监控的程序（地址已实证可查）
PROGRAMS = {
    "Raydium-CP": "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",
    "Pump.fun": "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
    "Meteora-DLMM": "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9aVaVNSu",
    "Jupiter-Router": "JUP6LrZxUCaku1FJMGc1tVhTxW9P7QfP5d6kqWJ4hFk",
}


def load_helius_key() -> str:
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return os.environ.get("HELIUS_API_KEY", "")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("HELIUS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("HELIUS_API_KEY", "")


def collect(url: str) -> list:
    rows = []
    for name, addr in PROGRAMS.items():
        try:
            r = requests.post(url, json={"jsonrpc": "2.0", "id": 1,
                                         "method": "getSignaturesForAddress",
                                         "params": [addr, {"limit": SAMPLE}]},
                              timeout=TIMEOUT, proxies=PROXIES)
            sigs = r.json().get("result", [])
            if not sigs:
                rows.append({"program": name, "n": 0, "failed": 0, "rate": 0.0, "errs": {}})
                continue
            failed = sum(1 for s in sigs if s.get("err") is not None)
            errs = {}
            for s in sigs:
                e = s.get("err")
                if e is not None:
                    key = str(e)[:60]
                    errs[key] = errs.get(key, 0) + 1
            rows.append({
                "program": name,
                "n": len(sigs),
                "failed": failed,
                "rate": failed / len(sigs),
                "errs": errs,
            })
        except Exception as e:
            rows.append({"program": name, "n": 0, "failed": 0, "rate": 0.0, "errs": {"error": str(e)[:40]}})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--watchdog", action="store_true")
    args = ap.parse_args()

    key = load_helius_key()
    if not key:
        print("ERROR: 未找到 HELIUS_API_KEY", file=sys.stderr)
        return 1
    url = f"https://mainnet.helius-rpc.com/?api-key={key}"

    def tick():
        rows = collect(url)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        alerts = [r for r in rows if r["n"] > 0 and r["rate"] >= ALERT_FAIL_RATE]

        if args.watchdog:
            if alerts:
                lines = "，".join(f"{r['program']} {r['rate']*100:.0f}%" for r in alerts)
                print(f"⚠️ 失败率异常 @ {ts}：{lines}")
            return 0

        print(f"\n=== 失败交易监控 @ {ts} ===")
        print(f"报警阈值: 失败率 ≥ {ALERT_FAIL_RATE*100:.0f}%")
        print(f"\n{'程序':<16}{'采样':>6}{'失败':>6}{'失败率':>8}")
        for r in rows:
            mark = " ★" if r["n"] > 0 and r["rate"] >= ALERT_FAIL_RATE else ""
            print(f"{r['program']:<16}{r['n']:>6}{r['failed']:>6}{r['rate']*100:>7.0f}%{mark}")
            if r["errs"] and not (len(r["errs"]) == 1 and "error" in r["errs"]):
                for err, cnt in sorted(r["errs"].items(), key=lambda x: -x[1])[:3]:
                    print(f"    {cnt}x {err}")
        if not alerts:
            print(f"\n无失败率 ≥ {ALERT_FAIL_RATE*100:.0f}% 的程序（执行质量正常）")
        return 0

    code = tick()
    if args.watch and not args.watchdog:
        import time
        while True:
            time.sleep(args.watch)
            tick()
    return code


if __name__ == "__main__":
    sys.exit(main())
