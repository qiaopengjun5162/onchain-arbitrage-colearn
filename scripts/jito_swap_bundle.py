#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jito Swap Bundle（jito_swap_bundle.py）— D13 主线（2026-08-16）
================================================================
把「Jupiter 构造 swap」+「Jito bundle 提交」串成闭环：
  发现（quote）→ 构造（官方 /swap/v1/swap 端点）→ 提交（sendBundle）
  → 轮询（landed/pending/invalid）→ 日志（JSONL）

说明：
  - 与 jito_bundle_pipeline.py（纯 transfer demo）互补：本脚本跑真实 swap 路径
  - 构造走**官方 /swap/v1/swap 端点**（Jupiter 自动组装指令+LUT）——实测 2026-08-16：
    build v2 raw instructions 手动组装 simulate 通过但 Jito sendBundle Invalid，
    官方端点交易重签名后一次 confirmed
  - ⚠️ 官方端点返回的 swapTransaction 是**未签名**的（签名者全零），必须重签名
  - tip 交易用与 swap 相同的 blockhash（bundle 内统一）

用法：
  python scripts/jito_swap_bundle.py --dry-run                    # 构造+签名+定价，不提交
  python scripts/jito_swap_bundle.py                              # SOL→USDC 小额真提交
  python scripts/jito_swap_bundle.py --amount 10000000 --slippage 100

依赖：hermes venv python3.11（solana-py + solders 0.26.0）
"""
import argparse
import base64
import datetime
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from solders.keypair import Keypair
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey

# ---------- 配置 ----------
PROXY = "http://127.0.0.1:7890"
JUP_BASE = "https://api.jup.ag/swap"
RPC = "https://api.mainnet-beta.solana.com"
ENGINE = "https://ny.mainnet.block-engine.jito.wtf/api/v1/bundles"
TIP_FLOOR_URL = "https://bundles.jito.wtf/api/v1/bundles/tip_floor"
LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "jito_swap_log.jsonl"

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
AMOUNT_DEFAULT = 10_000_000  # 0.01 SOL


def http_get(url, timeout=25):
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-d13"})
    with op.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def http_post(url, payload, timeout=30):
    data = json.dumps(payload).encode()
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with op.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500] if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body}") from e


def rpc_call(method, params):
    d = http_post(RPC, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if "error" in d:
        raise RuntimeError(f"RPC {method}: {d['error']}")
    return d["result"]


def fetch_tip_floor():
    return http_get(TIP_FLOOR_URL)[-1]


def pick_tip():
    """auto：99 分位 ×1.5，下限 0.005 SOL（实测），上限 0.01 SOL。返回 (lamports, 依据)。"""
    floor = fetch_tip_floor()
    pct = floor.get("landed_tips_99th_percentile")
    if pct is None:
        return 5_000_000, "auto:floor-unavailable→0.005SOL"
    tip = max(min(pct * 1.5, 0.01), 0.005)
    return int(tip * 1e9), f"auto:99th={pct:.6f}×1.5→{tip:.6f}SOL"


def jup_quote(input_mint, output_mint, amount, slippage_bps):
    params = {"inputMint": input_mint, "outputMint": output_mint,
              "amount": str(amount), "slippageBps": str(slippage_bps)}
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return http_get(f"{JUP_BASE}/v1/quote?{qs}")


def jup_swap_tx(user_key, quote_resp):
    """官方 /swap/v1/swap 端点 → 完整 swap 交易 base64（Jupiter 自动组装指令+LUT）。
    ⚠️ 返回的交易是**未签名**的（签名者全零），必须用我们的 keypair 重新签名。
    ⚠️ 实测 2026-08-16：build v2 raw instructions 手动组装 simulate 通过但 Jito
    sendBundle Invalid；官方端点交易重签名后一次 confirmed——优先走官方端点。"""
    payload = {"userPublicKey": user_key, "wrapAndUnwrapSol": True,
               "dynamicComputeUnitLimit": True, "quoteResponse": quote_resp}
    d = http_post(f"{JUP_BASE}/v1/swap", payload)
    if "error" in d:
        raise RuntimeError(f"Jupiter swap: {d['error']}")
    return d["swapTransaction"], d.get("lastValidBlockHeight")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只构造+签名+定价，不提交")
    ap.add_argument("--amount", type=int, default=AMOUNT_DEFAULT, help="输入数量 lamports（默认 0.01 SOL）")
    ap.add_argument("--slippage", type=int, default=100, help="滑点 bps（默认 1%）")
    ap.add_argument("--input-mint", default=SOL)
    ap.add_argument("--output-mint", default=USDC)
    args = ap.parse_args()

    with open(Path.home() / ".config/solana/id.json") as f:
        kp = Keypair.from_bytes(bytes(json.load(f)))
    print(f"🔑 钱包: {kp.pubkey()}")

    # 1) 发现：quote
    q = jup_quote(args.input_mint, args.output_mint, args.amount, args.slippage)
    if "error" in q:
        print("❌ quote 失败:", q["error"])
        sys.exit(1)
    print(f"📊 quote: {q['inAmount']} lamports → {q['outAmount']} lamports "
          f"(route {len(q.get('routePlan', []))} 跳, priceImpact {q.get('priceImpactPct')}%)")

    # 2) 构造：官方 /swap/v1/swap 端点（Jupiter 自动组装指令+LUT）
    # ⚠️ 实测 2026-08-16：build v2 raw instructions 手动组装 simulate 通过但 Jito
    #    sendBundle Invalid；官方端点交易重签名后一次 confirmed——官方端点是可靠路径
    swap_b64, lvbh = jup_swap_tx(str(kp.pubkey()), q)
    swap_tx_unsigned = VersionedTransaction.from_bytes(base64.b64decode(swap_b64))
    print(f"🔄 swap tx: {swap_tx_unsigned.message.instructions.__len__()} 指令（官方端点组装）")

    # ⚠️ 官方端点返回**未签名**交易（签名者全零）——用我们的 keypair 重新签名
    swap_tx = VersionedTransaction(swap_tx_unsigned.message, [kp])
    print(f"🔏 swap tx 签名: {str(swap_tx.signatures[0])[:16]}…")
    blockhash = swap_tx.message.recent_blockhash

    # 4) tip 交易（同 blockhash）
    tip_lamports, tip_basis = pick_tip()
    tip_ix = transfer(TransferParams(from_pubkey=kp.pubkey(),
                                     to_pubkey=Pubkey.from_string(random.choice(
                                         http_post(ENGINE, {"jsonrpc": "2.0", "id": 1, "method": "getTipAccounts", "params": []})["result"])),
                                     lamports=tip_lamports))
    tip_tx = VersionedTransaction(MessageV0.try_compile(kp.pubkey(), [tip_ix], [], blockhash), [kp])
    print(f"💸 tip: {tip_basis} = {tip_lamports} lamports, sig={str(tip_tx.signatures[0])[:12]}")

    # 5) simulate 验证 swap tx（不广播）
    # ⚠️ 必须带 replaceRecentBlockhash=true：公共 RPC 对刚拿到的 blockhash 有确认时序
    #    滞后，默认 simulate 会报 BlockhashNotFound（实测 2026-08-16）；replace 后
    #    用节点自己的最新 blockhash 校验，err=null 即交易逻辑有效
    sim = rpc_call("simulateTransaction",
                   [base64.b64encode(bytes(swap_tx)).decode(),
                    {"encoding": "base64", "replaceRecentBlockhash": True}])
    err = sim.get("value", {}).get("err")
    logs = sim.get("value", {}).get("logs", [])
    print(f"🧪 simulate: err={err} logs={len(logs)}")
    if err is not None:
        print("  最后 5 条日志:", logs[-5:] if logs else "无")
        sys.exit(1)

    rec = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "network": "mainnet",
        "input_mint": args.input_mint[:8], "output_mint": args.output_mint[:8],
        "amount": args.amount, "slippage_bps": args.slippage,
        "out_amount": q["outAmount"],
        "tip_lamports": tip_lamports, "tip_basis": tip_basis,
        "dry_run": args.dry_run,
        "bundle_id": None, "status": "constructed", "err": None,
    }
    if args.dry_run:
        print("\n🧪 dry-run：已构造+签名+simulate 通过，未提交")
        rec["status"] = "dry-run"
        write_log(rec)
        return

    # 6) 提交
    encoded = [base64.b64encode(bytes(swap_tx)).decode(), base64.b64encode(bytes(tip_tx)).decode()]
    d = http_post(ENGINE, {"jsonrpc": "2.0", "id": 1, "method": "sendBundle",
                           "params": [encoded, {"encoding": "base64"}]})
    if "error" in d:
        print("❌ sendBundle 失败:", d["error"])
        rec["status"] = "send-failed"
        rec["err"] = str(d["error"])
        write_log(rec)
        sys.exit(1)
    bundle_id = d["result"]
    rec["bundle_id"] = bundle_id
    print(f"✅ bundle_id: {bundle_id}")

    # 7) 轮询
    final = None
    for i in range(12):
        time.sleep(3)
        st = http_post(ENGINE, {"jsonrpc": "2.0", "id": 1, "method": "getBundleStatuses",
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
            try:
                st2 = http_post(ENGINE, {"jsonrpc": "2.0", "id": 1,
                                         "method": "getInflightBundleStatuses",
                                         "params": [[bundle_id]]})
                v2 = st2.get("result", {}).get("value", [])
                if v2:
                    s2 = v2[0]
                    conf2 = s2.get("status", "?")
                    if conf2 == "Invalid":
                        final = ("invalid", conf2, s2.get("err"))
                        print(f"❌ bundle Invalid (inflight): {conf2} err={s2.get('err')} slot={s2.get('landed_slot')}")
                        break
                    if conf2 == "Landed":
                        final = ("landed", "inflight-Landed", s2.get("err"))
                        print(f"🎉 bundle Landed (inflight): slot={s2.get('landed_slot')}")
                        print(f"   查 https://explorer.jito.wtf/bundle/{bundle_id}")
                        break
                    print(f"  [{i}] inflight status={conf2} err={s2.get('err')}")
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
    write_log(rec)


def write_log(rec):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"📝 日志: {LOG_FILE}")


if __name__ == "__main__":
    main()
