#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polymarket 排行榜「税前口径」验证 v3 (polymarket_leaderboard_fee_verify.py)
==========================================================================
背景：@runes_leo 称排行榜 pnl 是税前 gross；手续费=股数×0.07×p×(1-p)仅吃单方付；
榜前地址真实到手 24-45%；返佣多=坏信号。
v3 修正：activity API 翻页封顶 ~5500 事件（只覆盖最近 ~11 天），月度窗口拿不全 →
改用 weekly 榜（7 天窗口）与「最近 7 天链上重建」严格对照，全部数据完整可拉。
口径：
  pure_trading = ΣSELL − ΣBUY + ΣREDEEM        （不含返佣，不含手续费 = 对应榜单 gross）
  rebates      = Σ(MAKER+TAKER_REBATE)          （真实现金回流）
  fee_upper    = Σ size×0.07×p×(1−p)            （全按吃单 = 上界）
  榜单 pnl（weekly，官方显示）vs pure_trading → 验证「榜单=gross 交易盈亏」
  真实到手 = pure_trading − fee + rebates
用法：hermes venv python3 scripts/polymarket_leaderboard_fee_verify.py
"""

import datetime as dt
import json
import re
import ssl
import time
import urllib.request

PROXY = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
opener = urllib.request.build_opener(urllib.request.ProxyHandler(PROXY))

def get(url, retries=4, timeout=30):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            with opener.open(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 400:
                return None
            time.sleep(1.5 * (i + 1))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None

def fetch_html(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            with opener.open(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception:
            time.sleep(1.5)
    return ""

def parse_lb_page(url):
    """解析 leaderboard 页面 __next_f 流里的榜单数组"""
    html = fetch_html(url)
    rows = None
    for m in re.finditer(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html):
        c = m.group(1)
        body = c.split(":", 1)[1] if re.match(r'^\d+:', c) else c
        try:
            decoded = json.loads('"' + body + '"')
        except Exception:
            continue
        if "proxyWallet" not in decoded:
            continue
        j = decoded.find('"rank":1,"proxyWallet"')
        if j < 0:
            continue
        k = decoded.rfind("[", 0, j)
        depth = 0; in_str = False; esc = False; kk = k
        while kk < len(decoded):
            ch = decoded[kk]
            if in_str:
                if esc: esc = False
                elif ch == "\\": esc = True
                elif ch == '"': in_str = False
            else:
                if ch == '"': in_str = True
                elif ch == "[": depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0: break
            kk += 1
        try:
            rows = json.loads(decoded[k:kk+1])
        except Exception:
            continue
        if rows:
            break
    return rows

def fetch_activity(addr, since_ts, max_events=6000):
    events, offset = [], 0
    while offset < max_events:
        d = get(f"https://data-api.polymarket.com/activity?user={addr}&limit=500&offset={offset}")
        if not d:
            break
        keep = [t for t in d if t["timestamp"] >= since_ts]
        events.extend(keep)
        if len(keep) < len(d):
            break
        offset += len(d)
        time.sleep(0.25)
    return events

def analyze(events):
    buy = sell = redeem = maker_rb = taker_rb = 0.0
    fee_upper = 0.0; n_trade = 0
    for e in events:
        tp = e["type"]; usdc = e.get("usdcSize") or 0.0
        if tp == "TRADE":
            n_trade += 1
            if e.get("side") == "BUY": buy += usdc
            else: sell += usdc
            p = e.get("price") or (usdc / e["size"] if e.get("size") else 0)
            fee_upper += e["size"] * 0.07 * p * (1 - p)
        elif tp == "REDEEM": redeem += usdc
        elif tp == "MAKER_REBATE": maker_rb += usdc
        elif tp == "TAKER_REBATE": taker_rb += usdc
    pure = sell - buy + redeem
    reb = maker_rb + taker_rb
    return {"n": len(events), "n_trade": n_trade, "buy": buy, "sell": sell,
            "redeem": redeem, "pure_trading": pure, "rebates": reb,
            "take_home": pure - fee_upper + reb, "fee_upper": fee_upper}

def main():
    # 1) 拉 weekly + 24h 榜
    lbw = {r["proxyWallet"]: r for r in (parse_lb_page("https://polymarket.com/leaderboard/overall/weekly/profit") or [])}
    lbd = {r["proxyWallet"]: r for r in (parse_lb_page("https://polymarket.com/leaderboard/overall/daily/profit") or [])}
    print("weekly rows:", len(lbw), "| daily rows:", len(lbd))

    # 2) 三个地址（月榜前 3 正收益）
    lbm = json.load(open("/tmp/polymarket_lb.json"))
    targets = sorted([r for r in lbm if (r["pnl"] or 0) > 0], key=lambda r: r["pnl"], reverse=True)[:3]
    print(f"\n{'地址':<32}{'窗口':>8}{'事件':>6}{'纯交易$':>11}{'返佣$':>9}{'费上界$':>9}{'榜单(weekly)$':>14}{'真实到手$':>11}{'榜单口径':>8}")
    out = []
    now = int(dt.datetime.now().timestamp())
    for r in targets:
        addr = r["addr"]
        for win_name, days in (("7d", 7), ("1d", 1)):
            since = now - days * 86400
            try:
                ev = fetch_activity(addr, since)
                s = analyze(ev)
                lb = (lbw if days == 7 else lbd).get(addr, {})
                lb_pnl = lb.get("pnl")
                # 榜单 gross vs 纯交易；真实到手 = pure − fee + rebate
                gross_match = (s["pure_trading"] / lb_pnl) if lb_pnl else float("nan")
                print(f"{addr[:30]:<32}{win_name:>8}{s['n']:>6}{s['pure_trading']:>11,.0f}"
                      f"{s['rebates']:>9,.0f}{s['fee_upper']:>9,.0f}"
                      f"{lb_pnl:>14,.0f}{s['take_home']:>11,.0f}{gross_match:>8.0%}")
                if days == 7:
                    out.append({"addr": addr, "name": r["name"], "weekly_lb_pnl": lb_pnl, **s})
            except Exception as e:
                print(f"{addr[:30]:<32}{win_name:>8} ERROR {str(e)[:60]}")
    with open("/tmp/polymarket_verify_v3.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
