#!/bin/bash
# Firsto TapeOut 跨市场价差 watchdog：非空输出才推送
cd "$(dirname "$0")/.."
python3 scripts/firsto_cross_market_scan.py 2>/dev/null
