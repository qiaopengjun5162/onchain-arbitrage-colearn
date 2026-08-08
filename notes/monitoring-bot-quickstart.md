# 监控 Bot 入门：新手选型建议

## 问题

突发溢价靠人工根本来不及，必须有监控 Bot。新手写监控脚本，用哪套框架或 API 比较友好？

## 最小闭环

监控脚本不需要框架。一个能跑的监控只有四步：

```text
定时拉数据 -> 计算价差/异常 -> 超过阈值 -> 推送告警 -> 记录日志
```

先跑通这个，再考虑复杂架构。

## 推荐组合：Python 路线

### 数据源

- CEX 行情、资金费率：`ccxt`（统一封装 100+ 交易所，文档全，最省事）
- DEX 价格：DexScreener API（免费、无需 key、适合盯新池子和价差）
- Solana DEX 数据：Birdeye API
- Solana 路由报价：Jupiter Quote API、Titan DART 公共 endpoint（1 rps，无需 key）
- 跨链报价：LI.FI API
- Solana 链上事件：Helius WebSocket / Webhook（地址监控、交易解析）
- EVM 历史数据：The Graph subgraph

### 告警通道

- Telegram Bot：`python-telegram-bot` 或直接 HTTP 调 `sendMessage`，10 行代码搞定
- 飞书 / Discord webhook：一条 POST 请求

### 定时

- 第一版：`while True` + `asyncio.sleep`，别急着上调度框架
- 第二版：cron 或 APScheduler
- 不建议一上来用 Airflow / Celery，杀鸡用牛刀

## Node.js 路线

如果后续主要做 Solana 生态，可以用 `@solana/web3.js` + Helius。

但起步速度上 Python + ccxt 更快，监控逻辑两边互通。

## 最小示例结构

可运行版本见 `scripts/monitor_demo.py`（Binance SOL/USDT vs Solana 链上 wSOL/USDC，带连续 N 次确认和告警冷却）。

## 补充：用合约方法调用记录发现新池子（2026-08-05 群分享）

> 需要根据不同的合约来分开来看，合约就是一个一个的方法。以 Uniswap 为例，在一个池子合约里有添加池子的方法，找到这个方法，查一下调用记录就行。

思路拆解：链上数据发掘的最小单位不是「协议」而是「合约方法」。想找新池子，不用爬前端或等数据商收录——直接盯工厂合约的创建方法：

- EVM：Uniswap V3 Factory 的 `createPool`，PancakeSwap 类似。用 explorer 的 method filter 或 The Graph 查这个方法的调用记录，每次调用 = 一个新池子诞生，参数里直接带 token0/token1/fee
- Solana：对应的是 Raydium/Orca 的初始化池子指令，用 Helius 的 Enhanced Transaction API 按 program + instruction type 过滤

为什么这是 edge 来源：聚合器和数据商的收录有延迟（几分钟到几小时），而套利笔记里说过"edge 在聚合器看不见或看得慢的地方——未被索引的新池子"。盯方法调用记录 = 把发现新池子的时延压缩到一个区块确认。这也是「数据发掘是能力缺口」那条 backlog 的第一个可操作答案。

```python
import asyncio
import ccxt
import requests

THRESHOLD = 0.005  # 0.5% 价差才告警
TG_TOKEN = "..."
TG_CHAT_ID = "..."

async def main():
    binance = ccxt.binance()
    while True:
        try:
            ticker = binance.fetch_ticker("SOL/USDT")
            # 这里接第二个数据源，算价差
            # 超阈值就发 Telegram
        except Exception as e:
            print(f"fetch failed: {e}")
        await asyncio.sleep(10)

asyncio.run(main())
```

## 新手常见坑

- 假信号：API 返回脏数据、网络抖动，触发误报。加"连续 N 次超阈值才告警"。
- 告警疲劳：阈值太低，一天几百条，最后没人看。分级阈值 + 冷却时间（同一信号 N 分钟内只报一次）。
- Rate limit：公共 API 有限速，轮询间隔别太短；Titan 公共 endpoint 只有 1 rps。
- 只看价格不看深度：屏幕上 1% 价差，盘口深度只够成交 50 U。第二版要加深度检查。
- 提前接下单：监控没稳定之前，不要接任何下单逻辑。先只读跑 1-2 周。

## 升级路径

1. 只读监控：价格 / 资金费 / 价差告警
2. 加深数据：盘口深度、成交量、OI、predicted funding
3. 加路由报价：Jupiter / Titan / LI.FI quote 对比
4. 加 Paper Trading：信号出现时记录"如果当时下单"的虚拟盈亏
5. 最后才讨论执行，而且执行前必须有成本模型和 kill criteria

## 和共学的关系

监控脚本是"在场"的前提，也是每日打卡最容易拿出证据的产出：

- 今天接通了哪个数据源
- 今天告警了多少次，误报率多少
- 今天发现了哪个真实价差（哪怕没吃到）

这些都比"我看了某篇文章"更像有效打卡。
