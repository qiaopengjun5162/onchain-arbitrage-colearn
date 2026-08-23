#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘执行纪律检查（execution_guard.py）— 2026-08-23 D19 补缺（D14 缺口②）
========================================================================
给 Jito bundle 管线加「实盘前护栏」：人工确认最小资金 + 失败分类日志（032 模型）。

背景（032 原子性≠执行权 + D14 周总结缺口②）：
- bundle 保证顺序+全有或全无，但不保证纳入（会被竞争 bundle 挤掉/晚到/validator 无 mev-boost）
- landed_net = 毛差 − DEX fee/滑点/冲击 − base fee/gas − tip − 融资成本
- expected_net = P(纳入) × landed_net − 基建成本
- 负样本必须分类：revert / bid too low / conflict / late / proposer coverage
- 实盘铁律：最小资金护栏（亏光也不影响生活）+ 每次执行留失败分类日志

用法：
  python execution_guard.py --check                          # 检查护栏是否通过（执行前必跑）
  python execution_guard.py --simulate --gross-bps 80 --cost-bps 55 --tip-sol 0.005
                                                             # 模拟一笔：landed/expected 双模型
  python execution_guard.py --record-status landed --net-usd 12.5 --class bid-too-low
                                                             # 执行后记录结果（失败分类必填）

配置：环境变量 EXEC_MAX_LOSS_USD（单笔最大可亏，默认 20）/ EXEC_BANKROLL_USD（总资金，默认 100）
      — 都需人工确认后写进 ~/.hermes/.env 或 shell 环境，脚本只读不存密钥
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "data" / "execution_guard_log.jsonl"

# 护栏阈值（可被环境变量覆盖；默认保守值需人工确认）
MAX_LOSS_USD = float(os.environ.get("EXEC_MAX_LOSS_USD", "20"))       # 单笔最大可亏
BANKROLL_USD = float(os.environ.get("EXEC_BANKROLL_USD", "100"))      # 总资金
MIN_NET_USD = float(os.environ.get("EXEC_MIN_NET_USD", "5"))          # 单笔最小净收益（否则不值当）
TIP_REFERENCE_SOL = 0.005                                             # 实测稳落地 tip（D11/D12）

# 032 负样本分类（失败必填一项）
FAIL_CLASSES = {
    "revert": "交易回滚（合约拒绝/状态冲突）",
    "bid-too-low": "tip/bid 太低未被纳入（竞价让渡）",
    "conflict": "与竞争 bundle 状态冲突（被改状态挤掉）",
    "late": "晚到（blockhash 过期/错过窗口）",
    "proposer-coverage": "validator 无 mev-boost/无共同 relay 未纳入",
    "timeout-pending": "超时未确认（未知，需人工查）",
}


def guard_check() -> dict:
    """执行前护栏检查：全部通过才允许实盘。"""
    checks = []
    # 1. 资金护栏
    loss_ok = MAX_LOSS_USD <= BANKROLL_USD * 0.2
    checks.append({
        "item": "资金护栏",
        "pass": loss_ok,
        "detail": f"单笔最大可亏 ${MAX_LOSS_USD:.0f} ≤ 总资金 ${BANKROLL_USD:.0f} 的 20%（${BANKROLL_USD*0.2:.0f}）",
    })
    # 2. 净收益门槛
    checks.append({
        "item": "净收益门槛",
        "pass": MIN_NET_USD >= 5,
        "detail": f"单笔最小净收益 ${MIN_NET_USD:.0f}（< $5 不值得承担执行风险）",
    })
    # 3. 人工确认标记（必须显式设 EXEC_APPROVED=yes）
    approved = os.environ.get("EXEC_APPROVED", "") == "yes"
    checks.append({
        "item": "人工确认",
        "pass": approved,
        "detail": "EXEC_APPROVED=yes 未设置（实盘必须有你点头，AGENTS.md 铁律：发布/交易前必须人复核）",
    })
    passed = all(c["pass"] for c in checks)
    return {"passed": passed, "checks": checks}


def simulate(gross_bps: float, cost_bps: float, tip_sol: float, notional_usd: float = 1000.0,
             p_landed: float = 0.7) -> dict:
    """032 双模型：landed_net vs expected_net。"""
    gross_usd = notional_usd * gross_bps / 1e4
    cost_usd = notional_usd * cost_bps / 1e4
    tip_usd = tip_sol * 200.0  # 简化 SOL 价格 200，可用 env SOL_PRICE 覆盖
    tip_usd = tip_sol * float(os.environ.get("SOL_PRICE", "200"))
    landed_net = gross_usd - cost_usd - tip_usd
    expected_net = p_landed * landed_net
    return {
        "notional_usd": notional_usd, "gross_bps": gross_bps, "cost_bps": cost_bps,
        "tip_sol": tip_sol, "p_landed": p_landed,
        "gross_usd": round(gross_usd, 2), "cost_usd": round(cost_usd, 2),
        "tip_usd": round(tip_usd, 2),
        "landed_net_usd": round(landed_net, 2),
        "expected_net_usd": round(expected_net, 2),
        "verdict": "进" if expected_net >= MIN_NET_USD else "不进（expected 不够门槛）",
    }


def record_status(status: str, net_usd: Optional[float], fail_class: Optional[str] = None, note: str = ""):
    """执行后记录。失败必须带分类（032 负样本分类）。"""
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "net_usd": net_usd,
        "fail_class": fail_class,
        "note": note,
    }
    if status != "landed":
        if fail_class not in FAIL_CLASSES:
            print(f"[!] 失败状态必须填分类，可选: {', '.join(FAIL_CLASSES)}")
            sys.exit(1)
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"✅ 已记录: {status} / net=${net_usd} / class={fail_class or '-'}")


def main():
    ap = argparse.ArgumentParser(description="实盘执行纪律检查（Jito bundle 护栏）")
    ap.add_argument("--check", action="store_true", help="执行前护栏检查")
    ap.add_argument("--simulate", action="store_true", help="模拟一笔（032 双模型）")
    ap.add_argument("--gross-bps", type=float, default=80, help="毛价差 bps")
    ap.add_argument("--cost-bps", type=float, default=55, help="成本 bps（fee+滑点+gas）")
    ap.add_argument("--tip-sol", type=float, default=TIP_REFERENCE_SOL)
    ap.add_argument("--notional-usd", type=float, default=1000)
    ap.add_argument("--p-landed", type=float, default=0.7, help="纳入概率 P(landed)")
    ap.add_argument("--record-status", choices=["landed", "invalid", "pending", "timeout-pending"])
    ap.add_argument("--net-usd", type=float, help="执行后净收益 USD")
    ap.add_argument("--class", dest="fail_class", choices=list(FAIL_CLASSES) + [None])
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    if args.check:
        g = guard_check()
        print("=== 实盘护栏检查 ===")
        for c in g["checks"]:
            print(f"  {'✅' if c['pass'] else '❌'} {c['item']}: {c['detail']}")
        print(f"\n结论: {'✅ 全部通过，可以实盘' if g['passed'] else '❌ 未通过，禁止实盘'}")
        sys.exit(0 if g["passed"] else 2)

    if args.simulate:
        s = simulate(args.gross_bps, args.cost_bps, args.tip_sol, args.notional_usd, args.p_landed)
        print("=== 032 双模型模拟 ===")
        print(f"  名义 ${s['notional_usd']:.0f} | 毛价差 {s['gross_bps']:.0f}bps = ${s['gross_usd']:.2f}")
        print(f"  成本 {s['cost_bps']:.0f}bps = ${s['cost_usd']:.2f} | tip {s['tip_sol']} SOL = ${s['tip_usd']:.2f}")
        print(f"  landed_net  = ${s['landed_net_usd']:.2f}（成功纳入的净收益）")
        print(f"  expected_net = P(landed)={s['p_landed']:.1f} × landed = ${s['expected_net_usd']:.2f}")
        print(f"  判定: {s['verdict']}")
        return

    if args.record_status:
        record_status(args.record_status, args.net_usd, args.fail_class, args.note)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
