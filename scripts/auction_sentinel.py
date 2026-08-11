#!/usr/bin/env python3
"""Maker/Sky LIQ2.0 拍卖哨兵 v1 — Dog→Clipper 荷兰式拍卖监控。

数据源：
  - RPC eth_call（ethereum.publicnode.com，走 Clash 代理 7890）：读状态/参数/价格曲线
  - Blockscout v2 API（eth.blockscout.com，直连免费）：Kick/Take 事件日志（公共 RPC
    eth_getLogs 全部受限：publicnode 需付费 archive、1rpc 限 50 blocks、cloudflare 500）

逻辑：
  1. 动态发现：IlkRegistry.list() → ilkData() 拿每个 ilk 的 clip/gem 地址（缓存 24h）
  2. 参数快照：Dog.ilks() 拿 chop/hole/dirt（治理变更可追溯）
  3. 活跃拍卖：每 clip count() > 0 → sales() 明细 + calc.price() 当前价 + 市价 → 折价率
  4. Kick/Take 事件：blockscout 按 clip 地址分页拉日志（新版 7 参签名，勿用旧文档），
     本地按 topic0 过滤，按 last_block 增量去重

告警模式（watchdog）：有任何活跃拍卖或新 Kick 即 stdout 非空（cron 推送）；正常静默。
落盘：data/maker_auctions.db（事件历史）+ data/maker_ilks.json（ilk 缓存）
       + data/auction_sentinel_state.json（已扫块号）

用法：
    python scripts/auction_sentinel.py             # 常规扫描（cron watchdog）
    python scripts/auction_sentinel.py --backfill  # 只落盘不告警（首跑初始化）
    python scripts/auction_sentinel.py --history 200  # 每个 clip 拉 N 页历史（首跑）

证据（2026-08-10 调研 notes/maker-liquidation-auction-20260810.md）：
- 新版 Kick 签名: Kick(uint256 id, uint256 top, uint256 tab, uint256 lot, address usr, address kpr, uint256 coin)
  topic0 = 0x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8
- 新版 Take 签名: Take(uint256,uint256,uint256,uint256,uint256,uint256,address)
  topic0 = 0x05e309fd6ce72f2ab888a20056bb4210df08daed86f21f95053deb19964d86b1
- ETH-A clip 最近 Kick 2026-06-05，之后 65 天零活动（低频事件流，事件驱动即可）
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
from eth_utils import keccak
import eth_abi

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "maker_auctions.db"
ILKS_CACHE = DATA_DIR / "maker_ilks.json"
STATE_FILE = DATA_DIR / "auction_sentinel_state.json"

RPC = os.environ.get("MAKER_RPC", "https://ethereum.publicnode.com")
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
BLOCKSCOUT = os.environ.get("BLOCKSCOUT", "https://eth.blockscout.com")

# 合约（Ethereum 主网，2026-08 实测）
ILK_REGISTRY = "0x5a464C28D19848f44199D003BeF5ecc87d090F87"
DOG = "0x135954d155898D42C90D2a57824C690e0c7BEf1B"

# 事件签名（新版，实测 topics/data 结构，勿用旧文档签名）
# Kick(uint256 indexed id, uint256 top, uint256 tab, uint256 lot,
#      address indexed usr, address indexed kpr, uint256 coin)
#   topics[1]=id, topics[2]=usr, topics[3]=kpr；data = (top, tab, lot, coin) 4 字段
# Take(uint256 indexed id, uint256 top, uint256 tab, uint256 lot,
#      uint256 wad, uint256 coin, address indexed usr)
#   topics[1]=id, topics[2]=usr；data = (top, tab, lot, wad, coin) 5 字段
# 单位：top=ray(1e27), tab/coin=rad(1e45), lot=wad(1e18)
KICK_TOPIC = "0x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8"
TAKE_TOPIC = "0x05e309fd6ce72f2ab888a20056bb4210df08daed86f21f95053deb19964d86b1"
KICK_DATA_ABI = ["uint256", "uint256", "uint256", "uint256"]   # top, tab, lot, coin
TAKE_DATA_ABI = ["uint256", "uint256", "uint256", "uint256", "uint256"]  # top, tab, lot, wad, coin
RAY = 1e27
RAD = 1e45

# 折价率计算用的市价源（CoinGecko，免费无 key）；gem 地址 → coingecko id
CG_ID_MAP = {
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "ethereum",       # WETH
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": "bitcoin",        # WBTC
    "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0": "wrapped-steth",  # WSTETH
    "0x56072c95faa701256059aa122697b94aded8296f": "sky",            # SKY
    "0x056fd409e1d7a124bd7017459dfea2f387b6d5cd": "gemini-dollar",  # GUSD
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "usd-coin",       # USDC
    "0x8e870d67f660d95d5be530380d0ec0bd388289e1": "paxos-standard", # PAX
    "0x50379f632ca68d36e50cfbc8f78fe16bd1499ad7": "univ3daiusdc",   # GUNIV3DAIUSDC2
    "0xabddafb225e10b90d798bb8a886238fb835e2053": "univ3daiusdc",   # GUNIV3DAIUSDC1
    "0xae461ca67b15dc8dc81ce7615e0320daa1ab8da5": "uniswap",        # UNIV2DAIUSDC (approx)
}

DEFAULT_PAGES = 2      # 每个 clip 常规拉几页日志（每页 50 条）
MAX_PAGES = 10         # 单次最多翻页数（防止失控）
CACHE_TTL_HOURS = 24   # ilk 缓存刷新周期


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def rpc(method, params, timeout=20):
    r = requests.post(
        RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        headers={"Content-Type": "application/json"},
        proxies={"http": PROXY, "https": PROXY},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def sel(sig):
    return "0x" + keccak(text=sig)[:4].hex()


def eth_call(to, data, block="latest"):
    res = rpc("eth_call", [{"to": to, "data": data}, block])
    if "result" not in res:
        raise RuntimeError(f"eth_call revert: {to} {data[:10]} -> {res.get('error', {}).get('message', '')}")
    return res["result"]


def get_ilks(refresh=False):
    """IlkRegistry → (ilk名, clip地址, gem地址) 列表。缓存 24h。"""
    if ILKS_CACHE.exists() and not refresh:
        age_h = (time.time() - ILKS_CACHE.stat().st_mtime) / 3600
        if age_h < CACHE_TTL_HOURS:
            return json.loads(ILKS_CACHE.read_text())

    res = rpc("eth_call", [{"to": ILK_REGISTRY, "data": sel("list()")}, "latest"])
    ilks = eth_abi.decode(["bytes32[]"], bytes.fromhex(res["result"][2:]))[0]

    ilkdata_sel = sel("ilkData(bytes32)")
    rows = []
    for ilk in ilks:
        name = ilk.decode().rstrip("\x00")
        try:
            out = eth_call(ILK_REGISTRY, ilkdata_sel + ilk.hex())
            vals = eth_abi.decode(
                ["uint256", "address", "address", "uint256", "uint256", "address", "address", "string"],
                bytes.fromhex(out[2:]),
            )
            rows.append({"ilk": name, "clip": vals[6].lower(), "gem": vals[2].lower()})
        except Exception:
            rows.append({"ilk": name, "clip": "0x" + "0" * 40, "gem": "0x" + "0" * 40})

    ILKS_CACHE.parent.mkdir(exist_ok=True)
    ILKS_CACHE.write_text(json.dumps(rows, ensure_ascii=False))
    return rows


def dog_ilks(ilk_name):
    """Dog.ilks(bytes32) → (clip, chop, hole, dirt)。chop=wad(1e18), hole/dirt=rad(1e45)。"""
    key = ilk_name.encode().ljust(32, b"\x00").hex()
    out = eth_call(DOG, sel("ilks(bytes32)") + key)
    clip, chop, hole, dirt = eth_abi.decode(
        ["address", "uint256", "uint256", "uint256"], bytes.fromhex(out[2:])
    )
    return clip.lower(), chop / 1e18, hole / RAD, dirt / RAD


def clip_count(clip):
    out = eth_call(clip, sel("count()"))
    return int(out, 16)


def clip_sales(clip, aid):
    """Clipper.sales(uint256) → (pos, tab, lot, usr, tic, top)。tab=rad, lot=wad, top=ray。"""
    out = eth_call(clip, sel("sales(uint256)") + aid.to_bytes(32, "big").hex())
    pos, tab, lot, usr, tic, top = eth_abi.decode(
        ["uint256", "uint256", "uint256", "address", "uint256", "uint256"],
        bytes.fromhex(out[2:]),
    )
    return pos, tab / RAD, lot / 1e18, usr, tic, top / RAY


def calc_price(clip, top, tic, now_ts):
    """拍卖当前价（USDS/抵押品）= calc.price(top, tic, now)。top 为 ray 小数，转回整数。"""
    try:
        out = eth_call(clip, sel("calc()"))
        calc = "0x" + out[-40:]
        top_raw = round(top * RAY)
        price_out = eth_call(
            calc,
            sel("price(uint256,uint256,uint256)")
            + top_raw.to_bytes(32, "big").hex()
            + tic.to_bytes(32, "big").hex()
            + now_ts.to_bytes(32, "big").hex(),
        )
        return int(price_out, 16) / 1e18
    except Exception:
        return None


def market_price(gem_addr):
    """CoinGecko 简单市价（gem → id 映射，无映射返回 None）。"""
    cg_id = CG_ID_MAP.get(gem_addr)
    if not cg_id:
        return None
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": cg_id, "vs_currencies": "usd"},
            proxies={"http": PROXY, "https": PROXY},
            timeout=15,
        )
        r.raise_for_status()
        return (r.json().get(cg_id) or {}).get("usd")
    except Exception:
        return None


def fetch_clip_logs(clip, from_block, max_pages):
    """Blockscout 分页拉 clip 日志，本地过滤 Kick/Take。返回 [(topics, data, block, tx)]。"""
    out = []
    url = f"{BLOCKSCOUT}/api/v2/addresses/{clip}/logs"
    params = None
    for _ in range(max_pages):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
        except Exception as e:
            break
        d = r.json()
        items = d.get("items", [])
        for it in items:
            t0 = (it.get("topics") or [None])[0]
            if t0 in (KICK_TOPIC, TAKE_TOPIC):
                blk = it.get("block_number")
                out.append((it.get("topics") or [], it.get("data", "0x"), blk, it.get("transaction_hash")))
        npp = d.get("next_page_params")
        if not npp:
            break
        # 到达 last_block 就停
        min_blk = min((it.get("block_number") or 0) for it in items) if items else 0
        if min_blk <= from_block:
            break
        params = {"block_number": npp.get("block_number"), "index": npp.get("index"),
                  "items_count": npp.get("items_count")}
    return out


def init_db(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS auction_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT, ilk TEXT, clip TEXT, auction_id TEXT, block INTEGER, tx TEXT,
        top REAL, tab REAL, lot REAL, usr TEXT, kpr TEXT, coin REAL,
        auction_price REAL, market_price REAL, discount REAL, seen_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ilk_snapshots (
        ts TEXT, ilk TEXT, clip TEXT, chop REAL, hole REAL, dirt REAL, active_count INTEGER
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_evt ON auction_events(event_type, auction_id)")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_block": 0}


def save_state(st):
    STATE_FILE.write_text(json.dumps(st))


def main():
    ap = argparse.ArgumentParser(description="Maker LIQ2.0 拍卖哨兵 v1")
    ap.add_argument("--backfill", action="store_true", help="只落盘不告警（首跑）")
    ap.add_argument("--quiet", action="store_true", help="无异动静默（cron watchdog）")
    ap.add_argument("--history", type=int, default=DEFAULT_PAGES,
                    help="每个 clip 拉日志的翻页数（每页 50 条）")
    ap.add_argument("--refresh-ilks", action="store_true", help="强制刷新 ilk 缓存")
    args = ap.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    init_db(conn)

    alerts = []
    errors = []
    latest_hex = rpc("eth_blockNumber", [])["result"]
    latest = int(latest_hex, 16)
    now_ts = int(time.time())

    # ── 1. ilk 发现 + 参数快照 + count() 轮询 ──
    ilks = get_ilks(refresh=args.refresh_ilks)
    for row in ilks:
        name, clip = row["ilk"], row["clip"]
        if clip == "0x" + "0" * 40:
            continue
        try:
            clip_addr, chop, hole, dirt = dog_ilks(name)
            cnt = clip_count(clip_addr)
            conn.execute(
                "INSERT INTO ilk_snapshots VALUES (?,?,?,?,?,?,?)",
                (now_iso(), name, clip_addr, chop, hole, dirt, cnt),
            )
            conn.commit()  # 每 ilk 提交，避免长事务磁盘错误
            if cnt > 0:
                out = eth_call(clip_addr, sel("list()"))
                aids = eth_abi.decode(["uint256[]"], bytes.fromhex(out[2:]))[0]
                for aid in aids[:20]:
                    pos, tab, lot, usr, tic, top = clip_sales(clip_addr, int(aid))
                    price = calc_price(clip_addr, top, tic, now_ts)
                    mkt = market_price(row["gem"])
                    disc = ((mkt - price) / mkt * 100) if (mkt and price and mkt > 0) else None
                    alerts.append({
                        "ilk": name, "clip": clip_addr, "aid": int(aid),
                        "tab": tab, "lot": lot, "usr": usr,
                        "tic": tic, "top": top,
                        "auction_price": price, "market_price": mkt, "discount": disc,
                    })
        except Exception as e:
            errors.append(f"{name}: {e}")

    # ── 2. Kick/Take 事件增量扫描（blockscout）──
    st = load_state()
    from_block = st.get("last_block", 0)
    ilk_by_clip = {r["clip"]: r["ilk"] for r in ilks}
    for row in ilks:
        clip = row["clip"]
        if clip == "0x" + "0" * 40:
            continue
        try:
            for topic0, data, blk, tx in fetch_clip_logs(clip, from_block, args.history):
                if blk is None or blk <= from_block:
                    continue
                ilk_name = ilk_by_clip.get(clip, clip[:10])
                # 注意：fetch_clip_logs 现在返回 (topics, data, block, tx)，topics 含 id/usr/kpr
                topics = topic0
                if topics[0] == KICK_TOPIC:
                    # topics[1]=id, [2]=usr, [3]=kpr；data = (top, tab, lot, coin)
                    aid = int(topics[1], 16)
                    usr = "0x" + topics[2][-40:]
                    kpr = "0x" + topics[3][-40:] if len(topics) > 3 and topics[3] else ""
                    vals = eth_abi.decode(KICK_DATA_ABI, bytes.fromhex(data[2:]))
                    top, tab, lot, coin = vals
                    row_vals = ("KICK", ilk_name, clip, str(aid), blk, tx,
                                top / RAY, tab / RAD, lot / 1e18, usr, kpr, coin / RAD,
                                None, None, None, now_iso())
                else:
                    # Take(id indexed, max, price, owe, tab, lot, usr indexed)
                    #   topics[1]=id, topics[2]=usr；data = (max, price, owe, tab, lot)
                    #   price=ray(1e27), owe/tab=rad(1e45), lot=wad(1e18), max 可能超大(不限价)
                    aid = int(topics[1], 16)
                    usr = "0x" + topics[2][-40:] if len(topics) > 2 and topics[2] else ""
                    vals = eth_abi.decode(TAKE_DATA_ABI, bytes.fromhex(data[2:]))
                    max_p, price, owe, tab, lot = vals
                    row_vals = ("TAKE", ilk_name, clip, str(aid), blk, tx,
                                price / RAY, tab / RAD, lot / 1e18, usr, "", owe / RAD,
                                None, None, None, now_iso())
                dup = conn.execute(
                    "SELECT 1 FROM auction_events WHERE event_type=? AND auction_id=? AND tx=?",
                    (row_vals[0], row_vals[3], row_vals[5]),
                ).fetchone()
                if not dup:
                    conn.execute(
                        "INSERT INTO auction_events VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        row_vals,
                    )
                    conn.commit()  # 每事件提交，避免长事务磁盘错误
                    if not args.backfill and row_vals[0] == "KICK":
                        alerts.append({
                            "ilk": row_vals[1], "clip": row_vals[2], "aid": int(row_vals[3]),
                            "tab": row_vals[8], "lot": row_vals[9], "usr": row_vals[10],
                            "kpr": row_vals[11], "top": row_vals[7],
                            "auction_price": None, "market_price": None, "discount": None,
                            "kick_tx": row_vals[5], "block": row_vals[4],
                        })
        except Exception as e:
            errors.append(f"logs {clip[:10]}: {e}")

    st["last_block"] = latest
    try:
        conn.commit()
        save_state(st)  # 仅提交成功后才推进已扫块号
    except sqlite3.OperationalError as e:
        errors.append(f"final commit: {e}")
    conn.close()

    for e in errors:
        print(f"[err] {e}", file=sys.stderr)

    # ── 3. 告警输出（watchdog：非空即推送）──
    if alerts:
        print(f"🔨 Maker LIQ2.0 拍卖告警（{now_iso()}）— {len(alerts)} 条：")
        for a in alerts:
            if a.get("kick_tx"):
                print(f"  ⚡ NEW KICK {a['ilk']} clip={a['clip'][:10]}… id={a['aid']} "
                      f"top=${a['top']:,.4f} tab=${a['tab']:,.2f} lot={a['lot']:,.4f}")
                print(f"     tx: https://etherscan.io/tx/{a['kick_tx']} (blk {a['block']})")
            else:
                d = a.get("discount")
                d_s = f"{d:+.2f}%" if d is not None else "市价未知"
                p_s = f"${a['auction_price']:,.4f}" if a.get("auction_price") else "价格待算"
                print(f"  🔴 活跃拍卖 {a['ilk']} id={a['aid']} tab=${a['tab']:,.2f} "
                      f"lot={a['lot']:,.4f} 当前价 {p_s} vs 市价 ${a['market_price'] or '?'} → 折价 {d_s}")
                print(f"     usr={a['usr'][:10]}… tic={a['tic']}")
    elif not args.backfill and not args.quiet:
        print(f"无活跃拍卖，无新 Kick（latest blk {latest}，已扫至 {st['last_block']}）")


if __name__ == "__main__":
    main()
