#!/usr/bin/env python3
"""Jupiter 路由变化监控 v2：route snapshot + 报价新鲜度 + 漂移检测（只读）。

对应 notes/solana/README.md 研究线二阶段「数据：路由变化」：
- Jupiter 聚合路由（routePlan）会随池子流动性/费率变化而改变
- 路由变化 = 市场结构变化信号（新池上线/流动性迁移/费率调整）
- 对套利的意义：监控 SOL→USDC 主路径的路由，发现「路由跳变」时往往伴随价差窗口

v2 升级（对应 notes/colearn-incremental-137-digest-20260810.md 教训）：
- 笔记 052/056/058：一次报价不可信，二次查询纠偏 → --double-check 双报价漂移检测
- 笔记 058：LI.FI 默认按费用排序不按时间 → Jupiter 侧没有 executionDuration，
  用 contextSlot / 每跳 updateContextSlot 做「报价新鲜度」维度（slot_lag 替代执行时长）
- 每次 tick 追加时间序列 CSV（jupiter_route_time.csv），变化事件之外还有基线可分析

数据源：api.jup.ag/swap/v1/quote（Metis 路由引擎，走代理；v6 已弃用）
新鲜度：mainnet.helius-rpc.com getSlot（HELIUS_API_KEY 从 ~/.hermes/.env 读）

用法：
    python scripts/jupiter_route_monitor.py              # 单次快照
    python scripts/jupiter_route_monitor.py --watch 3600
    python scripts/jupiter_route_monitor.py --watchdog   # cron：静默，路由变化/漂移/陈旧才报
    python scripts/jupiter_route_monitor.py --double-check  # 每 tick 两次报价检测漂移（watchdog 默认开）

依赖：python3（requests）；系统 python3.9 可用，hermes venv 更佳
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
TIME_PATH = Path(__file__).resolve().parent.parent / "data" / "jupiter_route_time.csv"
ENV_PATH = Path.home() / ".hermes" / ".env"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
AMOUNT = 1_000_000_000  # 1 SOL（lamports）
CONFIRM_N = 2           # 同一新路由连续 N 次才算「稳定变化」（防秒级跳变噪音）
DOUBLE_CHECK_GAP = 2.0  # 双报价间隔（秒）
OUT_DRIFT_BPS = 10      # 两次报价 outAmount 相对差 >0.1% 即判漂移
STALE_SLOT_THRESHOLD = 1500   # contextSlot 落后当前 slot 超 ~10min（400ms/slot）判陈旧
STALE_HOP_THRESHOLD = 3000    # 某跳 updateContextSlot 落后 contextSlot 超 ~20min 判可疑池


def _read_env_key(name: str) -> str:
    """从 ~/.hermes/.env 读 key（处理 export 前缀）。"""
    v = os.environ.get(name, "")
    if v:
        return v
    try:
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
            if line.startswith(f"export {name}="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def get_route() -> dict:
    params = {"inputMint": SOL_MINT, "outputMint": USDC_MINT,
              "amount": AMOUNT, "slippageBps": 100}
    r = requests.get(QUOTE_URL, params=params, timeout=TIMEOUT, proxies=PROXIES)
    r.raise_for_status()
    q = r.json()
    route = q.get("routePlan", [])
    labels = [p.get("swapInfo", {}).get("label", "?") for p in route]
    out_amount = q.get("outAmount", "0")
    sig_input = "|".join(labels) + "|" + out_amount
    sig = hashlib.md5(sig_input.encode()).hexdigest()[:12]
    # 每跳价格源更新时间（updateContextSlot），取最小 = 路线里最旧的价格源
    slots = [p.get("swapInfo", {}).get("updateContextSlot") for p in route]
    slots = [s for s in slots if isinstance(s, int)]
    return {
        "labels": labels,
        "out_amount": int(out_amount),
        "sig": sig,
        "ts": int(time.time()),
        "context_slot": q.get("contextSlot"),
        "min_update_slot": min(slots) if slots else None,
        "time_taken": q.get("timeTaken"),  # 服务器报价耗时（非执行时间，仅存档）
    }


def get_current_slot():
    """返回当前 slot；无 key 或请求失败返回 None。"""
    key = _read_env_key("HELIUS_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(f"https://mainnet.helius-rpc.com/?api-key={key}",
                          json={"jsonrpc": "2.0", "id": 1, "method": "getSlot"},
                          timeout=TIMEOUT, proxies=PROXIES)
        r.raise_for_status()
        return r.json().get("result")
    except Exception:
        return None


def _csv_append(path: Path, header: str, row: str) -> None:
    new = not path.exists()
    with open(path, "a") as f:
        if new:
            f.write(header + "\n")
        f.write(row + "\n")


def tick(double_check: bool, watchdog: bool) -> int:
    try:
        cur = get_route()
    except Exception as e:
        if not watchdog:
            print(f"[err] quote: {e}")
        return 1

    drift = 0
    route_flip = 0
    if double_check:
        time.sleep(DOUBLE_CHECK_GAP)
        try:
            cur2 = get_route()
            # 金额级漂移：两次报价 outAmount 差 > OUT_DRIFT_BPS（实打实的报价不可信）
            d_bps = abs(cur2["out_amount"] - cur["out_amount"]) * 10000 / max(cur["out_amount"], 1)
            if d_bps > OUT_DRIFT_BPS:
                drift = 1
            # 纯路由抖动：签名不同但金额差很小（1 SOL 量级单跳池秒级翻转=正常噪音，只记账）
            if cur2["sig"] != cur["sig"] and d_bps <= OUT_DRIFT_BPS:
                route_flip = 1
        except Exception as e:
            if not watchdog:
                print(f"[err] second quote: {e}")

    cur_slot = get_current_slot()
    slot_lag = None
    if isinstance(cur.get("context_slot"), int) and isinstance(cur_slot, int):
        slot_lag = max(0, cur_slot - cur["context_slot"])
    stale_hops = False
    if isinstance(cur.get("min_update_slot"), int) and isinstance(cur.get("context_slot"), int):
        if cur["context_slot"] - cur["min_update_slot"] > STALE_HOP_THRESHOLD:
            stale_hops = True

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
    cur["slot_lag"] = slot_lag
    cur["stale_hops"] = stale_hops
    cur["drift"] = drift
    cur["route_flip"] = route_flip

    # 存当前状态
    try:
        STATE_PATH.parent.mkdir(exist_ok=True)
        with open(STATE_PATH, "w") as f:
            json.dump(cur, f)
        # 时间序列（每次 tick 一行）
        _csv_append(TIME_PATH,
                    "ts,sig,labels,out_amount,context_slot,slot_lag,time_taken,drift,route_flip",
                    f"{ts},{cur['sig']},\"{'->'.join(cur['labels'])}\","
                    f"{cur['out_amount']},{cur.get('context_slot')},{slot_lag},"
                    f"{cur.get('time_taken')},{drift},{route_flip}")
        # 变化事件
        if confirmed_change:
            _csv_append(LOG_PATH,
                        "ts,old_route,new_route,old_out,new_out,old_context,new_context",
                        f"{ts},\"{'->'.join(prev_labels)}\",\"{'->'.join(cur['labels'])}\","
                        f"{prev_out},{cur['out_amount']},"
                        f"{prev.get('context_slot')},{cur.get('context_slot')}")
    except Exception as e:
        if not watchdog:
            print(f"[err] state: {e}")

    issues = []
    if confirmed_change:
        issues.append(f"路由稳定变化：{'->'.join(prev_labels)} → {'->'.join(cur['labels'])}")
    if drift:
        issues.append(f"报价漂移（两次报价金额差>{OUT_DRIFT_BPS}bps，单次报价不可信）")
    if isinstance(slot_lag, int) and slot_lag > STALE_SLOT_THRESHOLD:
        issues.append(f"报价陈旧（contextSlot 落后当前 {slot_lag} slots）")
    if stale_hops:
        issues.append("路线含陈旧价格源跳（updateContextSlot 异常落后）")

    if watchdog:
        if issues:
            print(f"⚠️ Jupiter @ {ts}：" + "；".join(issues))
        return 0

    print(f"\n=== Jupiter 路由快照 v2 @ {ts} ===")
    print(f"路由: {' → '.join(cur['labels'])}")
    print(f"输出: {cur['out_amount']/1e6:.4f} USDC（1 SOL）")
    print(f"contextSlot: {cur.get('context_slot')} | 当前 slot: {cur_slot} | 落后: {slot_lag}")
    print(f"最旧价格源跳: {cur.get('min_update_slot')} | timeTaken(服务器): {cur.get('time_taken')}")
    print(f"漂移: {'⚠️ 金额级不一致' if drift else '✅ 一致'}"
          f" | 路由抖动: {'🔄 秒级翻转' if route_flip else '✅ 稳定'}"
          f" | 陈旧价格源: {'⚠️ 有' if stale_hops else '✅ 无'}")
    if prev_sig is None:
        print("（首次快照，无对比基线）")
    elif confirmed_change:
        print(f"⚠️ 路由稳定变化！上次: {' → '.join(prev_labels)}")
    elif changed:
        print(f"🔄 路由跳变观察中（{cur.get('pending', 0)}/{CONFIRM_N}，需稳定确认）")
    else:
        print("✅ 路由稳定（与上次一致）")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--watchdog", action="store_true")
    ap.add_argument("--double-check", action="store_true",
                    help="每 tick 两次报价检测漂移（watchdog 模式默认开启）")
    args = ap.parse_args()

    double_check = args.double_check or args.watchdog

    code = tick(double_check, args.watchdog)
    if args.watch and not args.watchdog:
        while True:
            time.sleep(args.watch)
            tick(double_check, args.watchdog)
    return code


if __name__ == "__main__":
    sys.exit(main())
