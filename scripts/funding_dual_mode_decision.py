#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金费套利双模式判定函数（funding_dual_mode_decision.py）— 2026-08-23 D19
===========================================================================
D19 对比表 P0 落地项：输入（价差、费率差、波动率）→ 输出（套收敛 / 套费率 / 不进场）。

背景（08-21 群内纠正 + D19 对比表）：
- 同一场景可以双模式切换，判断变量 = 价差状态而非费率高低
- 套收敛：价差已极端（≥5% 级）赌回归 → 赚价差收敛的钱
- 套费率：价差稳定、波动小、横盘 → 双边持仓吃费率差（卖保险）
- 价差是生死线：快变量（秒级/分钟级）吃慢变量（8h/1h 结算）→ 价差恶化即退

用法：
  python funding_dual_mode_decision.py --spread-bps 520 --rate-diff-bps 100 --vol-bps 350
  python funding_dual_mode_decision.py --from-json data/funding_spread_scan.jsonl   # 批量判定最近扫描
  python funding_dual_mode_decision.py --quiet                                       # watchdog：仅输出可执行模式

输出：JSON + 人话结论。可作为模块被 scanner / 交易机器人引用（decision() 纯函数）。
"""
import argparse
import json
import sys
from pathlib import Path

# ---------- 判定参数（可调，默认值来自 19 天沉淀） ----------
# 正常跨所价差参考：p50=34bps（D17/D18 回测）；<50bps = 正常区间
SPREAD_NORMAL_BPS = 50      # 价差低于此 = 正常（套费率候选）
SPREAD_EXTREME_BPS = 500    # 价差 ≥5% = 极端（套收敛候选，妖币/单边信号）
# 费率差门槛：双腿成本 50-60bps（D18），费率差年化须覆盖
RATE_DIFF_MIN_BPS = 60      # 每小时费率差下限（bps/8h 档），低于此连成本都盖不住
# 波动率：横盘 vs 单边。用 24h 高低差近似（bps）
VOL_FLAT_BPS = 300          # 24h 波动 <3% = 横盘（套费率安全区）
VOL_STORM_BPS = 1000        # 24h 波动 >10% = 风暴（两种模式都危险）
# 价差恶化退出阈值（机器执行纪律：价差恶化 ≥ 已积累费率 × 系数即跑）
SPREAD_EXIT_MULT = 1.5      # 价差恶化量 ≥ 费率收入 × 1.5 → 退出
# 持仓周期数默认值（套费率退出线用）：1 周期 = 1 次资金费结算（8h）；默认持 3 个结算周期 = 24h
HOLD_PERIODS_DEFAULT = 3

ROOT = Path(__file__).resolve().parent.parent
SCAN_LOG = ROOT / "data" / "funding_spread_scan.jsonl"


def decision(spread_bps, rate_diff_bps, vol_bps, stability=1.0, hold_periods=HOLD_PERIODS_DEFAULT):
    """
    纯函数：三输入 → 模式判定。
    返回 dict：{mode, reason, exit_trigger_bps, confidence}
    mode: 'convergence'(套收敛) / 'funding'(套费率) / 'no_entry'(不进场) / 'danger'(危险勿动)
    exit_trigger_bps: 套费率模式的机器退出线 = 已积累费率收入(每周期 rate_diff_bps × 持仓周期数) × 1.5
    """
    # 0. 数据有效性
    if spread_bps is None or rate_diff_bps is None or vol_bps is None:
        return {"mode": "no_entry", "reason": "输入缺失", "confidence": 0.0, "exit_trigger_bps": None}

    # 1. 风暴检查：波动率 >10% 直接 danger（单边行情里所有价差/资金费中性策略都会死）
    if vol_bps > VOL_STORM_BPS:
        return {
            "mode": "danger",
            "reason": f"24h 波动 {vol_bps}bps > 风暴线 {VOL_STORM_BPS}bps：单边行情，价差不收敛反而扩大，双腿不同步变裸仓",
            "confidence": 0.9,
            "exit_trigger_bps": None,
        }

    # 基差带符号（正=永续升水），极端/正常判断看绝对值，符号只决定方向
    spread_abs = abs(spread_bps)

    # 2. 套收敛：价差极端（≥5%）→ 赌回归（但要价差在收窄方向）
    if spread_abs >= SPREAD_EXTREME_BPS:
        if rate_diff_bps < RATE_DIFF_MIN_BPS:
            return {
                "mode": "convergence",
                "reason": f"价差 {spread_bps}bps 极端（≥{SPREAD_EXTREME_BPS}bps），费率差 {rate_diff_bps}bps 不诱人 → 纯套收敛（赌回归），"
                          f"注意：极端价差 = 妖币/单边信号，退出纪律必须写死",
                "confidence": 0.7,
                "exit_trigger_bps": None,
            }
        return {
            "mode": "convergence",
            "reason": f"价差 {spread_bps}bps 极端且费率差 {rate_diff_bps}bps 可观 → 混合：主套收敛 + 顺带吃费率",
            "confidence": 0.75,
            "exit_trigger_bps": None,
        }

    # 3. 套费率：价差正常 + 波动小（横盘）+ 费率差覆盖成本 + 费率稳定
    if spread_abs <= SPREAD_NORMAL_BPS and vol_bps <= VOL_FLAT_BPS:
        if rate_diff_bps < RATE_DIFF_MIN_BPS:
            return {
                "mode": "no_entry",
                "reason": f"价差 {spread_bps}bps 正常、波动 {vol_bps}bps 横盘，但费率差 {rate_diff_bps}bps "
                          f"< 成本线 {RATE_DIFF_MIN_BPS}bps → 进场给交易所打工",
                "confidence": 0.85,
                "exit_trigger_bps": None,
            }
        if stability < 0.6:
            return {
                "mode": "no_entry",
                "reason": f"费率差 {rate_diff_bps}bps 达标但稳定性 {stability:.2f} < 0.6（费率乱跳=诱饵嫌疑，"
                          f"TUT/BTW 屠宰场剧本）→ 不进场",
                "confidence": 0.8,
                "exit_trigger_bps": None,
            }
        # 机器执行退出线 = 持仓期内已积累费率收入 × 安全系数（价差恶化超过即平仓，人只定阈值）
        income_bps = rate_diff_bps * hold_periods
        exit_trigger_bps = round(income_bps * SPREAD_EXIT_MULT, 1)
        return {
            "mode": "funding",
            "reason": f"横盘（波动 {vol_bps}bps）+ 价差正常（{spread_bps}bps）+ 费率差 {rate_diff_bps}bps "
                      f"覆盖成本 + 稳定性 {stability:.2f} → 卖保险，只收租不赌方向；"
                      f"退出线 = {hold_periods}周期积累费率 {income_bps:.0f}bps × {SPREAD_EXIT_MULT} "
                      f"= 价差恶化 ≥{exit_trigger_bps}bps 即平仓",
            "confidence": 0.9,
            "exit_trigger_bps": exit_trigger_bps,
        }

    # 4. 中间地带：价差在 50-500bps 之间，或波动在 3-10% 之间 → 不进场（观察）
    return {
        "mode": "no_entry",
        "reason": f"价差 {spread_bps}bps / 波动 {vol_bps}bps 处于中间地带（非横盘非极端）→ "
                  f"等横盘（套费率）或等极端（套收敛），现在进场两头不靠",
        "confidence": 0.6,
        "exit_trigger_bps": None,
    }


def exit_rule(rate_income_bps, spread_worsen_bps):
    """
    机器执行退出纪律：价差恶化 ≥ 已积累费率收入 × SPREAD_EXIT_MULT → 平仓。
    返回 (should_exit, reason)
    """
    threshold = rate_income_bps * SPREAD_EXIT_MULT
    if spread_worsen_bps >= threshold:
        return True, f"价差恶化 {spread_worsen_bps}bps ≥ 费率积累 {rate_income_bps}bps × {SPREAD_EXIT_MULT} = {threshold:.0f}bps → 立即平仓"
    return False, f"价差恶化 {spread_worsen_bps}bps < 退出线 {threshold:.0f}bps，继续持有"


def from_scan_log(limit=20, min_spread=20.0):
    """从 funding_spread_scan.jsonl 批量判定最近扫描中的候选行。"""
    if not SCAN_LOG.exists():
        print(f"[!] 找不到 {SCAN_LOG}", file=sys.stderr)
        return []
    rows = []
    for line in SCAN_LOG.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        for r in rec.get("rows", []):
            if r.get("spread_bps", 0) >= min_spread:
                rows.append(r)
    out = []
    for r in rows[-limit:]:
        # spread_bps 是跨所费率差（收入端）；波动率用 history 极差近似；stability 直接用
        hist = r.get("history", [])
        vol = (max(hist) - min(hist)) * 1e4 if hist else 0
        # 价差（生死线）：scanner 新增 basis_bps（现货↔永续基差）优先；旧数据无基差时退回费率差近似（标注近似）
        basis = r.get("basis_bps")
        spread_input = basis if basis is not None else r.get("spread_bps")
        d = decision(spread_input, r["spread_bps"], vol, r.get("stability", 0))
        d["base"] = r["base"]
        d["spread_bps"] = r["spread_bps"]
        d["basis_bps"] = basis if basis is not None else "approx(费率差)"
        d["has_spot"] = r.get("has_spot", False)
        out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser(description="资金费套利双模式判定（套收敛/套费率/不进场）")
    ap.add_argument("--spread-bps", type=float, help="当前价差（bps）")
    ap.add_argument("--rate-diff-bps", type=float, help="跨所费率差（bps/结算周期）")
    ap.add_argument("--vol-bps", type=float, help="24h 波动率（bps，高低差近似）")
    ap.add_argument("--stability", type=float, default=1.0, help="费率稳定性 0-1（默认 1.0）")
    ap.add_argument("--from-json", action="store_true", help="从 funding_spread_scan.jsonl 批量判定")
    ap.add_argument("--limit", type=int, default=20, help="from-json 模式读取最近 N 个候选")
    ap.add_argument("--quiet", action="store_true", help="watchdog：仅输出可执行模式（funding/convergence）")
    ap.add_argument("--exit-check", nargs=2, type=float, metavar=("RATE_INCOME", "SPREAD_WORSEN"),
                    help="退出纪律检查：费率收入(bps) 价差恶化(bps)")
    args = ap.parse_args()

    if args.exit_check:
        should, reason = exit_rule(*args.exit_check)
        print(("🚨 " if should else "✅ ") + reason)
        return 1 if should else 0

    if args.from_json:
        results = from_scan_log(limit=args.limit)
        exec_mode = [r for r in results if r["mode"] in ("funding", "convergence")]
        if args.quiet:
            if exec_mode:
                print(f"🔴 资金费双模式判定: {len(exec_mode)} 个可执行候选")
                for r in exec_mode:
                    spot = "现货✓" if r.get("has_spot") else "无现货✗"
                    ext = f" 退出线{r['exit_trigger_bps']}bps" if r.get("exit_trigger_bps") else ""
                    print(f"  {r['base']:<10} {r['mode']:<12} 价差{r['spread_bps']:.0f}bps {spot}{ext}")
            return
        print(f"=== 资金费双模式判定（最近 {len(results)} 候选）===")
        for r in results:
            ext = f" | 退出线 {r['exit_trigger_bps']}bps" if r.get("exit_trigger_bps") else ""
            print(f"\n{r.get('base','?'):<10} [{r['mode']}]{ext}")
            print(f"  基差 {r.get('basis_bps')}bps | {r['reason']}")
        return

    if not (args.spread_bps is not None and args.rate_diff_bps is not None and args.vol_bps is not None):
        ap.error("需要 --spread-bps --rate-diff-bps --vol-bps（或 --from-json）")

    d = decision(args.spread_bps, args.rate_diff_bps, args.vol_bps, args.stability)
    if args.quiet:
        if d["mode"] in ("funding", "convergence"):
            print(f"🔴 {d['mode']}: {d['reason']}")
        return
    print(json.dumps(d, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
