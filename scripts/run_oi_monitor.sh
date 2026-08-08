#!/bin/bash
# OI 监控 cron wrapper：正常时静默，有异动告警才输出（cron watchdog 模式）
# 由 Hermes cronjob 每 30 分钟调用；代理地址可用 PROXY 环境变量覆盖。
cd "$(dirname "$0")/.." || exit 1
export PROXY="${PROXY:-http://127.0.0.1:7890}"
export PYTHONWARNINGS="ignore::UserWarning"
exec .venv/bin/python scripts/oi_monitor.py --quiet
