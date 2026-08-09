#!/usr/bin/env python3
"""基础设施自检哨兵：延迟 P50/P99.9 + 可用性探测（只读）。

对应 notes/node-infra-acceptance-checklist-20260808.md 的「延迟验收」落地版：
- 拒看 Mean，只看 P50/P99.9 + 标准差
- 每个外部依赖（RPC/交易所 API/数据源）测多次采样
- 微爆发模拟：连续快速请求观察尾部延迟

2026-08-09 实战发现（首次运行即抓到 2 个真问题）：
1. defisphere 裸路径 404：必须带完整 query params（sort/networks/from_date/to_date），见 _defisphere_url()
2. jupiter 旧端点 quote-api.jup.ag/v6 已下线（官方 2025-10-01 弃用）→ 已改用 api.jup.ag/swap/v1/quote（Metis 路由引擎）
   同时修复 scripts/jupiter_quote.py 的遗留旧端点 bug
3. helius_rpc 需 HELIUS_API_KEY 环境变量（~/.zshrc 或 hermes env 文件里），execute_code/subprocess 不加载 shell env 会误报 0%

用法：
    python scripts/infra_selfcheck.py                # 全量自检
    python scripts/infra_selfcheck.py --endpoints jup,rpc
    python scripts/infra_selfcheck.py --watch 3600   # 每小时轮询

退出码：0 = 全绿；1 = 有黄色警告；2 = 有红色失败（cron watchdog 用）

依赖：hermes venv python3.11（requests, ccxt）
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path


def _load_env_fallback():
    """兜底：从 ~/.hermes/.env 读 key（cron/execute_code 不继承 shell env 时防止误报 0%）。"""
    if os.environ.get("HELIUS_API_KEY"):
        return
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[7:]
                if line.startswith("HELIUS_API_KEY="):
                    os.environ["HELIUS_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return
    except Exception:
        pass


_load_env_fallback()
from datetime import datetime, timezone

import requests

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
TIMEOUT = 10          # 单次请求超时
SAMPLES = 7           # 每端点采样次数（含 1 次预热）
WARN_P99 = 500        # P99.9 >= 500ms 黄色警告
FAIL_P99 = 2000       # P99.9 >= 2000ms 红色失败
WARN_SD = 200         # 标准差 >= 200ms 说明抖动大

# 端点清单：name -> (method, url, 校验函数, 是否走代理, 需要完整URL构造)
def _ok_200(r):
    return r.status_code == 200

def _ok_json(r):
    return r.status_code == 200

def _ok_rpc(r):
    return r.status_code == 200 and '"result"' in r.text

def _ok_defisphere(r):
    return r.status_code == 200 and ('results' in r.text or 'data' in r.text)

import urllib.parse
from datetime import datetime, timedelta

def _defisphere_url():
    fd = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    td = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    params = {"sort": "-datetime", "page": 1, "limit": 5,
              "networks": "ethereum", "from_date": fd, "to_date": td}
    return f"https://sphere.data.blockanalitica.com/liquidations/?{urllib.parse.urlencode(params)}"

ENDPOINTS = {
    # 交易所 API（cex 套利数据源）
    "okx": ("GET", "https://www.okx.com/api/v5/public/time", _ok_200, True),
    "bitget": ("GET", "https://api.bitget.com/api/v2/public/time", _ok_200, True),
    "kucoin": ("GET", "https://api.kucoin.com/api/v1/timestamp", _ok_200, True),
    "gate": ("GET", "https://api.gateio.ws/api/v4/spot/time", _ok_200, True),
    # Solana RPC（Helius 需 API key，从环境变量读）
    "helius_rpc": ("POST", f"https://mainnet.helius-rpc.com/?api-key={os.environ.get('HELIUS_API_KEY','')}",
                   _ok_rpc, False),
    # Jupiter 报价（Metis 路由引擎；quote-api.jup.ag v6 已于 2025-10-01 弃用）
    "jupiter": ("GET", "https://api.jup.ag/swap/v1/quote?inputMint=So11111111111111111111111111111111111111112&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=1000000",
                _ok_json, True),
    # DeFi Sphere 清算数据（真实路径带完整 params，2026-08-09 验证）
    "defisphere": ("GET", _defisphere_url(), _ok_defisphere, True),
    # LI.FI 跨链报价
    "lifi": ("GET", "https://li.quest/v1/tokens?chains=1,10,137,8453",
             _ok_json, True),
}


def probe(method, url, check, use_proxy, n=SAMPLES):
    """采样 n 次（含预热 1 次），返回延迟列表 + 可用性。"""
    latencies = []
    ok_count = 0
    for i in range(n):
        proxies = PROXIES if use_proxy else None
        try:
            t0 = time.perf_counter()
            if method == "GET":
                r = requests.get(url, timeout=TIMEOUT, proxies=proxies)
            else:
                r = requests.post(url, timeout=TIMEOUT, proxies=proxies,
                                  json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"})
            dt = (time.perf_counter() - t0) * 1000
            latencies.append(dt)
            if check(r):
                ok_count += 1
        except Exception as e:
            latencies.append(TIMEOUT * 1000)
    # 去掉预热（第一个样本）
    latencies = latencies[1:] or latencies
    return latencies, ok_count, n


def summarize(name, method, url, check, use_proxy):
    latencies, ok_count, total = probe(method, url, check, use_proxy)
    p50 = statistics.median(latencies)
    p999 = sorted(latencies)[int(len(latencies) * 0.999) - 1] if len(latencies) > 1 else latencies[0]
    sd = statistics.pstdev(latencies) if len(latencies) > 1 else 0.0
    availability = ok_count / total
    status = "🟢"
    if p999 >= FAIL_P99 or availability < 0.5:
        # 0.5 阈值：免费额度抖动（如 Jupiter 无 key 限流 71%）不算真故障
        status = "🔴"
    elif p999 >= WARN_P99 or sd >= WARN_SD or availability < 1.0:
        status = "🟡"
    return {
        "name": name, "status": status, "p50_ms": round(p50, 1),
        "p999_ms": round(p999, 1), "sd_ms": round(sd, 1),
        "availability": f"{availability:.0%}", "ok": f"{ok_count}/{total}",
    }


def run(endpoints=None):
    results = []
    for name, (m, u, c, p) in ENDPOINTS.items():
        if endpoints and name not in endpoints:
            continue
        try:
            results.append(summarize(name, m, u, c, p))
        except Exception as e:
            results.append({"name": name, "status": "🔴", "error": str(e)})
    return results


def main():
    ap = argparse.ArgumentParser(description="基础设施自检哨兵")
    ap.add_argument("--endpoints", help="逗号分隔的端点名子集")
    ap.add_argument("--watch", type=int, help="轮询间隔秒数")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--watchdog", action="store_true",
                    help="cron watchdog 模式：全绿静默退出 0，有黄/红才打印问题端点")
    args = ap.parse_args()

    endpoints = args.endpoints.split(",") if args.endpoints else None

    if args.watch:
        while True:
            results = run(endpoints)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"\n=== infra selfcheck @ {ts} ===")
            for r in results:
                if r.get("status") != "🟢":
                    print(json.dumps(r, ensure_ascii=False))
            time.sleep(args.watch)

    results = run(endpoints)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    exit_code = 0
    problems = []
    for r in results:
        status = r["status"]
        if status == "🔴":
            exit_code = max(exit_code, 2)
            problems.append(r)
        elif status == "🟡":
            exit_code = max(exit_code, 1)
            problems.append(r)

    if args.watchdog:
        # watchdog：全绿静默（stdout 空 = cron 不推送），有问题只打印问题行
        if problems:
            print(f"基础设施自检 {ts}")
            for r in problems:
                print(f"{r['status']} {r['name']} P50={r.get('p50_ms')}ms P99.9={r.get('p999_ms')}ms "
                      f"可用={r.get('availability')} ok={r.get('ok')}")
        sys.exit(exit_code)

    print(f"基础设施自检 @ {ts}")
    print(f"{'端点':<14}{'状态':<4}{'P50':>8}{'P99.9':>8}{'SD':>8}{'可用':>8}{'OK':>6}")
    for r in results:
        status = r["status"]
        print(f"{r['name']:<14}{status:<4}{r.get('p50_ms','-'):>8}{r.get('p999_ms','-'):>8}"
              f"{r.get('sd_ms','-'):>8}{r.get('availability','-'):>8}{r.get('ok','-'):>6}")
    print(f"\n退出码 {exit_code}（0=全绿 1=黄 2=红）")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
