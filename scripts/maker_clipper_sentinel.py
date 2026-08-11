#!/usr/bin/env python3
"""Maker LIQ2.0 拍卖哨兵 v1 — Clipper 荷兰式拍卖监控（2026-08-11 建）。

数据源：ETH 主网公共 RPC（eth_call 直读链上状态，走 Clash 代理）
逻辑：轮询所有 ilk 的 Clipper.count() -> >0 即告警 + 拉 sales() 明细 + 折价估算
定位：低频事件流（几个月一波）-> 哨兵 = 「在场」+ 事件驱动，不是高频扫描

告警规则：
- 任一 clip count() > 0 即告警（含 ilk / 拍卖 id / lot / tab / 当前价）
- watchdog（--watchdog）模式：无活跃拍卖静默，有才输出

用法：
    python scripts/maker_clipper_sentinel.py            # 轮询+检测
    python scripts/maker_clipper_sentinel.py --watchdog # cron 静默模式
    python scripts/maker_clipper_sentinel.py --verbose  # 全 ilk 明细输出
环境变量：PROXY（默认 http://127.0.0.1:7890），RPC_URL 可覆盖
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "maker_clipper.db"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY} if os.environ.get("NO_PROXY") != "1" else None

RPC_URL = os.environ.get("RPC_URL", "https://eth.drpc.org")
# 实测可用（2026-08-11）：drpc / publicnode / merkle / 1rpc / blastapi
RPC_FALLBACKS = [
    "https://eth.drpc.org",
    "https://ethereum-rpc.publicnode.com",
    "https://eth.merkle.io",
    "https://1rpc.io/eth",
    "https://eth-mainnet.public.blastapi.io",
]

# ── 合约地址（2026-08-10 实测，Sky/Maker 主网） ──────────────────────────
DOG = "0x135954d155898D42C90D2a57824C690e0c7BEf1B"
ILK_REGISTRY = "0x5a464C28D19848f44199D003BeF5ecc87d090F87"  # IlkRegistry.list()

# ── Selectors（cast sig 生成，2026-08-11 验证） ──────────────────────────
SEL_LIST = "0x0f560cd7"      # IlkRegistry.list() -> bytes32[]
SEL_ILKS = "0xd9638d36"      # Dog.ilks(bytes32) -> (clip, cup, chop, hole, dirt)
SEL_COUNT = "0x06661abd"     # Clipper.count() -> uint256
SEL_SALES = "0xb5f522f7"     # Clipper.sales(uint256) -> (pos, tab, lot, usr, tic, top)

# 新版 Kick 事件 topic0（2026 实测签名，旧 8 参签名已废弃勿用）
KICK_TOPIC = "0x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8"

RETRY = 3
TIMEOUT = 20
SLEEP_BETWEEN = 0.25  # 轮询 17+ ilk 之间 sleep，避免公共 RPC 限流


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def rpc_call(session, method, params, rpc_url=None):
    """带重试的 JSON-RPC 调用；限流/失败时自动 fallback 到备用 RPC。"""
    urls = [rpc_url] if rpc_url else [RPC_URL] + [u for u in RPC_FALLBACKS if u != RPC_URL]
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    last_err = None
    for url in urls:
        for attempt in range(RETRY):
            try:
                r = session.post(url, json=body, timeout=TIMEOUT)
                r.raise_for_status()
                d = r.json()
                if "error" in d:
                    last_err = d["error"]
                    time.sleep(2 * (attempt + 1))
                    continue
                return d.get("result")
            except Exception as e:  # noqa: BLE001
                last_err = str(e)
                time.sleep(1 * (attempt + 1))
    raise RuntimeError(f"RPC {method} failed (all endpoints): {last_err}")


def eth_call(session, to, data):
    """eth_call -> 原始 hex。"""
    return rpc_call(session, "eth_call", [{"to": to, "data": data}, "latest"])


def to_checksum(addr_hex):
    return "0x" + addr_hex[-40:]


def parse_ilk_list(hex_data):
    """list() 返回 bytes32[]：offset + len + 各 32 字节。"""
    if not hex_data or hex_data == "0x":
        return []
    raw = bytes.fromhex(hex_data[2:])
    offset = int.from_bytes(raw[0:32], "big")
    n = int.from_bytes(raw[offset:offset + 32], "big")
    ilks = []
    for i in range(n):
        b = raw[offset + 32 + i * 32: offset + 64 + i * 32]
        ilks.append(b.rstrip(b"\x00").decode("ascii", errors="replace"))
    return ilks


def parse_ilks_result(hex_data):
    """Dog.ilks(bytes32) -> (clip, cup, chop, hole, dirt)。"""
    raw = bytes.fromhex(hex_data[2:])
    clip = "0x" + raw[12:32].hex()
    chop = int.from_bytes(raw[64:96], "big")
    hole = int.from_bytes(raw[96:128], "big")
    dirt = int.from_bytes(raw[128:160], "big")
    return {"clip": clip, "chop": chop, "hole": hole, "dirt": dirt}


def parse_count(hex_data):
    return int(hex_data, 16) if hex_data else 0


def parse_sales(hex_data):
    """Clipper.sales(uint256) -> (pos, tab, lot, usr, tic, top) 6 个槽。"""
    raw = bytes.fromhex(hex_data[2:])
    return {
        "pos": int.from_bytes(raw[0:32], "big"),
        "tab": int.from_bytes(raw[32:64], "big"),
        "lot": int.from_bytes(raw[64:96], "big"),
        "usr": "0x" + raw[108:128].hex(),
        "tic": int.from_bytes(raw[128:160], "big"),
        "top": int.from_bytes(raw[160:192], "big"),
    }


def ilk_bytes32(ilk: str) -> str:
    b = ilk.encode("ascii")
    return "0x" + b.hex().ljust(64, "0")


def fetch_all_ilks(session):
    """从 IlkRegistry.list() 拉全部 ilk，再查 Dog.ilks 拿 clip/chop 等。"""
    hex_list = eth_call(session, ILK_REGISTRY, SEL_LIST)
    ilks = parse_ilk_list(hex_list)
    out = []
    for ilk in ilks:
        hex_ilks = eth_call(session, DOG, SEL_ILKS + ilk_bytes32(ilk)[2:])
        info = parse_ilks_result(hex_ilks)
        info["ilk"] = ilk
        out.append(info)
        time.sleep(SLEEP_BETWEEN)
    return out


def main():
    ap = argparse.ArgumentParser(description="Maker LIQ2.0 Clipper 拍卖哨兵")
    ap.add_argument("--watchdog", action="store_true", help="cron 静默模式：无拍卖不输出")
    ap.add_argument("--verbose", action="store_true", help="输出全 ilk 明细")
    ap.add_argument("--rpc", default=None, help="覆盖 RPC URL")
    args = ap.parse_args()

    rpc_url = args.rpc or RPC_URL
    session = requests.Session()
    if PROXIES:
        session.proxies = PROXIES

    try:
        ilks = fetch_all_ilks(session)
    except Exception as e:  # noqa: BLE001
        print(f"❌ RPC 拉取失败: {e}", file=sys.stderr)
        sys.exit(2)

    active = []
    for info in ilks:
        clip = info["clip"]
        if clip == "0x" + "0" * 40:
            continue  # 无 clip 的 ilk（RWA 特殊清算路径）
        try:
            cnt = parse_count(eth_call(session, clip, SEL_COUNT))
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ {info['ilk']} clip 查询失败: {e}", file=sys.stderr)
            continue
        info["count"] = cnt
        if cnt > 0:
            sales = []
            for aid in range(cnt):
                hex_s = eth_call(session, clip, SEL_SALES + f"{aid:064x}")
                sales.append(parse_sales(hex_s))
                time.sleep(SLEEP_BETWEEN)
            info["sales"] = sales
            active.append(info)
        time.sleep(SLEEP_BETWEEN)

    # 落库（去重：clip + auction id）
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS auctions (
            ilk TEXT, clip TEXT, auction_id INTEGER, tab INTEGER, lot INTEGER,
            usr TEXT, tic INTEGER, top INTEGER, chop INTEGER, seen_at TEXT,
            PRIMARY KEY (clip, auction_id))"""
    )
    new_events = 0
    for info in active:
        for aid, s in enumerate(info["sales"]):
            cur = conn.execute(
                "SELECT 1 FROM auctions WHERE clip=? AND auction_id=?",
                (info["clip"], aid),
            )
            if cur.fetchone() is None:
                conn.execute(
                    "INSERT OR REPLACE INTO auctions VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        info["ilk"], info["clip"], aid, s["tab"], s["lot"],
                        s["usr"], s["tic"], s["top"], info["chop"], now_iso(),
                    ),
                )
                new_events += 1
    conn.commit()
    conn.close()

    if not args.watchdog or active or new_events:
        if not active:
            print(f"✅ 全系统 {len(ilks)} ilk 活跃拍卖 = 0（{now_iso()}）" if args.verbose or not args.watchdog else "")
        for info in active:
            chop = info["chop"] / 1e18
            for aid, s in enumerate(info["sales"]):
                lot = s["lot"] / 1e18
                tab = s["tab"] / 1e18
                top = s["top"] / 1e18
                print(
                    f"🚨 Maker 拍卖活跃: ilk={info['ilk']} id={aid} "
                    f"lot={lot:.4f} tab={tab:.2f} USDS top={top:.4f} "
                    f"chop={chop:.4f} usr={s['usr']}"
                )
    if new_events and not args.watchdog:
        print(f"（新入库 {new_events} 条拍卖记录）")


if __name__ == "__main__":
    main()
