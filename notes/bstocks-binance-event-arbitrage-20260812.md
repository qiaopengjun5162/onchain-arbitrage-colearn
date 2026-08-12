# bStocks × Binance 事件线 + 套利角度分析（2026-08-12）

> 触发：Paxon 群问「bStocks 明天可能和 Binance 发新产品，有没有套利机会」
> 数据：announcements.db（listing_monitor 已覆盖 Binance bStocks 公告 ✅）+ 公开公告搜索

## 事件线（2026）

| 日期 | 事件 |
|---|---|
| 06-11 | bStocks 正式上线币安（1:1 储备、24/7、BEP-20、ADGM 批准、股息自动复投、零兑换费） |
| 07-22 | 新增 10 种 bStocks 作为抵押资产（全仓杠杆/统一账户） |
| 08-05 | 新增 10 个 bStocks 现货交易对（ALABB/ASMLB/ASTSB…），**零挂单费至 09-01**，提现 08-05 开放 |
| 08-11 | **Binance Futures 发 TradFi perp 合约批次**（RWA perp！Ye Su 论点落地）+ **DOSUSDT 永续上线** |
| 08-12 | 新增 1 个 bStocks 现货交易对 + 1 个抵押资产（listing_monitor 已抓到） |
| 08-13 | 用户情报：可能再发新批次（未见公告，待监控确认） |

7 月 bStocks 占代币化股票 DEX 交易量 85%，市场月量 29 亿 → 88 亿美元。

## 套利角度（按可执行性排序）

1. **上币窗口价差（事件驱动，最有肉但容量小）**：新 ticker 上线 Binance spot 时链上 BSC 池（LiquidMesh/PancakeSwap）价格发现滞后 → 与底层美股（tvscreener 实时）溢价/折价。DOS 案例模板：首小时剧烈波动、安全垫 ≥1-2%、小额全链路试单。**关键：公告 → ticker → 底层价 → 链上深度 → 净价差，半小时内出判定**
2. **期现套利（币股版）——Binance TradFi perp 补齐空腿（结构变化！）**：新 bStocks 若对应对应 TradFi perp：long bStock + short perp 锁基差吃资金费。以前空腿需外部所（Bybit/Kraken xStocks），**现在 Binance 内部闭环**——门槛大幅下降。需确认 TradFi perp 批次是否覆盖 bStocks 标的（08-11 批次细节未拉到）
3. **闭市漂移**：bStock 7×24 vs 美股时段 → 闭市溢价/折价开盘收敛（币股哨兵在跑）；新上市初期做市稀疏、漂移更大
4. **零挂单费窗口**：若新批次延续零 maker 费，做市成本低 → maker 策略窗口
5. **抵押资产新增**：借贷需求 → 币股借贷利率差（冷门小容量）

## 硬约束（笔记已验证，别踩）

- 赎回 KYC 门槛 → 散户只能单腿 = 赌收敛不是真套利
- 非交易时段 Binance Web3 API 拒绝（40367/40369）→ 闭市漂移只能看不能经 API 交易
- quoteId 30s 有效期；BStock 与 Ondo 代币集严格互斥
- 币股流动性薄：单个新 ticker 深度很浅，看到价差 ≠ 吃到（DOS 教训）

## 待办

- [ ] 「bStocks 事件响应检查表」：公告 → ticker → 底层美股价 → BSC 链上池 → 净价差 → 深度 → 判定（半自动脚本）
- [ ] 确认 08-11 TradFi perp 批次的标的清单（bapi 详情接口参数待修）
- [ ] DOS 线更新：DOSUSDT 永续上线 → 期现结构新角度（币安合约 vs 链上/现货）
