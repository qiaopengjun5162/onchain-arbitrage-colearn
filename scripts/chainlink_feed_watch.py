#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chainlink 预言机更新监听器（chainlink_feed_watch.py）— 2026-08-29 清算事件线 Flashblocks 决胜层

核心问题（08-25 probe 结论）：清算交易稀有（~1 笔/小时），信号策略不能等清算交易；
Chainlink 更新是事件驱动（价格偏离超阈值 + 心跳），更新交易发往 aggregator（≠ oracle 地址）。

本脚本解决「怎么监听预言机更新」：
  1. GraphQL 拿 Morpho watchlist 市场 → oracle 地址
  2. eth_getCode + PUSH32 扫描提取 Chainlink feed proxy（MorphoChainlinkOracleV2 的 feeds 是
     immutable，嵌入 bytecode，无公开 getter；USDe 型 46B 最小代理先穿透 implementation）
  3. proxy.aggregator()（0x245a7bfc）→ aggregator 地址（Chainlink 节点 transmit() 发往这里）
  4. 轮询 Base pending 区块（mainnet.base.org，~1s 级滚动，08-25 实测）→ 扫交易 to ∈ aggregator
     → 命中 = 预言机刚更新 = 清算窗口窗口开启 → 立即触发持仓级 HF 扫描（复用 prey_hf_trigger）

节奏定位：公共 RPC pending ~1s（Flashblocks 真 WS 200ms 需 Chainstack 类付费端点，端点可换）
触发到 HF 联动延迟 ≈ pending 轮询 1s + HF GraphQL 2-5s ≈ 3-6s（vs v2 轮询 2-3s 半周期）
价值：v2 靠「偏离突变」间接推断预言机要更新；本脚本直接命中「更新交易」= 确定性信号

用法：
  python scripts/chainlink_feed_watch.py --duration 100   # 跑 100 秒窗口（cron 用）
  python scripts/chainlink_feed_watch.py --once           # 单轮快照（验证/巡检）
  python scripts/chainlink_feed_watch.py --show-feeds     # 只看 feed/aggregator 映射

cron 建议：*/2 * * * *（每 2 分钟 100s 窗口；no_agent watchdog：有更新才输出）
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROXY = "http://127.0.0.1:7890"
PROXIES = {"http": PROXY, "https": PROXY}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
TIMEOUT = 20

RPC = "https://base-rpc.publicnode.com"       # eth_call/getCode（批量）
PENDING_EP = "https://mainnet.base.org"        # pending 区块视图（08-25 实测 ~1s 滚动）
GRAPHQL = "https://blue-api.morpho.org/graphql"

AGG_SEL = "0x245a7bfc"          # aggregator()
DEDUP_S = 90                    # 同 aggregator 90s 内不重报（Chainlink 心跳可能连续更新）
HF_ON_HIT = True                # 命中时触发 HF 扫描

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "chainlink_feed_watch_state.json"

MARKETS_QUERY = """{ markets(first: 200, orderBy: SupplyAssetsUsd, orderDirection: Desc) {
    items { marketId chain { id } listed lltv oracle { address }
            collateralAsset { symbol address } loanAsset { symbol address }
            state { utilization supplyAssetsUsd borrowAssetsUsd } } } }"""


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rpc_post(url, reqs, timeout=TIMEOUT):
    return requests.post(url, json=reqs, headers={"Content-Type": "application/json", "User-Agent": UA},
                         proxies=PROXIES, timeout=timeout)


def gql_markets(chain_id=8453, watch=12):
    for attempt in range(3):
        try:
            r = rpc_post(GRAPHQL, {"query": MARKETS_QUERY})
            d = r.json()
            if d.get("data"):
                break
        except Exception:
            d = {"data": None}
        if attempt < 2:
            time.sleep(2 * (attempt + 1))
    if not d.get("data"):
        return []
    items = [m for m in d["data"]["markets"]["items"] if m["chain"]["id"] == chain_id]
    items = [m for m in items
             if (m.get("collateralAsset") or {}).get("address")
             and (m.get("loanAsset") or {}).get("address")
             and (m.get("oracle") or {}).get("address")]
    live = [m for m in items if m["listed"] and (m.get("state") or {}).get("supplyAssetsUsd")]
    live.sort(key=lambda m: -(m["state"]["supplyAssetsUsd"] or 0))
    return live[:watch]


def get_code(addr):
    r = rpc_post(RPC, [{"jsonrpc": "2.0", "id": 1, "method": "eth_getCode", "params": [addr, "latest"]}])
    return r.json()[0].get("result") or "0x"


def push32_addrs(bytecode):
    """从部署代码扫 PUSH32 (0x7f) 常量，提取形似地址的 32 字节值（前 12 字节为 0）。"""
    b = bytecode[2:]
    out = set()
    for m in re.finditer(r"7f" + r"[0-9a-f]{64}", b):
        val = m.group(0)[2:]
        if val[:24] == "0" * 24:
            out.add("0x" + val[24:])
    return sorted(out)


def resolve_proxy(addr):
    """EIP-1167 最小代理（46B）穿透到 implementation。"""
    code = get_code(addr)
    if len(code) == 2 + 46 * 2:
        return resolve_proxy("0x" + code[2:][-40:])
    return addr


def batch_call(reqs):
    res = rpc_post(RPC, reqs)
    try:
        return res.json()
    except Exception:
        return []


def build_feed_map(markets):
    """oracle bytecode → proxy → aggregator。返回 {aggregator: [market 标签]} + 诊断。"""
    # 1. oracle → bytecode 提取 proxy 候选
    oracles = {}
    for m in markets:
        oracles.setdefault(m["oracle"]["address"], []).append(
            f"{m['collateralAsset']['symbol']}->{m['loanAsset']['symbol']}")
    addrs = list(oracles)
    res = batch_call([{"jsonrpc": "2.0", "id": i, "method": "eth_getCode", "params": [a, "latest"]}
                      for i, a in enumerate(addrs)])
    code_by_addr = {}
    for i, a in enumerate(addrs):
        code = res[i].get("result") if isinstance(res[i], dict) else None
        code_by_addr[a] = code or "0x"
    # 2. 穿透代理 + 提取 proxy
    proxy_set = set()
    for a, code in code_by_addr.items():
        real = resolve_proxy(a) if len(code) == 2 + 46 * 2 else a
        proxy_set |= set(push32_addrs(code_by_addr.get(real, code)))
    proxy_set.discard("0x" + "0" * 40)
    proxy_set.discard("0x" + "0" * 39 + "1")
    proxies = sorted(proxy_set)
    # 3. proxy.aggregator()
    agg_reqs = [{"jsonrpc": "2.0", "id": i, "method": "eth_call",
                 "params": [{"to": p, "data": AGG_SEL}, "latest"]} for i, p in enumerate(proxies)]
    agg_res = batch_call(agg_reqs)
    feed_map = {}
    diag = []
    for i, p in enumerate(proxies):
        raw = agg_res[i].get("result") if i < len(agg_res) and isinstance(agg_res[i], dict) else None
        if raw and len(raw) == 66:
            ag = "0x" + raw[-40:]
            feed_map.setdefault(ag, []).append(p)
            diag.append(f"  {p} → aggregator {ag}")
    return feed_map, diag


def load_state():
    try:
        if STATE_PATH.exists():
            return json.loads(STATE_PATH.read_text())
    except Exception:
        pass
    return {}


def main():
    ap = argparse.ArgumentParser(description="Chainlink 预言机更新监听器")
    ap.add_argument("--duration", type=int, default=0, help="运行秒数（0=无限）")
    ap.add_argument("--once", action="store_true", help="单轮快照")
    ap.add_argument("--interval", type=float, default=1.0, help="pending 轮询间隔秒")
    ap.add_argument("--show-feeds", action="store_true", help="只看映射后退出")
    args = ap.parse_args()

    markets = gql_markets()
    if not markets:
        print("[!] watchlist 为空（GraphQL 重试后仍失败）", file=sys.stderr)
        return 1
    feed_map, diag = build_feed_map(markets)
    if not feed_map:
        # 网络抖动导致 batch_call 失败 → 重试一次
        time.sleep(3)
        feed_map, diag = build_feed_map(markets)
    if not feed_map:
        print("[!] 未提取到 aggregator", file=sys.stderr)
        return 1

    print(f"=== Chainlink feed 监听 @ {utcnow()} UTC | {len(feed_map)} 个 aggregator "
          f"({len(markets)} 市场) ===", file=sys.stderr if not args.show_feeds else sys.stdout)
    for ag, proxies in sorted(feed_map.items()):
        print(f"  aggregator {ag}  <- {len(proxies)} proxy", file=sys.stderr if not args.show_feeds else sys.stdout)

    if args.show_feeds:
        return 0

    state = load_state()
    started = time.time()
    t0 = started
    last_block = None

    while True:
        try:
            r = rpc_post(PENDING_EP, [{"jsonrpc": "2.0", "id": 1,
                                       "method": "eth_getBlockByNumber", "params": ["pending", True]}])
            blk = r.json()[0].get("result")
        except Exception as e:
            print(f"[!] pending 轮询失败: {str(e)[:80]}", file=sys.stderr)
            time.sleep(args.interval)
            continue
        if not blk:
            time.sleep(args.interval)
            continue
        num = int(blk["number"], 16)
        new_block = last_block is not None and num != last_block
        last_block = num
        hits = []
        for tx in blk.get("transactions") or []:
            to = tx.get("to") or ""
            if to in feed_map:
                hits.append(tx)
        if hits:
            now = time.time()
            fresh = []
            for tx in hits:
                key = tx["to"]
                last = state.get(key)
                if last and now - last.get("ts", 0) < DEDUP_S:
                    continue
                state[key] = {"ts": now, "block": num}
                fresh.append(tx)
            if fresh:
                for tx in fresh:
                    proxies = feed_map[tx["to"]]
                    print(f"🔄 [{utcnow()[11:19]}] 预言机更新 块#{num} "
                          f"tx={tx['hash'][:18]}.. → {tx['to'][:12]}.. "
                          f"(proxy: {proxies[0][:12]}..)")
                if HF_ON_HIT:
                    try:
                        sys.path.insert(0, str(ROOT / "scripts"))
                        import prey_hf_trigger as pht
                        rows = pht.hf_scan()
                        if rows:
                            print("── 命中后持仓级 HF ──")
                            for line in pht.format_hf_rows(rows, limit=5):
                                print(line)
                    except Exception as e:
                        print(f"[!] HF 联动失败: {str(e)[:80]}", file=sys.stderr)
        try:
            STATE_PATH.parent.mkdir(exist_ok=True)
            STATE_PATH.write_text(json.dumps(state))
        except Exception:
            pass

        if args.once:
            print(f"\n[--once] 一轮完成 @ 块#{num}，命中 {len(hits)}", file=sys.stderr)
            return 0
        if args.duration and time.time() - started >= args.duration:
            break
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
