#!/usr/bin/env python3
"""资金费套利双模式判定函数 v1（2026-08-24，本周 P0 落地）。

来源：notes/funding-arb-execution-delta-spread-20260821.md（Paxon 群分享 08-21）
核心认知：
- 同一场景可以双模式（套收敛/套费率）切换，**判断变量=价差状态而非费率高低**
- 套利利润 = 费率收入 − 价差恶化 − 手续费 − 滑点；价差是生死线（快变量吃慢变量）
- 机器执行：价差往坏方向收敛即退出，人只定阈值（退出线 = 已积累费率收入 × 安全系数）

输入（全部 bps 口径，年化统一）：
  价差 spread_bps         当前现货↔永续（或两腿）价差
  价差中位 spread_median  历史价差中位数（正常水平参照）
  费率差 funding_apr_bps  年化费率差（8h/1h 统一换算后）
  价差波动 spread_vol_bps 价差日波动（横盘判据）

输出：{mode, reason[], exit_trigger_bps}
  mode: 套收敛 / 套费率 / 不进场（极端+稳定可双候选时给主推+次选）

用法：
  python3 scripts/funding_mode_decision.py --spread 500 --median 50 \
      --funding-apr 8760 --vol 20 --hold-h 48
  （--demo 跑 5 个内置场景）
"""
import argparse

# ---- 默认阈值（bps，可参数覆盖）----
SPREAD_NORMAL_BPS = 50      # 正常价差 <0.5%
EXTREME_RATIO = 5            # 价差 ≥ 5×正常 = 极端（妖币/单边信号）
FUNDING_MIN_APR_BPS = 1000   # 年化 10% 门槛（覆盖手续费+滑点+资金成本）
VOL_MAX_BPS = 30             # 价差日波动 ≤30bps = 横盘（套费率前提）
EXIT_SAFETY = 1.2            # 价差恶化退出 = 积累费率 × 1.2


def decide_mode(spread_bps, spread_median, funding_apr_bps, spread_vol_bps,
                hold_hours=24, normal=SPREAD_NORMAL_BPS,
                extreme_ratio=EXTREME_RATIO, funding_min=FUNDING_MIN_APR_BPS,
                vol_max=VOL_MAX_BPS, exit_safety=EXIT_SAFETY) -> dict:
    """双模式判定（v1 规则版，可审计——每条输出都带触发规则）。"""
    ref = max(spread_median, 1)
    ratio = spread_bps / ref
    extreme = spread_bps >= extreme_ratio * max(ref, normal)
    funding_ok = funding_apr_bps >= funding_min
    stable = spread_vol_bps <= vol_max
    reasons = [
        f"价差 {spread_bps}bps = 中位 {ref}bps 的 {ratio:.1f}×"
        f"（{'极端≥' + str(extreme_ratio) + '×' if extreme else '未极端'}）",
        f"费率差 年化 {funding_apr_bps/100:.1f}%"
        f"（{'达标≥' + str(funding_min/100) + '%' if funding_ok else '未达标'}）",
        f"价差波动 {spread_vol_bps}bps（{'横盘≤' + str(vol_max) if stable else '高波动'}）",
    ]

    exit_trigger = None
    if extreme:
        if stable:
            mode = "套收敛"
            reasons.append("价差极端 + 波动小 = 回归证据强，赌收敛（风险：黑天鹅/妖币价差继续扩）")
            if funding_ok:
                reasons.append("费率差同时达标 → 双候选：主推套收敛（空间大），次选套费率（价差不恶化前提下）")
        else:
            mode = "不进场"
            reasons.append("价差极端 + 高波动 = 妖币/单边行情信号，价差可能继续扩，等回归证据")
    elif stable and funding_ok:
        mode = "套费率"
        # 机器执行纪律：退出线 = 已积累费率收入 × 安全系数
        funding_bps_per_h = funding_apr_bps / 365 / 24
        exit_trigger = round(hold_hours * funding_bps_per_h * exit_safety, 2)
        reasons.append(
            f"价差稳定横盘 + 费率达标 → 双边持仓吃费率；"
            f"退出线 = {hold_hours}h 积累费率 {hold_hours*funding_bps_per_h:.1f}bps × {exit_safety} = "
            f"价差恶化 ≥{exit_trigger}bps 即平仓（机器执行，人只定阈值）")
    else:
        mode = "不进场"
        reasons.append("中间地带：价差不够极端、或波动大、或费率不足——看不清不进场")

    return {"mode": mode, "reasons": reasons, "exit_trigger_bps": exit_trigger,
            "spread_bps": spread_bps, "funding_apr_bps": funding_apr_bps}


def demo():
    cases = [
        ("文档场景：价差 5% + 费率 1bp/h（87.6%/yr）", dict(spread_bps=500, spread_median=50, funding_apr_bps=8760, spread_vol_bps=20, hold_hours=48)),
        ("横盘健康：价差 0.6% + 费率 15%/yr", dict(spread_bps=60, spread_median=50, funding_apr_bps=1500, spread_vol_bps=15, hold_hours=72)),
        ("妖币高波动：价差 8% + 波动 120bps", dict(spread_bps=800, spread_median=50, funding_apr_bps=3000, spread_vol_bps=120, hold_hours=24)),
        ("费率不足：价差 0.6% + 费率 3%/yr", dict(spread_bps=60, spread_median=50, funding_apr_bps=300, spread_vol_bps=15, hold_hours=24)),
        ("中间模糊：价差 1.5% + 波动 40bps", dict(spread_bps=150, spread_median=50, funding_apr_bps=1200, spread_vol_bps=40, hold_hours=24)),
    ]
    for name, kw in cases:
        r = decide_mode(**kw)
        print(f"\n== {name} ==")
        print(f"  判定：{r['mode']}" + (f" ｜ 退出线 {r['exit_trigger_bps']}bps" if r["exit_trigger_bps"] else ""))
        for why in r["reasons"]:
            print(f"    - {why}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spread", type=float, help="当前价差 bps")
    ap.add_argument("--median", type=float, default=50, help="历史价差中位 bps")
    ap.add_argument("--funding-apr", type=float, help="年化费率差 bps（如 8760 = 87.6%）")
    ap.add_argument("--vol", type=float, default=15, help="价差日波动 bps")
    ap.add_argument("--hold-h", type=float, default=24, help="预计持仓小时数（套费率退出线用）")
    ap.add_argument("--demo", action="store_true", help="跑 5 个内置场景")
    args = ap.parse_args()
    if args.demo or not args.spread:
        demo()
        return 0
    r = decide_mode(args.spread, args.median, args.funding_apr, args.vol, args.hold_h)
    print(f"判定：{r['mode']}" + (f" ｜ 退出线 {r['exit_trigger_bps']}bps" if r["exit_trigger_bps"] else ""))
    for why in r["reasons"]:
        print(f"  - {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
