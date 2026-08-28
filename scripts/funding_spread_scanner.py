#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨所资金费率差扫描器（funding_spread_scanner.py）— 2026-08-20 D16
=====================================================================
扫 Binance/Bybit/OKX 永续资金费率，找「跨所费率差 + 有现货 + 有深度」的币。

背景（2026-08-20 群研究沉淀）：
- 资金费套利 = 卖保险：收确定的保费（资费），扛不确定的赔付（暴涨）
- TUT 剧本：狗庄制造巨大费率差吸引套利者 → 插针爆仓。判据 = 费率历史剧烈跳变
- BNC 实测否决：无现货/深度 $500 级/费率 -0.42%↔+1.09% 一天乱跳 = 诱饵
- → 本扫描器把「费率稳定性」作为核心过滤条件，不只是看瞬时费率差

用法（hermes venv，需代理）：
  python scripts/funding_spread_scanner.py --top 15
  python scripts/funding_spread_scanner.py --min-spread-bps 30 --min-volume 500000
  python scripts/funding_spread_scanner.py --history 6   # 检查近 N 次结算的稳定性

输出：stdout 表格 + JSONL 追加到 data/funding_spread_scan.jsonl
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

# 双模式判定函数（D19 Codex 版 + D21 收尾：退出线接入数据流）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from funding_dual_mode_decision import decision as dual_mode_decision

PROXY = "http://127.0.0.1:7890"
LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "funding_spread_scan.jsonl"
EXCHANGES = ["binance", "bybit", "okx"]


def make_exchange(name):
    cls = getattr(ccxt, name)
    ex = cls({"enableRateLimit": True, "timeout": 20000})
    ex.proxies = {"http": PROXY, "https": PROXY}
    return ex


def fetch_funding_rates(ex, name):
    """拉永续资金费率，返回 {base: rate}。不同所参数不同。"""
    out = {}
    try:
        if name == "binance":
            marks = ex.fetch_funding_rates()
            for sym, m in marks.items():
                if m.get("fundingRate") is not None and sym.endswith(":USDT"):
                    out[sym.split("/")[0]] = m["fundingRate"]
        elif name == "bybit":
            marks = ex.fetch_funding_rates(params={"category": "linear"})
            for sym, m in marks.items():
                if m.get("fundingRate") is not None:
                    out[sym.split("/")[0]] = m["fundingRate"]
        elif name == "okx":
            marks = ex.fetch_funding_rates(params={"instType": "SWAP"})
            for sym, m in marks.items():
                if m.get("fundingRate") is not None:
                    out[sym.split("/")[0]] = m["fundingRate"]
    except Exception as e:
        print(f"  ⚠️ [{name}] 费率拉取失败: {e}")
    return out


def fetch_spot_bases(ex, name):
    """拉现货交易对，返回 base 集合。⚠️ 必须指定 spot 类型，否则 Bybit fetch_tickers 混入永续。"""
    out = set()
    try:
        if name == "bybit":
            ts = ex.fetch_tickers(params={"category": "spot"})
        elif name == "okx":
            ts = ex.fetch_tickers(params={"instType": "SPOT"})
        else:
            ts = ex.fetch_tickers()
        for s in ts:
            if "/USDT" in s or "/USDC" in s:
                out.add(s.split("/")[0])
    except Exception as e:
        print(f"  ⚠️ [{name}] 现货拉取失败: {e}")
    return out


def fetch_depth_usd(ex, name, base, limit=10):
    """前 N 档深度（USD 近似）。返回 (bid_usd, ask_usd, spread_bps) 或 None。"""
    try:
        if name == "bybit":
            ob = ex.fetch_order_book(f"{base}/USDT:USDT", limit=limit, params={"category": "linear"})
        elif name == "okx":
            ob = ex.fetch_order_book(f"{base}/USDT:USDT", limit=limit, params={"instType": "SWAP"})
        else:
            ob = ex.fetch_order_book(f"{base}/USDT:USDT", limit=limit)
        bids, asks = ob.get("bids", []), ob.get("asks", [])
        if not bids or not asks:
            return None
        bid_usd = sum(p * v for p, v in bids)
        ask_usd = sum(p * v for p, v in asks)
        mid = (bids[0][0] + asks[0][0]) / 2
        spread_bps = (asks[0][0] / bids[0][0] - 1) * 10000
        return bid_usd, ask_usd, spread_bps, mid
    except Exception:
        return None


def fetch_perp_basis(ex, name, base):
    """现货↔永续基差（生死线）：永续价 vs 现货价。返回基差 bps（正=永续升水）。"""
    try:
        perp_sym = f"{base}/USDT:USDT"
        spot_sym = f"{base}/USDT"
        t_p = ex.fetch_ticker(perp_sym)
        t_s = ex.fetch_ticker(spot_sym)
        pp, sp = t_p.get("last") or t_p.get("close"), t_s.get("last") or t_s.get("close")
        if not pp or not sp:
            return None
        return round((pp / sp - 1) * 10000, 1)
    except Exception:
        return None


def fetch_funding_history(ex, name, base, limit=8):
    """近 N 次资金费结算历史，返回 [rate, ...]。用于稳定性判断。"""
    try:
        if name == "bybit":
            hist = ex.fetch_funding_rate_history(f"{base}/USDT:USDT", limit=limit, params={"category": "linear"})
        elif name == "okx":
            hist = ex.fetch_funding_rate_history(f"{base}/USDT:USDT", limit=limit, params={"instType": "SWAP"})
        else:
            hist = ex.fetch_funding_rate_history(f"{base}/USDT:USDT", limit=limit)
        return [h["fundingRate"] for h in hist if h.get("fundingRate") is not None][-limit:]
    except Exception:
        return []


def stability_score(history):
    """费率稳定性：同向率（0-1）+ 波动惩罚。1 = 完美稳定同向，0 = 乱跳。"""
    if len(history) < 3:
        return 0.0
    signs = [1 if r > 0 else (-1 if r < 0 else 0) for r in history]
    nonzero = [s for s in signs if s != 0]
    if not nonzero:
        return 0.0
    same = sum(1 for s in nonzero if s == nonzero[0]) / len(nonzero)
    vals = [abs(r) for r in history]
    vol = (max(vals) - min(vals)) / (max(vals) or 1e-12)
    # 同向率高 + 波动小 = 稳定；波动大直接压分
    return same * max(0.0, 1.0 - vol)


def write_log(rec):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--min-spread-bps", type=float, default=20.0, help="跨所费率差最小 bps")
    ap.add_argument("--min-volume", type=float, default=100_000, help="任一所有永续 24h 成交额下限")
    ap.add_argument("--history", type=int, default=8, help="费率稳定性检查的结算次数")
    ap.add_argument("--no-depth", action="store_true", help="跳过深度检查（快扫）")
    ap.add_argument("--signal-only", action="store_true",
                    help="watchdog 模式：仅当存在「有现货+稳定≥0.6」候选时输出（供 cron 静默/告警）")
    args = ap.parse_args()

    # watchdog 模式下抑制加载过程输出：收集到列表，仅最终信号打印
    _buf = []
    def out(s=""):
        if args.signal_only:
            _buf.append(s)
        else:
            print(s)

    t0 = time.time()
    out("🔍 跨所资金费率差扫描（卖保险视角：费率稳定才值得看）")
    out("=" * 90)

    exchanges = {}
    funding = {}
    spot = {}
    for name in EXCHANGES:
        out(f"  [{name}] 初始化...")
        ex = make_exchange(name)
        exchanges[name] = ex
        funding[name] = fetch_funding_rates(ex, name)
        spot[name] = fetch_spot_bases(ex, name)
        out(f"    ✓ 永续 {len(funding[name])} 个 | 现货 {len(spot[name])} 个")

    # 合并币种
    all_bases = set()
    for s in funding.values():
        all_bases |= set(s.keys())

    out(f"\n共扫到 {len(all_bases)} 个有永续的币，过滤中...")
    rows = []
    checked = 0
    for base in sorted(all_bases):
        rates = {n: funding[n].get(base) for n in EXCHANGES}
        rates = {n: r for n, r in rates.items() if r is not None}
        if len(rates) < 2:
            continue
        spread = max(rates.values()) - min(rates.values())
        if spread * 10000 < args.min_spread_bps:
            continue
        # 现货检查：至少一所有现货（SF 可行性）
        has_spot = any(base in spot[n] for n in EXCHANGES)
        # 稳定性：取费率最高的所的近 N 次结算
        top_ex = max(rates, key=lambda n: rates[n])
        hist = fetch_funding_history(exchanges[top_ex], top_ex, base, args.history)
        stab = stability_score(hist)
        # 基差（生死线）：用第一个有现货的所测现货↔永续基差
        basis = None
        if has_spot:
            for n in EXCHANGES:
                if base in spot[n]:
                    basis = fetch_perp_basis(exchanges[n], n, base)
                    if basis is not None:
                        break
        # 双模式判定：价差输入=真基差（无现货/失败退回费率差近似）；费率差=跨所费率差；波动=费率历史极差近似
        spread_val = round(spread * 10000, 1)
        hist_vol = (max(hist) - min(hist)) * 1e4 if hist else 0
        d = dual_mode_decision(basis if basis is not None else spread_val, spread_val, hist_vol, stab,
                                      top_rate_bps=rates[top_ex] * 10_000)
        rows.append({
            "base": base, "rates": {n: round(r, 6) for n, r in rates.items()},
            "spread_bps": spread_val,
            "basis_bps": basis,
            "has_spot": has_spot, "stability": round(stab, 2),
            "top_ex": top_ex, "history": [round(r, 4) for r in hist[-6:]],
            "mode": d["mode"], "exit_trigger_bps": d["exit_trigger_bps"],
        })
        checked += 1
        if checked % 50 == 0:
            out(f"    ...已检查 {checked} 个")

    out("=" * 100)
    # 排序：可执行模式（套费率/套收敛）优先 > 稳定性 > 费率差
    mode_rank = {"funding": 0, "funding_reverse": 0, "convergence": 0, "no_entry": 1, "danger": 2}
    rows.sort(key=lambda r: (mode_rank.get(r["mode"], 1), -r["stability"], -r["spread_bps"]))
    out(f"{'币':<12}{'费率差bps':>10}{'基差bps':>8}{'现货':>6}{'稳定':>6}  {'模式':<8}{'退出线':>8}  历史(近6次)")
    out("-" * 100)
    shown = 0
    for r in rows[:args.top]:
        rates_s = " ".join(f"{n}:{r['rates'][n]*100:.2f}" for n in EXCHANGES if n in r["rates"])
        hist_s = " ".join(f"{h*100:+.2f}" for h in r["history"]) if r["history"] else "N/A"
        flag = "✅" if (r["has_spot"] and r["stability"] >= 0.6) else ("👀" if r["has_spot"] else "⚠️无现货")
        mode_cn = {"funding": "套费率", "funding_reverse": "反开费率", "convergence": "套收敛", "no_entry": "不进场", "danger": "危险"}.get(r["mode"], r["mode"])
        ext = f"{r['exit_trigger_bps']:.0f}bps" if r.get("exit_trigger_bps") else "-"
        basis_s = f"{r['basis_bps']:.0f}" if r.get("basis_bps") is not None else "n/a"
        out(f"{r['base']:<12}{r['spread_bps']:>10.1f}{basis_s:>8}{'Y' if r['has_spot'] else 'N':>6}"
            f"{r['stability']:>6.2f}  {mode_cn:<8}{ext:>8}  {hist_s}  {flag}")
        shown += 1

    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "bases_checked": len(all_bases),
        # 2026-08-28: 全量 rows 落盘（不再只存 top N）——费率档位跳变检测(funding_rate_jump_watch)需要全量跨快照比对
        "rows": rows,
        "t_scan_s": round(time.time() - t0, 2),
    }
    write_log(rec)

    # watchdog 模式：仅当有「有现货 + 稳定≥0.6」候选时输出（空输出 = cron 静默）
    signals = [r for r in rows if r["has_spot"] and r["stability"] >= 0.6]
    if args.signal_only:
        if not signals:
            return
        # 有信号：先回放完整扫描过程（缓冲内容），再打信号摘要
        for line in _buf:
            print(line)
        print("🚨 跨所资金费率差扫描：发现合格候选（有现货 + 费率稳定）")
        print("=" * 90)
        for r in signals[:args.top]:
            rates_s = " ".join(f"{n}:{r['rates'][n]*100:.2f}" for n in EXCHANGES if n in r["rates"])
            hist_s = " ".join(f"{h*100:+.2f}" for h in r["history"]) if r["history"] else "N/A"
            mode_cn = {"funding": "套费率", "funding_reverse": "反开费率", "convergence": "套收敛", "no_entry": "不进场", "danger": "危险"}.get(r["mode"], r["mode"])
            ext = f"退出线{r['exit_trigger_bps']:.0f}bps" if r.get("exit_trigger_bps") else "无退出线"
            basis_s = f"基差{r['basis_bps']:.0f}bps" if r.get("basis_bps") is not None else "基差n/a"
            print(f"  {r['base']:<10} 费率差 {r['spread_bps']:.1f}bps | {rates_s} | 稳定 {r['stability']:.2f}")
            print(f"      {basis_s} | {mode_cn} | {ext}")
            print(f"      历史: {hist_s}")
        print("提示：进场前查深度/现货流动性，按风控框架（蚂蚁仓/抗2倍涨幅/1倍强平）执行")
        return

    print(f"\n📝 日志: {LOG_FILE}（耗时 {rec['t_scan_s']}s）")
    print("提示：稳定≥0.6 + 有现货 = 值得深挖；费率一天乱跳的=诱饵嫌疑（TUT 剧本），跳过")


if __name__ == "__main__":
    main()
