#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
狗庄出货雷达 v1（whale_dump_radar.py）— 2026-08-15 凌晨
=========================================================
监控「巨鲸拉盘→合约出货」模式（HFT 案例 0x4bfd879f 沉淀的信号原型）：
  ① 巨鲸地址向外部大额转出代币（供币/出货）
  ② 该代币近期暴涨（24h/7d 涨幅超阈值）→ 狗庄拉盘特征
  ③ 同一代币 1 小时内从巨鲸流出 ≥N 笔 → 密集出货

数据源（全部免费，0 成本）：
  - blockscout v2 API：巨鲸地址的 token-transfers（方向 + 金额）
  - CoinGecko：代币现价 + 24h/7d 涨幅（按 contract address）

用法：
  python scripts/whale_dump_radar.py              # 单次扫描
  python scripts/whale_dump_radar.py --watchdog   # cron：无信号静默，有信号才输出
  python scripts/whale_dump_radar.py --whale 0x…  # 追加监控巨鲸

输出：data/whale_dump_radar_YYYYMMDD.jsonl + stdout（人话版）
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 已确认的巨鲸归集地址（HFT 案例实证：0x28C6c06298d514 余额 212,311 ETH）
DEFAULT_WHALES = [
    "0x28C6c06298d514Db089934071355E5743bf21d60",  # HFT 案例归集巨鲸
]

# 阈值（可调）
OUT_MIN_USD = 5_000        # 单笔流出价值下限（USD）
PUMP_24H = 1.00            # 24h 涨幅 ≥100% 标记
PUMP_7D = 3.00             # 7d 涨幅 ≥300% 标记（狗庄拉盘特征）
DENSE_OUT_MIN = 3          # 同代币 1h 内流出笔数 ≥N = 密集出货
LOOKBACK_H = 1             # 扫描窗口（小时）


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def blockscout_transfers(addr, pages=3):
    """blockscout 拉地址最近 token 转账（翻页，默认 3 页 ≈ 150 笔）"""
    items = []
    url = f"https://eth.blockscout.com/api/v2/addresses/{addr}/token-transfers"
    for _ in range(pages):
        d = get_json(url)
        items.extend(d.get("items", []))
        npp = d.get("next_page_params")
        if not npp:
            break
        qs = "&".join(f"{k}={v}" for k, v in npp.items())
        url = f"https://eth.blockscout.com/api/v2/addresses/{addr}/token-transfers?{qs}"
    return items


def coingecko_price(token_addr):
    """按合约地址查现价 + 24h/7d 涨幅（返回 None 表示查不到）"""
    try:
        d = get_json(f"https://api.coingecko.com/api/v3/coins/ethereum/contract/{token_addr}")
        md = d.get("market_data", {})
        return {
            "symbol": d.get("symbol", "?"),
            "usd": (md.get("current_price") or {}).get("usd"),
            "chg_24h": md.get("price_change_percentage_24h"),
            "chg_7d": md.get("price_change_percentage_7d_in_currency", {}).get("usd"),
        }
    except Exception:
        return None


def scan(whales, lookback_h=LOOKBACK_H, watchdog=False):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now = time.time()
    signals = []
    rows = []

    for whale in whales:
        if not watchdog:
            print(f"👁 巨鲸 {whale[:14]}…")
        try:
            transfers = blockscout_transfers(whale)
        except Exception as e:
            print(f"  ❌ 拉取失败: {str(e)[:80]}")
            continue

        # 窗口内 OUT 大额转账
        out_by_token = {}
        for t in transfers:
            frm = (t.get("from") or {}).get("hash", "").lower()
            to = (t.get("to") or {}).get("hash", "").lower()
            if frm.lower() != whale.lower():
                continue  # 只看巨鲸流出
            try:
                ts_t = datetime.fromisoformat(t["timestamp"].replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if now - ts_t > lookback_h * 3600:
                continue
            tok = t.get("token") or {}
            token_addr = tok.get("address", "")
            decimals = tok.get("decimals", 18)
            try:
                val = float(t.get("total", {}).get("value", 0)) / (10 ** decimals)
            except Exception:
                continue
            out_by_token.setdefault(token_addr, []).append({
                "to": to, "amount": val, "ts": t["timestamp"][:19], "symbol": tok.get("symbol", "?")
            })

        for token_addr, outs in out_by_token.items():
            if len(outs) < 1:
                continue
            price = coingecko_price(token_addr) if token_addr else None
            if not price or not price.get("usd"):
                continue
            usd_total = sum(o["amount"] for o in outs) * price["usd"]
            chg24 = price.get("chg_24h") or 0
            chg7 = price.get("chg_7d") or 0
            pump = chg24 >= PUMP_24H * 100 or chg7 >= PUMP_7D * 100
            dense = len(outs) >= DENSE_OUT_MIN

            if usd_total >= OUT_MIN_USD and pump:
                sig = {
                    "ts": ts, "whale": whale, "token": token_addr,
                    "symbol": price["symbol"], "out_usd": round(usd_total, 0),
                    "chg_24h": round(chg24, 1), "chg_7d": round(chg7, 1),
                    "n_out": len(outs), "dense": dense,
                    "top_to": outs[0]["to"][:16],
                }
                signals.append(sig)
                rows.append(sig)
                level = "🔴" if (chg24 >= 200 or chg7 >= 500) else "🟠"
                line = (f"{level} 疑似狗庄出货: {price['symbol']} "
                        f"巨鲸{whale[:10]}…流出 ${usd_total:,.0f} "
                        f"(24h {chg24:+.0f}% / 7d {chg7:+.0f}%) {len(outs)}笔"
                        f"{' 密集!' if dense else ''} | 去向 {sig['top_to']}…")
                if watchdog:
                    print(line)
                else:
                    print(f"  {line}")
            elif not watchdog:
                print(f"  ⚪ {price['symbol']} 流出 ${usd_total:,.0f} (24h {chg24:+.0f}%) 未达信号")

    # 落盘
    if rows:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        outfile = DATA_DIR / f"whale_dump_radar_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        with open(outfile, "a") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n💾 落盘 {outfile}")

    if not signals:
        if not watchdog:
            print("\n✅ 无信号（全绿）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watchdog", action="store_true", help="cron 模式：无信号静默，有信号才输出")
    ap.add_argument("--whale", action="append", default=[], help="追加监控巨鲸地址")
    ap.add_argument("--lookback", type=int, default=LOOKBACK_H, help="扫描窗口（小时）")
    args = ap.parse_args()

    whales = list(dict.fromkeys(DEFAULT_WHALES + args.whale))
    try:
        scan(whales, lookback_h=args.lookback, watchdog=args.watchdog)
    except Exception as e:
        print(f"❌ 失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
