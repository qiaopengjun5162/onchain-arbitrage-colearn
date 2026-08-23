#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安 ETF 合约涨幅差监控（binance_etf_spread_monitor.py）— 2026-08-23 D19
========================================================================
币股 RWA 线新数据源（binance-etf-contract-arb 笔记落地项）。

逻辑（JXiaoLoong 框架）：
- 杠杆型 ETF 永续（SNXX 2x SNDK）与其标的（SNDK）存在「每日涨幅差」
- 涨幅差 = ETF 当日涨幅 - K × 标的当日涨幅（K=杠杆倍数）
- 标的涨幅用 ETF 自身隐含：K 倍做多的 ETF，其涨幅应 ≈ K × 标的涨幅 → 差 = 套利空间
- **周末窗口**：美股休市无 AP 抹平 + 涨幅不重置（周一收盘才重置）→ 价差可拉大到 4%+
- watchdog：涨幅差偏离 ≥ 阈值 → 推送（可做多 ETF + K 倍做空标的，赌收敛）

数据源（全部免 key）：
- Binance fapi 永续 24h ticker（ETF 合约现价/24h 量）— data-api 镜像不封
- 标的参考价：同合约体系内对应永续（SNDKUSDT 即标的代币合约）——用「标的相关永续」当日涨幅近似

⚠️ 简化假设：无美股实时 API 时用币安上的标的代币永续价格代表美股（周末休市但永续照常交易，价格≈美股收盘价+情绪漂移）——这正是「闭市漂移」本身，监控的就是它。

用法：
  python binance_etf_spread_monitor.py              # 全量输出（调试）
  python binance_etf_spread_monitor.py --quiet      # watchdog：有信号才输出
  python binance_etf_spread_monitor.py --history 5  # 输出近 N 次快照

部署：cron 每 15 分钟（可 7×24），wrapper 见 run_binance_etf.sh
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
BASE_DIR = Path(__file__).resolve().parent.parent
HIST_PATH = BASE_DIR / "data" / "binance_etf_spread.jsonl"

# ETF 合约 -> (标的永续, 杠杆倍数, 方向)  — 帖子里提到的可套对
ETF_MAP = {
    "SNXXUSDT": ("SNDKUSDT", 2, 1),    # SNDK 2x 做多
    "MUUUSDT":  ("MUUSDT",   2, 1),    # MU 2x 做多
    "INTWUSDT": ("INTCUSDT", 2, 1),    # INTC 2x 做多
    "MVLLUSDT": ("MRVLUSDT", 2, 1),    # MRVL 2x 做多
    "SOXLUSDT": ("SMHUSDT",  3, 1),    # 半导体 3x 做多（SOX 指数用 SMH 近似）
    "SOXSUSDT": ("SMHUSDT",  3, -1),   # 半导体 3x 做空
    "TQQQUSDT": ("QQQUSDT",  3, 1),    # QQQ 3x 做多
    "SQQQUSDT": ("QQQUSDT",  3, -1),   # QQQ 3x 做空
    "KORUUSDT": ("EWYUSDT",  3, 1),    # EWY(韩国) 3x 做多
}

# 信号阈值
THRESHOLD_BPS = int(os.environ.get("THRESHOLD_BPS", "100"))   # 涨幅差偏离 ≥1% 推送
VOL_MIN = float(os.environ.get("VOL_MIN", "500000"))          # ETF 24h 量 ≥$500K 才扫


def http_json(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    return json.loads(opener.open(req, timeout=timeout).read())


def fetch_tickers():
    """fapi 24h ticker → {sym: {px, vol24h}} + 当日 open（1d kline 第一根，UTC 0 点基准，对应「每日重置」）"""
    out = {}
    try:
        tickers = http_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
        for t in tickers:
            sym = t["symbol"]
            out[sym] = {
                "px": float(t["lastPrice"]),
                "open": float(t["openPrice"]),
                "vol24h": float(t["quoteVolume"]),
            }
    except Exception as e:
        print(f"[!] fapi ticker 拉取失败: {str(e)[:100]}", file=sys.stderr)
    return out


def fetch_daily_open(symbols):
    """1d kline → {sym: 今日 open}（UTC 0 点重置基准，ETF 每日重置语义）"""
    out = {}
    for sym in symbols:
        try:
            url = (f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}"
                   f"&interval=1d&limit=1")
            k = http_json(url)[0]
            out[sym] = float(k[1])  # open
        except Exception:
            pass
    return out


def compute(tickers, daily_open):
    """计算所有 ETF 对的涨幅差（bps）。返回 [{etf, base, k, direction, etf_ret, base_ret, exp_ret, dev_bps, vol}]"""
    rows = []
    for etf, (base, k, direction) in ETF_MAP.items():
        t_etf = tickers.get(etf)
        t_base = tickers.get(base)
        if not t_etf or not t_base:
            continue
        if t_etf["vol24h"] < VOL_MIN:
            continue
        # 当日涨幅 = (现价 - 今日0点open) / open（每日重置基准）
        etf_open = daily_open.get(etf) or t_etf["open"]
        base_open = daily_open.get(base) or t_base["open"]
        etf_ret = (t_etf["px"] - etf_open) / etf_open
        base_ret = (t_base["px"] - base_open) / base_open
        # 期望 ETF 涨幅 = K 倍标的涨幅（direction=1 做多 / -1 做空）
        exp_ret = k * direction * base_ret
        dev = (etf_ret - exp_ret) * 1e4  # bps，正 = ETF 跑赢期望（标的超涨）
        rows.append({
            "etf": etf, "base": base, "k": k, "direction": direction,
            "etf_ret_bps": round(etf_ret * 1e4, 1),
            "base_ret_bps": round(base_ret * 1e4, 1),
            "exp_ret_bps": round(exp_ret * 1e4, 1),
            "dev_bps": round(dev, 1),
            "etf_px": t_etf["px"], "base_px": t_base["px"],
            "vol24h": t_etf["vol24h"],
        })
    rows.sort(key=lambda r: abs(r["dev_bps"]), reverse=True)
    return rows


def log_history(rows):
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(HIST_PATH, "a") as f:
            f.write(json.dumps({"ts": ts, "rows": rows}, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[!] 历史落盘失败: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="币安 ETF 合约涨幅差监控（周末窗口）")
    ap.add_argument("--quiet", action="store_true", help="watchdog：有偏离信号才输出")
    ap.add_argument("--threshold-bps", type=float, default=THRESHOLD_BPS)
    ap.add_argument("--history", type=int, default=0, help="输出近 N 次历史快照")
    args = ap.parse_args()

    tickers = fetch_tickers()
    # 拉所有相关标的的当日 open（1d kline）
    all_syms = set()
    for etf, (base, _, _) in ETF_MAP.items():
        all_syms.add(etf)
        all_syms.add(base)
    daily_open = fetch_daily_open(list(all_syms))
    rows = compute(tickers, daily_open)
    log_history(rows)

    if args.history > 0 and HIST_PATH.exists():
        lines = HIST_PATH.read_text(encoding="utf-8").splitlines()
        print(f"=== 近 {args.history} 次快照（{len(lines)} 条累计）===")
        for line in lines[-args.history:]:
            rec = json.loads(line)
            sig = [r for r in rec["rows"] if abs(r["dev_bps"]) >= args.threshold_bps]
            print(f"{rec['ts'][:16]} | {len(sig)} 信号 / {len(rec['rows'])} 对: "
                  + ", ".join(f"{r['etf'][:4]}{r['dev_bps']:+.0f}bps" for r in sig[:5]) or "无")
        return

    signals = [r for r in rows if abs(r["dev_bps"]) >= args.threshold_bps]

    if args.quiet:
        if signals:
            print(f"🔴 币安ETF涨幅差: {len(signals)} 个信号 (阈值 {args.threshold_bps:.0f}bps)")
            for r in signals[:10]:
                side = "做多ETF+做空标的" if r["dev_bps"] > 0 else "做空ETF+做多标的"
                print(f"  {r['etf']:<10} vs {r['base']:<9} 偏离 {r['dev_bps']:>+7.1f}bps "
                      f"(ETF {r['etf_ret_bps']:+.1f} vs {r['k']}x{r['base'][:4]} {r['exp_ret_bps']:+.1f}) → {side}")
        return

    print(f"=== 币安 ETF 涨幅差 {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC ===")
    print(f"扫描 {len(rows)} 个 ETF 对 | 阈值 {args.threshold_bps:.0f}bps | 24h量≥${VOL_MIN:,.0f}")
    print(f"信号: {len(signals)}")
    print()
    for r in rows:
        mark = "🔴" if abs(r["dev_bps"]) >= args.threshold_bps else "  "
        side = "做多ETF+空标的" if r["dev_bps"] > 0 else "做空ETF+多标的"
        print(f"{mark} {r['etf']:<10} vs {r['base']:<9} 偏离 {r['dev_bps']:>+8.1f}bps | "
              f"ETF {r['etf_ret_bps']:+.1f}bps vs 期望 {r['exp_ret_bps']:+.1f}bps | {side} | vol ${r['vol24h']:,.0f}")
    print(f"\n历史已追加: {HIST_PATH}")


if __name__ == "__main__":
    main()
