#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solana RPC Provider 健康哨兵 v1（2026-08-12，TSW 机房故障后新增）
==============================================================
背景：2026-08-12 03:51-04:25 UTC TSW 机房故障 → 29% stake 离线、Jito BE 停、
Helius（验证者节点在 TSW）发交易失败。教训：RPC 供应商 = 单点故障。

功能：
- 多端点轮询 getHealth + getSlot + 延迟：
  * health != ok → 该 provider 故障
  * slot 两次检查不前进 → 集群 stall（比 health 更隐蔽的故障形态）
  * 记录 JSONL 审计（data/rpc_provider_health.jsonl）
- watchdog 模式（--quiet + cron）：全部健康 = 静默；任何故障 = 打印告警并退出非 0

用法：
  python3 scripts/rpc_provider_health_sentinel.py            # 单次检查（详细输出）
  python3 scripts/rpc_provider_health_sentinel.py --quiet    # cron watchdog
依赖：stdlib only；HELIUS_API_KEY 从 ~/.hermes/.env 读（同 priority_fee_monitor）
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "rpc_provider_health.jsonl"
STALL_SLOT_DELTA = 8          # 两次检查间 slot 至少前进这么多才算"活着"
CHECK_INTERVAL = 20           # 单次检查内的两次采样间隔（秒）


def load_helius_key():
    key = os.environ.get("HELIUS_API_KEY", "")
    if key:
        return key.strip()
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("HELIUS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def endpoints():
    eps = {
        "public-mainnet-beta": "https://api.mainnet-beta.solana.com",
        "alchemy-demo": "https://solana-mainnet.g.alchemy.com/v2/demo",
    }
    key = load_helius_key()
    if key:
        eps["helius"] = f"https://mainnet.helius-rpc.com/?api-key={key}"
    return eps


def rpc_call(url, method, params=None, timeout=12):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
        return d.get("result"), (time.time() - t0) * 1000, None
    except Exception as e:
        return None, (time.time() - t0) * 1000, str(e)[:100]


def check_endpoint(name, url):
    """两次采样：health + slot 前进量。返回 (status, detail)。"""
    h1, ms1, e1 = rpc_call(url, "getHealth")
    s1, _, _ = rpc_call(url, "getSlot")
    if e1 and any(code in e1 for code in ("429", "403", "401")):
        return "RATE_LIMIT", f"{e1} ({ms1:.0f}ms) — 限流/鉴权，非故障"
    if h1 != "ok" or s1 is None:
        return "DOWN", f"health={h1} slot={s1} err={e1} ({ms1:.0f}ms)"
    time.sleep(CHECK_INTERVAL)
    s2, ms2, e2 = rpc_call(url, "getSlot")
    if s2 is None:
        return "DEGRADED", f"second getSlot failed: {e2} (first ok, {ms1:.0f}ms)"
    delta = s2 - s1
    if delta < STALL_SLOT_DELTA:
        return "STALL", f"slot {s1}->{s2} 前进 {delta} (<{STALL_SLOT_DELTA}) ({ms2:.0f}ms)"
    return "OK", f"slot {s1}->{s2} (+{delta}) {ms2:.0f}ms"


def main():
    quiet = "--quiet" in sys.argv
    results = {}
    for name, url in endpoints().items():
        try:
            status, detail = check_endpoint(name, url)
        except Exception as e:
            status, detail = "ERR", str(e)[:100]
        results[name] = {"status": status, "detail": detail}
        print(f"  {name:22s} {status:9s} {detail}")

    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "results": results,
        "any_bad": any(v["status"] != "OK" for v in results.values()),
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    bad = [n for n, v in results.items() if v["status"] not in ("OK", "RATE_LIMIT")]
    if bad:
        # 有故障必须报警（watchdog 不能静默）
        print(f"[rpc-health] 故障端点: {', '.join(bad)}")
        sys.exit(1)
    if not quiet:
        print(f"全部健康 ({len(results)} 端点)，已记录 {LOG_PATH}")


if __name__ == "__main__":
    main()
