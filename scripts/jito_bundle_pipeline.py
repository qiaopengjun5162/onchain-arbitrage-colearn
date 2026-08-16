#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jito Bundle 管线 v2（jito_bundle_pipeline.py）— D12 升级（2026-08-16）
========================================================================
把 demo（jito_bundle_demo.py）升级为参数化管线，为 D13「bundle 加套利逻辑」铺路：

  1. tip 自动定价：查 bundles.jito.wtf tip_floor 分位数，默认 99 分位 × 5 安全垫
     （实测 2026-08-15：1000~100000 lamports 全 pending/Invalid，0.005 SOL 稳落地）
  2. 结构化日志：每次运行 append 一行 JSONL 到 data/jito_bundle_log.jsonl
  3. 状态机轮询：getBundleStatuses + getInflightBundleStatuses 双查，
     landed/pending/invalid 区分，invalid 时打印错误明细

用法：
  python scripts/jito_bundle_pipeline.py --network mainnet --dry-run        # 构造+签名+定价，不提交
  python scripts/jito_bundle_pipeline.py --network mainnet                  # auto tip，真提交
  python scripts/jito_bundle_pipeline.py --network testnet --tip-mode fixed --tip 5000000
  python scripts/jito_bundle_pipeline.py --network mainnet --n-tx 1         # 纯 tip 单笔（最稳）

依赖：hermes venv python3.11（solana-py + solders 0.26.0）
"""
import argparse
import base64
import datetime
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from solders.keypair import Keypair
from solders.hash import Hash
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey

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
TIP_FLOOR_URL = "https://bundles.jito.wtf/api/v1/bundles/tip_floor"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
AMOUNT = 1_000  # 每笔 demo transfer 的 lamports（1e-6 SOL）
LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "jito_bundle_log.jsonl"


def http_post(url, payload, proxy=True, timeout=30):
    data = json.dumps(payload).encode()
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        # ⚠️ urllib 默认丢错误 body——读出来打印（2026-08-15 实测：400 的
        # "Duplicate transaction message hash" 只有读 body 才看得到）
        body = e.read().decode()[:500] if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body}") from e


def rpc_call(rpc, method, params):
    d = http_post(rpc, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, proxy=True)
    if "error" in d:
        raise RuntimeError(f"RPC {method}: {d['error']}")
    return d["result"]


def fetch_tip_floor():
    """查 tip_floor 分位数（SOL）。GET 接口，返回最新一条 dict。"""
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    with opener.open(TIP_FLOOR_URL, timeout=30) as r:
        arr = json.loads(r.read().decode())
    if not arr:
        return {}
    return arr[-1]  # 最新一条


def pick_tip(tip_mode, tip_fixed, percentile="99th"):
    """tip 定价。auto = tip_floor 99 分位 × 1.5 安全垫，下限 0.005 SOL、上限 0.01 SOL。
    返回 (lamports, 依据串)。

    定价依据（2026-08-15/16 实测）：
    - <99 分位 tip 全 pending/Invalid；0.005 SOL 立即 confirmed
    - 0.003 SOL 仍 Invalid（2026-08-16 实测）→ 下限提到 0.005
    - tip_floor 是动态的（2 分钟内 99th 可从 0.0009 涨到 0.0035 SOL）→ 必须现场查
    - ×1.5 + 下限 0.005 保证落地，上限 0.01 防止极端行情下 demo 烧钱
    """
    if tip_mode == "fixed":
        return tip_fixed, f"fixed:{tip_fixed}lamports"
    floor = fetch_tip_floor()
    pct = floor.get(f"landed_tips_{percentile}_percentile")
    if pct is None:
        # 兜底：实测稳定值 0.005 SOL
        return 5_000_000, "auto:floor-unavailable→0.005SOL(实测稳定)"
    tip = max(min(pct * 1.5, 0.01), 0.005)
    return int(tip * 1e9), f"auto:{percentile}={pct:.6f}SOL×1.5→{tip:.6f}SOL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", choices=list(NETWORKS), default="testnet")
    ap.add_argument("--dry-run", action="store_true", help="只构造+签名+定价，不提交")
    ap.add_argument("--tip-mode", choices=["auto", "fixed"], default="auto",
                    help="auto=查 tip_floor 99分位×5（默认，推荐）；fixed=用 --tip")
    ap.add_argument("--tip", type=int, default=5_000_000, help="fixed 模式的 tip lamports")
    ap.add_argument("--n-tx", type=int, default=3, help="bundle 内交易数（含 tip 交易，1~5）")
    ap.add_argument("--log", action="store_true", default=True, help="写 JSONL 日志（默认开）")
    args = ap.parse_args()

    net = NETWORKS[args.network]
    n_tx = max(1, min(args.n_tx, 5))

    with open(Path.home() / ".config/solana/id.json") as f:
        kp = Keypair.from_bytes(bytes(json.load(f)))
    print(f"🔑 钱包: {kp.pubkey()}")

    # 0) tip 定价
    tip_lamports, tip_basis = pick_tip(args.tip_mode, args.tip)
    print(f"💸 tip 定价: {tip_basis} = {tip_lamports} lamports")

    # 1) 最新 blockhash + tip accounts
    bh = rpc_call(net["rpc"], "getLatestBlockhash", [{"commitment": "confirmed"}])
    blockhash = Hash.from_string(bh["value"]["blockhash"])
    print(f"⏱  blockhash: {blockhash}")
    tips = http_post(net["engine"], {"jsonrpc": "2.0", "id": 1, "method": "getTipAccounts", "params": []})["result"]
    tip_acc = random.choice(tips)
    print(f"💸 tip account: {tip_acc}（{len(tips)} 选 1）")

    # 2) 构造交易
    # ⚠️ 每笔 self-transfer 金额必须不同（金额×序号递增）——相同 from/to/金额/blockhash
    #    会生成相同 message → 相同签名 → block engine 报 "Duplicate transaction message hash"
    #    （2026-08-16 实测 HTTP 400）
    txs = []
    for i in range(n_tx - 1):
        amt = AMOUNT * (i + 1)
        ix = transfer(TransferParams(from_pubkey=kp.pubkey(), to_pubkey=kp.pubkey(),
                                     lamports=amt))
        msg = MessageV0.try_compile(kp.pubkey(), [ix], [], blockhash)
        tx = VersionedTransaction(msg, [kp])
        txs.append(tx)
        print(f"  tx{i+1}: transfer {amt} lamports (self) sig={str(tx.signatures[0])[:8]}")
    tip_ix = transfer(TransferParams(from_pubkey=kp.pubkey(), to_pubkey=Pubkey.from_string(tip_acc),
                                     lamports=tip_lamports))
    msg_tip = MessageV0.try_compile(kp.pubkey(), [tip_ix], [], blockhash)
    tx_tip = VersionedTransaction(msg_tip, [kp])
    txs.append(tx_tip)
    print(f"  tx{n_tx}: tip → {tip_acc[:8]}… sig={str(tx_tip.signatures[0])[:8]}")

    encoded = [base64.b64encode(bytes(tx)).decode() for tx in txs]

    # 3) 结构化日志（先记构造，提交后补状态）
    rec = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "network": args.network,
        "n_tx": n_tx,
        "tip_lamports": tip_lamports,
        "tip_basis": tip_basis,
        "dry_run": args.dry_run,
        "blockhash": str(blockhash),
        "bundle_id": None,
        "status": "constructed",
        "err": None,
    }

    if args.dry_run:
        print("\n🧪 dry-run：已构造+签名+定价，未提交")
        print(f"  bundle 大小: {len(encoded)} tx, {sum(len(e) for e in encoded)} B base64")
        rec["status"] = "dry-run"
        write_log(rec, args.log)
        return

    # 4) 提交
    print(f"\n📤 sendBundle → {net['engine']}")
    d = http_post(net["engine"], {"jsonrpc": "2.0", "id": 1, "method": "sendBundle",
                                  "params": [encoded, {"encoding": "base64"}]})
    if "error" in d:
        print("❌ sendBundle 失败:", d["error"])
        rec["status"] = "send-failed"
        rec["err"] = str(d["error"])
        write_log(rec, args.log)
        sys.exit(1)
    bundle_id = d["result"]
    rec["bundle_id"] = bundle_id
    print(f"✅ bundle_id: {bundle_id}")
    print(f"   （bundle_id ≠ 已上链；继续轮询状态）")

    # 5) 状态机轮询：getBundleStatuses 主查 + getInflightBundleStatuses 兜底（5 分钟内）
    # ⚠️ 字段差异（2026-08-16 实测）：getBundleStatuses 项有 confirmation_status；
    #    getInflightBundleStatuses 项是 status（"Pending"/"Landed"/"Invalid"）+ landed_slot
    final = None
    for i in range(12):
        time.sleep(3)
        st = http_post(net["engine"], {"jsonrpc": "2.0", "id": 1, "method": "getBundleStatuses",
                                       "params": [[bundle_id]]})
        v = st.get("result", {}).get("value")
        if v:
            s = v[0]
            conf = s.get("confirmation_status", "?")
            err = s.get("err")
            if conf in ("finalized", "confirmed"):
                final = ("landed", conf, err)
                print(f"🎉 bundle 已确认: {conf} err={err}")
                print(f"   查 https://explorer.jito.wtf/bundle/{bundle_id}")
                break
            if err is not None:
                final = ("invalid", conf, err)
                print(f"❌ bundle Invalid: {conf} err={err}")
                break
            print(f"  [{i}] status={conf} err={err}")
        else:
            # 兜底：inflight 查询（bundle 提交后 5 分钟内有效，能拿到 Invalid 明细）
            try:
                st2 = http_post(net["engine"], {"jsonrpc": "2.0", "id": 1,
                                                "method": "getInflightBundleStatuses",
                                                "params": [[bundle_id]]})
                v2 = st2.get("result", {}).get("value", [])
                if v2:
                    s2 = v2[0]
                    conf2 = s2.get("status", "?")
                    err2 = s2.get("err")
                    slot2 = s2.get("landed_slot")
                    if conf2 == "Invalid":
                        final = ("invalid", conf2, err2)
                        print(f"❌ bundle Invalid (inflight): status={conf2} err={err2} landed_slot={slot2}")
                        break
                    if conf2 == "Landed":
                        final = ("landed", "inflight-Landed", err2)
                        print(f"🎉 bundle Landed (inflight): slot={slot2} err={err2}")
                        print(f"   查 https://explorer.jito.wtf/bundle/{bundle_id}")
                        break
                    print(f"  [{i}] inflight status={conf2} err={err2} landed_slot={slot2}")
                else:
                    print(f"  [{i}] 状态未返回（pending 或已过期）")
            except Exception as e:
                print(f"  [{i}] inflight 查询失败: {e}")
    if final is None:
        print("⏳ 12 次轮询未确认，手动查 explorer.jito.wtf")
        rec["status"] = "timeout-pending"
    else:
        rec["status"] = final[0]
        rec["err"] = final[2]
    write_log(rec, args.log)


def write_log(rec, enabled=True):
    if not enabled:
        return
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"📝 日志: {LOG_FILE}")


if __name__ == "__main__":
    main()
