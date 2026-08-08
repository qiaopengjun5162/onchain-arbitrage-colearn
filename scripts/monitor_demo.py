"""只读监控 demo：Binance SOL/USDT vs Solana 链上 wSOL/USDC 价差告警。

第一阶段只做发现和告警：不接私钥、不下单、不写任何执行逻辑。

依赖：pip install ccxt requests
可选：设置环境变量 TG_TOKEN / TG_CHAT_ID 后推送到 Telegram，缺省只打印到控制台。
"""

import asyncio
import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import requests

SYMBOL = "SOL/USDT"
WSOL_MINT = "So11111111111111111111111111111111111111112"
POLL_INTERVAL = 10          # 秒；公共 API 有限速，别再短
THRESHOLD = 0.005           # 0.5% 价差才计入
CONFIRM_TIMES = 3           # 连续 N 次超阈值才告警，过滤脏数据和网络抖动
COOLDOWN_SEC = 600          # 同一方向告警冷却，防止告警疲劳
LOG_PATH = Path(__file__).parent.parent / "data" / "monitor_log.csv"

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")


def fetch_cex_price(exchange) -> float:
    return float(exchange.fetch_ticker(SYMBOL)["last"])


def fetch_dex_price() -> float:
    # 取 wSOL 流动性最好的 USDC 池，避免写死单个池子地址后池子失效
    resp = requests.get(
        f"https://api.dexscreener.com/latest/dex/tokens/{WSOL_MINT}", timeout=10
    )
    resp.raise_for_status()
    pairs = [
        p
        for p in resp.json().get("pairs", [])
        if p.get("chainId") == "solana"
        and p.get("quoteToken", {}).get("symbol") == "USDC"
    ]
    best = max(pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0))
    return float(best["priceUsd"])


def notify(msg: str) -> None:
    print(msg)
    if TG_TOKEN and TG_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=10,
        )


def log_row(ts: str, cex: float, dex: float, spread: float) -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    new_file = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["ts_utc", "cex_price", "dex_price", "spread_pct"])
        writer.writerow([ts, cex, dex, f"{spread:.5f}"])


async def main() -> None:
    exchange = ccxt.binance()
    streak = 0
    last_alert_at = 0.0

    while True:
        try:
            cex = await asyncio.to_thread(fetch_cex_price, exchange)
            dex = await asyncio.to_thread(fetch_dex_price)
            spread = (dex - cex) / cex
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            log_row(ts, cex, dex, spread)

            if abs(spread) >= THRESHOLD:
                streak += 1
            else:
                streak = 0

            cooled_down = time.time() - last_alert_at > COOLDOWN_SEC
            if streak >= CONFIRM_TIMES and cooled_down:
                direction = "DEX 高于 CEX" if spread > 0 else "DEX 低于 CEX"
                notify(
                    f"[{ts}] {direction} {spread:+.3%} | CEX {cex:.2f} / DEX {dex:.2f}"
                )
                last_alert_at = time.time()
                streak = 0
        except Exception as e:
            print(f"fetch failed: {e}")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
