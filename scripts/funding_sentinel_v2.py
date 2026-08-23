#!/usr/bin/env python3
"""资金费率哨兵 v2：多维交叉验证的 Funding 信号（只读）。

方法论来源：Paxon 私信（2026-08-08）——
1. Z-score 标准化剥离基线差异 → 横截面 Rank（横向比的是"拥挤度"不是"散户化程度"）
2. OI 交叉：funding 高 + OI↑ = 拥挤积累；funding 高 + OI↓ = 拥挤出清
3. 价格维度：横盘/阴跌 + 高 funding = 多单被动扛单
4. 多所 OI 加权合成全局 Funding + 费率离散度 = 情绪分歧信号

用法：
  python funding_sentinel_v2.py --once            # 跑一次
  python funding_sentinel_v2.py --watch 3600      # 每 1h 轮询（funding 8h 结算一次）
  python funding_sentinel_v2.py --quiet           # 无信号静默（cron watchdog 用）

依赖：hermes venv python3.11（ccxt 4.5.71）
"""

import argparse
import csv
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")

# 永续合约：币种 → 各所 symbol（统一用 USDT 本位永续）
SYMBOLS = ["BTC", "ETH", "SOL", "DOGE", "XRP", "BNB", "ADA", "AVAX", "LINK", "SUI"]

# 各所配置：funding ✅ / oi ✅ / 历史 ✅ / spot（basis 用）
EXCHANGES = {
    "okx": {"swap": "{sym}/USDT:USDT", "spot": "{sym}/USDT", "has_oi": True, "has_hist": True},
    "bitget": {"swap": "{sym}/USDT:USDT", "spot": "{sym}/USDT", "has_oi": True, "has_hist": True},
    "kucoin": {"swap": "{sym}/USDT:USDT", "spot": "{sym}/USDT", "has_oi": True, "has_hist": True},
    "gate": {"swap": "{sym}/USDT:USDT", "spot": "{sym}/USDT", "has_oi": False, "has_hist": True},
}

# 信号阈值
ZSCORE_HIGH = 1.5          # |z-score| ≥1.5 视为显著偏离基线
RANK_TOP_N = 3             # 横截面 Rank 前 N 名报信号
OI_CHANGE_BPS = 100        # OI 环比变化 ≥1% 视为方向性（用 8h 窗口对比需要历史；这里用现货 OI 快照做近似）
PRICE_FLAT_PCT = 0.5       # 24h 价格变动 <0.5% 视为横盘
BASIS_PCTILE_HIGH = 0.8    # basis 分位 ≥0.8 = 永续溢价处历史高位（接盘信号）
FUNDING_SPREAD_ALERT = 0.005  # 跨所 funding 最大差 ≥0.5%/期 → 疑似诱盘（TUT 案例：bg/gate 2%/4h vs binance≈0）
LOG_PATH = Path(__file__).parent.parent / "data" / "funding_signal_log.csv"
BASIS_LOG_PATH = Path(__file__).parent.parent / "data" / "funding_basis_history.csv"

def build_exchange(name: str):
    cls = getattr(ccxt, name)
    ex = cls({"enableRateLimit": True, "timeout": 15000, "options": {"defaultType": "swap"}})
    if os.environ.get("NO_PROXY") != "1":
        ex.proxies = {"http": PROXY, "https": PROXY}
    return ex


def fetch_funding_zscore(exchange, swap_sym: str, lookback: int = 30) -> dict:
    """拉历史 funding → 计算当前值相对滚动历史的 Z-score。

    v2.1（2026-08-23 D19 补缺，052/057 教训）：短窗口系统性骗人——
    BILL 4 天窗口 +126% 同号 100%，拉满 88 天仅 +13.57%（高估 9.3 倍）；
    SKR/WLFI/WLD 长窗口符号反转。因此同时算短窗口(8次=~3天)和长窗口(30次=~10天)，
    并加「换手率」：短窗口 sign 相对长窗口 sign 的变化率，>50% = 筛的是噪音。
    """
    try:
        hist = exchange.fetch_funding_rate_history(swap_sym, limit=lookback + 5)
        if len(hist) < 10:
            return {}
        rates = [h["fundingRate"] for h in hist if h.get("fundingRate") is not None]
        if len(rates) < 10:
            return {}
        # 当前值 = 最新结算；历史 = 之前的
        cur = rates[-1]
        past = rates[:-1]
        mean = statistics.mean(past)
        stdev = statistics.stdev(past) if len(past) > 1 else 0
        z = (cur - mean) / stdev if stdev > 0 else 0

        # ---- 双窗口对比（052/057）----
        short_n = min(8, len(past))    # 短窗口：近 8 次结算（~3 天）
        long_n = min(30, len(past))    # 长窗口：近 30 次（~10 天）
        short_rates = past[-short_n:]
        long_rates = past[-long_n:]
        short_mean = statistics.mean(short_rates) if short_rates else 0
        long_mean = statistics.mean(long_rates) if long_rates else 0
        # 短 vs 长 同号率（同号 = 稳定；异号 = 反转风险）
        def sign_of(v):
            return 1 if v > 0 else (-1 if v < 0 else 0)
        s_sign = sign_of(short_mean)
        l_sign = sign_of(long_mean)
        same_sign = (s_sign == l_sign)
        # 换手率：短窗口内 sign 变化次数 / (n-1)（052: 换手 >50% = 噪音）
        if len(short_rates) >= 3:
            sign_changes = sum(1 for i in range(1, len(short_rates))
                               if sign_of(short_rates[i]) != sign_of(short_rates[i-1]))
            turnover = sign_changes / (len(short_rates) - 1)
        else:
            turnover = 0.0
        # 短窗口高估倍数（|短均值| / |长均值|，同号时才计算）
        inflation = abs(short_mean) / abs(long_mean) if long_mean != 0 and same_sign else None

        return {"funding": cur, "mean": mean, "stdev": stdev, "zscore": z, "n": len(rates),
                "short_mean": short_mean, "long_mean": long_mean,
                "same_sign": same_sign, "turnover": turnover, "inflation": inflation}
    except Exception:
        return {}


def fetch_oi(exchange, swap_sym: str):
    """拉 OI（amount 口径，各所单位不同——哨兵只用于同所相对判断）。"""
    try:
        oi = exchange.fetch_open_interest(swap_sym)
        return oi.get("openInterestAmount") or oi.get("openInterestValue")
    except Exception:
        return None


def fetch_price_pct(exchange, swap_sym: str):
    try:
        t = exchange.fetch_ticker(swap_sym)
        return t.get("last"), t.get("percentage")  # last, 24h 涨跌%
    except Exception:
        return None, None


def fetch_basis(exchange, swap_sym: str, spot_sym: str):
    """永续-现货价差（bps）。永续溢价 = 正 basis = 多头拥挤信号。"""
    try:
        swap_t = exchange.fetch_ticker(swap_sym)
        spot_t = exchange.fetch_ticker(spot_sym)
        swap_p = swap_t.get("last")
        spot_p = spot_t.get("last")
        if not swap_p or not spot_p or spot_p <= 0:
            return None
        return (swap_p - spot_p) / spot_p * 10000  # bps
    except Exception:
        return None


def basis_percentile(symbol: str, ex: str, cur_bps: float, window: int = 100):
    """当前 basis 相对历史的分位（0~1）。高 = 永续溢价处历史高位。"""
    if cur_bps is None or not BASIS_LOG_PATH.exists():
        return None
    try:
        past = []
        with open(BASIS_LOG_PATH) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 4 and parts[1] == symbol and parts[2] == ex:
                    try:
                        past.append(float(parts[3]))
                    except ValueError:
                        pass
        past = past[-window:]
        if len(past) < 20:
            return None
        below = sum(1 for p in past if p <= cur_bps)
        return below / len(past)
    except Exception:
        return None


def append_basis_log(symbol: str, ex: str, bps):
    """basis 快照落盘（分位计算的数据源）。"""
    if bps is None:
        return
    new = not BASIS_LOG_PATH.exists()
    with open(BASIS_LOG_PATH, "a") as f:
        if new:
            f.write("ts,symbol,ex,basis_bps\n")
        f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')},{symbol},{ex},{bps:.2f}\n")


def collect_snapshot(symbols: list) -> list:
    """返回 [{symbol, ex, funding, zscore, oi, price, pct}]"""
    rows = []
    for ex_name, cfg in EXCHANGES.items():
        try:
            ex = build_exchange(ex_name)
            ex.load_markets()
        except Exception as e:
            print(f"  [!] {ex_name} 初始化失败: {str(e)[:80]}", file=sys.stderr)
            continue
        for sym in symbols:
            swap = cfg["swap"].format(sym=sym)
            spot = cfg.get("spot", "").format(sym=sym)
            try:
                fz = fetch_funding_zscore(ex, swap)
                if not fz:
                    continue
                oi = fetch_oi(ex, swap) if cfg["has_oi"] else None
                price, pct = fetch_price_pct(ex, swap)
                basis = fetch_basis(ex, swap, spot) if spot else None
                if basis is not None:
                    append_basis_log(sym, ex_name, basis)
                basis_p = basis_percentile(sym, ex_name, basis)
                rows.append({
                    "symbol": sym, "ex": ex_name,
                    "funding": fz["funding"], "zscore": fz["zscore"],
                    "mean": fz["mean"], "oi": oi, "price": price, "pct": pct,
                    "basis": basis, "basis_pctile": basis_p,
                    "short_mean": fz.get("short_mean"), "long_mean": fz.get("long_mean"),
                    "same_sign": fz.get("same_sign"), "turnover": fz.get("turnover"),
                    "inflation": fz.get("inflation"),
                })
            except Exception:
                continue
    return rows


def aggregate(rows: list) -> list:
    """按币种聚合：多所 OI 加权 funding + 费率离散度 + 横截面 rank。"""
    by_sym = {}
    for r in rows:
        by_sym.setdefault(r["symbol"], []).append(r)

    out = []
    for sym, items in by_sym.items():
        # OI 加权 funding（有 OI 的所加权，无 OI 的所等权兜底）
        funded = [i for i in items if i["funding"] is not None]
        oi_items = [i for i in funded if i.get("oi")]
        if oi_items:
            total_oi = sum(abs(i["oi"]) for i in oi_items)
            w_funding = sum(i["funding"] * abs(i["oi"]) / total_oi for i in oi_items)
        elif funded:
            w_funding = statistics.mean(i["funding"] for i in funded)
        else:
            continue
        # 离散度：各所 funding 的标准差（情绪分歧度）
        rates = [i["funding"] for i in funded]
        dispersion = statistics.stdev(rates) if len(rates) > 1 else 0
        # 跨所 funding 最大差（诱盘判别：max - min 的单期差异）
        funding_spread = (max(rates) - min(rates)) if len(rates) > 1 else 0
        funding_max_ex = max(funded, key=lambda i: i["funding"]).get("ex") if funded else None
        # 加权 z-score：平均（全局）+ 最大绝对值（单所显著即报）
        z_items = [i for i in items if i.get("zscore") is not None]
        w_z = statistics.mean(i["zscore"] for i in z_items) if z_items else 0
        max_z = max((abs(i["zscore"]) for i in z_items), default=0)
        # 价格与 OI 均值
        prices = [i["price"] for i in items if i.get("price")]
        pcts = [i["pct"] for i in items if i.get("pct") is not None]
        ois = [i["oi"] for i in items if i.get("oi")]
        # 双窗口指标：取 turnover 最高（最不稳的所）+ inflation 最高（最骗人的所）
        turnovers = [i["turnover"] for i in items if i.get("turnover") is not None]
        inflations = [i["inflation"] for i in items if i.get("inflation") is not None]
        same_signs = [i["same_sign"] for i in items if i.get("same_sign") is not None]
        # basis 聚合：均值 + 最高分位（单所高即高——接盘信号取最拥挤的所）
        basis_items = [i for i in items if i.get("basis") is not None]
        basis_p_items = [i for i in items if i.get("basis_pctile") is not None]
        out.append({
            "symbol": sym,
            "funding": w_funding, "zscore": w_z, "max_z": max_z, "dispersion": dispersion,
            "funding_spread": funding_spread, "funding_max_ex": funding_max_ex,
            "oi_avg": statistics.mean(ois) if ois else None,
            "price": statistics.mean(prices) if prices else None,
            "pct": statistics.mean(pcts) if pcts else None,
            "basis_avg": statistics.mean(i["basis"] for i in basis_items) if basis_items else None,
            "basis_max_pctile": max(i["basis_pctile"] for i in basis_p_items) if basis_p_items else None,
            "turnover_max": max(turnovers) if turnovers else None,
            "inflation_max": max(inflations) if inflations else None,
            "same_sign_all": all(same_signs) if same_signs else None,
            "ex_count": len(items),
        })
    # 横截面 rank：按 z-score 排序（正 = 高于自身基线）
    out.sort(key=lambda x: -x["zscore"])
    for i, row in enumerate(out):
        row["rank"] = i + 1
    return out


def classify(row: dict) -> str:
    """三态分类：拥挤积累 / 拥挤出清 / 被动扛单 / 正常（+ basis 分位交叉）

    v2.1（2026-08-23）：加双窗口过滤——换手率 >50% = 噪音（052 教训），
    高费率但 sign 在短窗口内乱翻的不算「拥挤积累」，降级为「高费率(高换手=噪音)」。
    """
    z = abs(row.get("max_z", row.get("zscore", 0)))
    pct = row["pct"] if row["pct"] is not None else 0
    basis_high = (row.get("basis_max_pctile") or 0) >= BASIS_PCTILE_HIGH
    turnover = row.get("turnover_max")
    noisy = turnover is not None and turnover > 0.5
    # 疑似诱盘：跨所 funding 差 ≥ 阈值（TUT 案例：bg/gate 2%/4h vs binance≈0）
    # 巨大资金费差吸引套利者做空高费所 → 插针收割。最高优先级，优先于一切信号。
    if (row.get("funding_spread") or 0) >= FUNDING_SPREAD_ALERT:
        return "疑似诱盘"   # 跨所资金费差异常 = 价差可能是诱饵（notes/tut-funding-trap）
    if z >= ZSCORE_HIGH:
        if noisy:
            return "高费率(高换手=噪音)"   # 052：sign 乱翻 = 筛的是噪音，非拥挤
        if row.get("oi_avg") and abs(pct) < PRICE_FLAT_PCT:
            return "被动扛单"   # 高费率 + 价格不动 = 多单死扛
        if row.get("oi_avg") is None:
            return "高费率(无OI)"
        return "拥挤积累"       # 高费率 + OI 存在（近似）
    if z <= -ZSCORE_HIGH:
        return "负费率(空头拥挤)"
    if basis_high and (row.get("basis_avg") or 0) > 0:
        return "高basis溢价"    # funding 正常但永续溢价处高位 = 远期看多拥挤
    return "正常"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", type=int, default=0)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    args = ap.parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    def tick():
        rows = collect_snapshot(symbols)
        agg = aggregate(rows)
        signals = [r for r in agg
                   if abs(r.get("max_z", r.get("zscore", 0))) >= ZSCORE_HIGH
                   or classify(r) == "疑似诱盘"]
        # 落盘
        if agg:
            new = not LOG_PATH.exists()
            with open(LOG_PATH, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(agg[0].keys()) + ["class"])
                if new:
                    w.writeheader()
                for r in agg:
                    w.writerow({**r, "class": classify(r)})
        if signals:
            print(f"\n=== {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC 资金费率信号 ===")
            print(f"{'币种':<8}{'OI加权funding':>16}{'Z-avg':>8}{'Z-max':>8}{'Rank':>6}{'24h%':>8}{'basis分位':>9}{'换手':>7}{'高估':>7}  分类")
            for r in agg:  # 显示全部排名，标出显著
                cls = classify(r)
                bp = r.get("basis_max_pctile")
                bp_s = f"{bp:.2f}" if bp is not None else "  -"
                to = r.get("turnover_max")
                to_s = f"{to:.2f}" if to is not None else "  -"
                inf = r.get("inflation_max")
                inf_s = f"{inf:.1f}x" if inf is not None else "  -"
                mark = " ★" if abs(r.get("max_z", r.get("zscore", 0))) >= ZSCORE_HIGH else ""
                if cls == "疑似诱盘":
                    mark = " ⚠️"   # 诱盘优先警示
                print(f"{r['symbol']:<8}{r['funding']*100:>13.4f}%{r['zscore']:>8.2f}"
                      f"{r['max_z']:>8.2f}{r['rank']:>6}"
                      f"{r['pct'] if r['pct'] is not None else 0:>7.2f}%{bp_s:>9}{to_s:>7}{inf_s:>7}  {cls}{mark}")
        elif not args.quiet:
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] 无显著 funding 信号 ({len(symbols)} 币 × {len(EXCHANGES)} 所)")

    tick()
    if args.watch and not args.once:
        while True:
            time.sleep(args.watch)
            tick()


if __name__ == "__main__":
    main()
