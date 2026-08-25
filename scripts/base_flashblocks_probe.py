#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flashblocks pending 验证原型（base_flashblocks_probe.py）— 2026-08-25 D21

目的：验证「用 Base 公共 RPC 的 pending 视图能否看到清算信号链路」——
Flashblocks 决胜层研究的第一步低成本验证（不花钱接 Chainstack 前先确认数据可见性）。

用法（hermes venv）：
  python scripts/base_flashblocks_probe.py --rounds 30 --interval 0.3

输出：
  - pending 块号滚动（可见性/节奏）
  - 交易 calldata selector 频率（交易构成）
  - Morpho liquidate（0xe72c76fe）命中计数

结论（2026-08-25 实测 30 轮）：
  - mainnet.base.org pending 可用：34.8s 内 18 个滚动块号 ≈ 1s 级，能追踪下一个 2s 区块构建
  - liquidate selector 0xe72c76fe 可匹配；但清算交易稀有（010 手册 ~1 笔/小时），
    30s 窗口命中概率≈0 → 信号策略不能等清算交易，要等预言机更新（~30s 一次）
  - 下一步：检测 Chainlink 聚合器更新交易（高频信号）→ 命中后轮询清算交易

⚠️ 2026-08-25 补充实测（40 轮/43.1s，扩展检测）：预言机更新 0 命中 →
  - Chainlink 更新是事件驱动（价格偏离超阈值 + 心跳），不是固定 30s；平稳市况可能数小时一次
  - Morpho oracle 是 ChainlinkOracle 包装合约，更新交易发往底层 aggregator（≠ oracle 地址），
    按 oracle 地址匹配 to 无效
  - 信号策略修正：与其监听预言机交易，不如高频轮询现货价 vs oracle 价偏离（prey radar 思路，
    但把 cron 30min 提到 1s 级）→ 偏离突变=预言机即将更新=清算窗口临近
"""
import argparse
import collections
import json
import time
import urllib.request

try:
    from eth_hash.auto import keccak
    MORPHO_LIQ = "0x" + keccak(b"liquidate(address,address,address,uint256,bytes)")[:4].hex()
except Exception:
    MORPHO_LIQ = "0xe72c76fe"  # 已知值

EP = "https://mainnet.base.org"


def rpc(url, method, params, timeout=10):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--interval", type=float, default=0.3)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    selectors = collections.Counter()
    block_nums = set()
    liq_hits = 0
    t0 = time.time()

    for i in range(args.rounds):
        try:
            blk = rpc(EP, "eth_getBlockByNumber", ["pending", True]).get("result")
            if not blk:
                continue
            num = int(blk["number"], 16)
            block_nums.add(num)
            for tx in blk.get("transactions") or []:
                data = tx.get("input") or ""
                if len(data) >= 10:
                    sel = data[:10]
                    selectors[sel] += 1
                    if sel == MORPHO_LIQ:
                        liq_hits += 1
                        print(f"  🚨 Morpho liquidate 命中: 块#{num} {tx.get('hash','')[:20]} to={tx.get('to','')[:20]}")
        except Exception as e:
            print(f"[{i}] ERR {str(e)[:60]}")
        time.sleep(args.interval)

    dur = time.time() - t0
    nums = sorted(block_nums)
    print(f"\n=== 结果（{args.rounds} 轮 / {dur:.1f}s）===")
    print(f"不同 pending 块号: {len(nums)} 个")
    if len(nums) >= 2:
        print(f"块号跨度: {nums[-1]-nums[0]} 块 → 约 {(nums[-1]-nums[0])*2/dur:.1f}s/块（2s 区块基准）")
    print(f"Morpho liquidate 命中: {liq_hits}")
    print(f"Top {args.top} selector:")
    for sel, cnt in selectors.most_common(args.top):
        print(f"  {sel}  {cnt}")
    print(f"\n结论: pending 可见性 {'✅' if len(nums) >= 3 else '❌'}; "
          f"清算交易稀有({liq_hits} 命中) → 信号策略 = 监听预言机更新而非等清算交易")


if __name__ == "__main__":
    main()
