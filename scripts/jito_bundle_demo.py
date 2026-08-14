#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jito Bundle demo（jito_bundle_demo.py）— D12 前置产出（2026-08-14）
====================================================================
构造 → 签名 → 提交 → 查状态的完整闭环脚本（无套利意图，只验证流程）。

网络现状（实测 2026-08-14）：
  - Jito devnet block engine 已退役（全区域 SSL EOF）→ devnet 不可用
  - testnet.block-engine.jito.wtf 可达 ✅（testnet SOL 需先领水）
  - mainnet 各区域可达 ✅（需真实 SOL，~$1 级别足够）

用法：
  python scripts/jito_bundle_demo.py --network testnet --dry-run   # 只构造+签名+模拟，不提交
  python scripts/jito_bundle_demo.py --network testnet             # 提交到 testnet
  python scripts/jito_bundle_demo.py --network mainnet             # 提交到 mainnet（小额真钱）

依赖：hermes venv python3.11（solana-py + solders）
"""
import argparse
import base64
import json
import os
import random
import sys
import time
import urllib.request
from pathlib import Path

from solders.keypair import Keypair
from solders.hash import Hash
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey
from solders.commitment_config import CommitmentLevel
from solders.signature import Signature

# ---------- 网络配置 ----------
NETWORKS = {
    "testnet": {
        "rpc": "https://api.testnet.solana.com",
        "engine": "https://testnet.block-engine.jito.wtf/api/v1/bundles",
    },
    "mainnet": {
        "rpc": "https://api.mainnet-beta.solana.com",
        "engine": "https://ny.mainnet.block-engine.jito.wtf/api/v1/bundles",
    },
}
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
TIP_MIN = 1000  # lamports；低于此 bundle 不会被拍卖选中
AMOUNT = 1_000  # 每笔 demo transfer 的 lamports（1e-6 SOL，可忽略）


def http_post(url, payload, proxy=True):
    data = json.dumps(payload).encode()
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=30) as r:
        return json.loads(r.read().decode())


def rpc_call(rpc, method, params):
    d = http_post(rpc, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, proxy=True)
    if "error" in d:
        raise RuntimeError(f"RPC {method}: {d['error']}")
    return d["result"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", choices=list(NETWORKS), default="testnet")
    ap.add_argument("--dry-run", action="store_true", help="只构造+签名，不提交")
    ap.add_argument("--tip", type=int, default=1000, help="tip lamports（最低 1000）")
    ap.add_argument("--n-tx", type=int, default=3, help="bundle 内交易数（含 tip 交易，≤5）")
    args = ap.parse_args()

    net = NETWORKS[args.network]
    # solana-cli 的 id.json = 64 字节 JSON 数组；solders Keypair 用 from_bytes
    with open(Path.home() / ".config/solana/id.json") as f:
        kp = Keypair.from_bytes(bytes(json.load(f)))
    print(f"🔑 钱包: {kp.pubkey()}")

    # 1) 最新 blockhash + tip accounts
    bh = rpc_call(net["rpc"], "getLatestBlockhash", [{"commitment": "confirmed"}])
    blockhash = Hash.from_string(bh["value"]["blockhash"])
    print(f"⏱  blockhash: {blockhash}")
    tips = http_post(net["engine"], {"jsonrpc": "2.0", "id": 1, "method": "getTipAccounts", "params": []})["result"]
    tip_acc = random.choice(tips)
    print(f"💸 tip account: {tip_acc}（{len(tips)} 选 1）tip={args.tip} lamports")

    # 2) 构造交易：n-1 笔小额 transfer（验证顺序执行）+ 1 笔 tip 转账
    txs = []
    for i in range(args.n_tx - 1):
        ix = transfer(TransferParams(from_pubkey=kp.pubkey(), to_pubkey=kp.pubkey(),
                                     lamports=AMOUNT))
        msg = MessageV0.try_compile(kp.pubkey(), [ix], [], blockhash)
        tx = VersionedTransaction(msg, [kp])
        txs.append(tx)
        print(f"  tx{i+1}: transfer {AMOUNT} lamports (self) sig={str(tx.signatures[0])[:8]}")

    # tip 交易（最后一笔：转 SOL 到 tip account）
    tip_ix = transfer(TransferParams(from_pubkey=kp.pubkey(), to_pubkey=Pubkey.from_string(tip_acc),
                                     lamports=args.tip))
    msg_tip = MessageV0.try_compile(kp.pubkey(), [tip_ix], [], blockhash)
    tx_tip = VersionedTransaction(msg_tip, [kp])
    txs.append(tx_tip)
    print(f"  tx{args.n_tx}: tip → {tip_acc[:8]}… sig={str(tx_tip.signatures[0])[:8]}")

    # 3) base64 编码 + 提交
    encoded = [base64.b64encode(bytes(tx)).decode() for tx in txs]
    if args.dry_run:
        print("\n🧪 dry-run：已构造+签名，未提交")
        print(f"  bundle 大小: {len(encoded)} tx, {sum(len(e) for e in encoded)} B base64")
        return

    print(f"\n📤 sendBundle → {net['engine']}")
    d = http_post(net["engine"], {"jsonrpc": "2.0", "id": 1, "method": "sendBundle",
                                  "params": [encoded]})
    if "error" in d:
        print("❌ sendBundle 失败:", d["error"])
        sys.exit(1)
    bundle_id = d["result"]
    print(f"✅ bundle_id: {bundle_id}")
    print(f"   （bundle_id ≠ 已上链；继续轮询状态）")

    # 4) 轮询状态
    for i in range(10):
        time.sleep(3)
        st = http_post(net["engine"], {"jsonrpc": "2.0", "id": 1, "method": "getBundleStatuses",
                                       "params": [[bundle_id]]})
        v = st.get("result", {}).get("value")
        if v:
            s = v[0]
            conf = s.get("confirmation_status", "?")
            err = s.get("err")
            if conf == "finalized":
                print(f"🎉 bundle 已确认: {conf} err={err}")
                print(f"   查 https://explorer.jito.wtf/bundle/{bundle_id}")
                return
            print(f"  [{i}] status={conf} err={err}")
        else:
            print(f"  [{i}] 状态未返回（可能 pending 或已过期）")
    print("⏳ 10 次轮询未确认，手动查 explorer.jito.wtf")


if __name__ == "__main__":
    main()
