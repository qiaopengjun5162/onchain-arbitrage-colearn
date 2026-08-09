#!/bin/bash
# 基础设施自检哨兵 cron wrapper（watchdog 模式：全绿静默，有黄/红才输出）
# 用法：cron no_agent 模式，脚本 stdout 非空即推送
cd "$(dirname "$0")/.."
source ~/.zshrc 2>/dev/null
/Users/qiaopengjun/.hermes/hermes-agent/venv/bin/python3.11 scripts/infra_selfcheck.py --watchdog 2>/dev/null
exit $?
