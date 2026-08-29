#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日笔记打卡检查器（daily_note_check.py）— 2026-08-29 共学结营后长期机制

背景：共学 08-25 结营，但学习是长期过程。用户明确要求：结营后仍须
  ① 每天记录笔记（daily/<日期>.md）
  ② 每天有 git 提交（产出入库）
  ③ 公众号输出线不断

本脚本每晚 21:30 由 cron 调用，检查当天记录是否完成：
  - daily/<today>.md 存在且 ≥10 行（有实质内容）
  - 今天有 git commit
都满足 → 空输出（watchdog 静默契约，不打扰）
任一缺失 → 推送提醒（stdout 非空 → cron 投递）

用法：
  python3 scripts/daily_note_check.py            # 检查今天
  python3 scripts/daily_note_check.py --date 2026-08-30   # 指定日期（补查）
  python3 scripts/daily_note_check.py --force    # 强制输出检查结果（测试用）
"""
import argparse
import datetime
import os
import subprocess
import sys

KB = "/Users/qiaopengjun/Code/Solana/onchain-arbitrage-colearn"
MIN_LINES = 10  # daily 最少行数（有实质内容而非空壳）


def check(date_str):
    daily = os.path.join(KB, "daily", f"{date_str}.md")
    # 1. daily 检查
    daily_ok = False
    if os.path.exists(daily):
        try:
            lines = open(daily, encoding="utf-8").read().splitlines()
            daily_ok = len([l for l in lines if l.strip()]) >= MIN_LINES
        except Exception:
            daily_ok = False
    # 2. git commit 检查（当天 00:00-23:59 本地时间）
    r = subprocess.run(
        ["bash", "-c",
         f"cd {KB} && git log --oneline --since='{date_str} 00:00' --until='{date_str} 23:59' | wc -l"],
        capture_output=True, text=True, timeout=30)
    commits = int((r.stdout or "0").strip() or 0)
    return daily_ok, commits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="检查日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--force", action="store_true", help="无论是否完成都输出（测试用）")
    args = ap.parse_args()

    date_str = args.date or datetime.date.today().isoformat()
    daily_ok, commits = check(date_str)

    if daily_ok and commits >= 1:
        if not args.force:
            return 0  # 已记录 = 静默（watchdog 契约）
        print(f"✅ 每日笔记打卡（{date_str}）：daily 已写（{MIN_LINES}+ 行）+ 今天 {commits} 个 commit，记录完整")
        return 0

    missing = []
    if not daily_ok:
        missing.append(f"daily/{date_str}.md 未写或内容过短（<{MIN_LINES} 行）")
    if commits < 1:
        missing.append("今天无 git 提交")
    lines = [f"📝 每日笔记打卡（{date_str}）：{'、'.join(missing)}"]
    if not daily_ok:
        lines.append("共学虽结营，学习不断——请写一篇 daily 笔记：今天做了什么 / 学到什么 / 下一步")
    if commits < 1:
        lines.append("产出记得 git commit + push 入库")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
