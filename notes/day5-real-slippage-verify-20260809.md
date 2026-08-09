# Day 5 主线：真实滑点验证——从假滑点到真实滑点（2026-08-09）

> 脚本：`scripts/solana_dex_slippage_verify.py`（只读）
> 承接：D4 的 `solana_dex_spread_monitor.py`（只报了中间价差）
> 官方主线：「从假滑点到真实滑点——探索 V3 tick 模拟或 Quoter 替代方案」

## 为什么要做

D4 发现 Raydium vs Jupiter 中间价差 17-20bps，但那是**假滑点**（理想化报价）。Day 5 要回答：**真实执行后（两腿 fee + 真实路由滑点）这个价差还剩多少？**

## 方法论：三档口径

1. **假滑点（基准）**：Raydium 直读 vault → 恒定乘积模拟（无路由拆分、单池理想化）
2. **真实滑点（卖腿）**：Jupiter quote 实际成交价（含多池路由拆分 + 各池 fee）
3. **完整环（可执行）**：USDC → Raydium 买 SOL（反向恒定乘积 + 0.3% fee + 滑点）→ Jupiter 卖 SOL

## 实测数据（2026-08-09 02:18 UTC，SOL/USDC）

| 金额 | Jupiter 卖价 | Raydium 买成本 | 池价差(毛) | **环净收益** | 路由 |
|---|---|---|---|---|---|
| 0.1 SOL | 75.8178 | 75.9640 | +10.8bps | **-19.2bps** | Quantum |
| 1 SOL | 75.8173 | 75.9650 | +10.7bps | **-19.4bps** | Quantum |
| 10 SOL | 75.8166 | 75.9749 | +10.6bps | **-20.8bps** | HumidiFi |
| 50 SOL | 75.8151 | 76.0192 | +10.5bps | **-26.8bps** | HumidiFi+Deriverse |
| 100 SOL | 75.8145 | 76.0746 | +10.4bps | **-34.2bps** | HumidiFi+Aquifer |

## 核心结论

1. **主流池跨 DEX 套利无机会（负结果闭环）**：毛价差 10.5bps 完全被两腿成本吞掉
   - Raydium 买腿 0.3% fee = 30bps（单项就超过毛价差）
   - 加上反向滑点（买腿）+ Jupiter 路由费 → 净收益 -19 ~ -34bps
2. **与 CEX 结论同构**：D4 主流币跨所毛价差 <2bps 扣成本后恒负；今天 Solana 主流池也一样——**「摩擦 > 价差」是主流标的的常态**
3. **滑点非线性**：0.1→100 SOL，环净收益从 -19 → -34bps，金额每大 10 倍净亏多 ~5-7bps
4. **D4 的 17-20bps 是中间价差上限**：真实可执行价差（毛）只有 ~10.5bps——聚合器路由拆分让单池模拟高估了可套利空间

## 技术发现

- Jupiter API v1 字段是 `priceImpactPct`（字符串，非单调不可靠）——**别用 priceImpactPct 判断滑点，用 outAmount/inAmount 实际算成交价**
- 大额路由自动拆分多池（HumidiFi+Aquifer+Deriverse...），单池恒定乘积模拟会**高估滑点**——但即便如此完整环依然亏损
- 反向买腿模拟（USDC→SOL）必须单独算：买腿成本 = 投入 USDC / 换回 SOL（含 fee），不能复用卖腿模拟

## 意义

「主流池无机会」不是坏消息——它把搜索空间**逼向长尾**：新上币、流动性薄弱的池子、清算瞬间的不平衡（这些才是摩擦 > 价差的反例）。对应 D4 赛道选择结论（清算/新币/事件驱动）。

## 2026-08-09 追加：Solana 长尾 meme 币验证（BONK/WIF）

- 脚本：`scripts/solana_meme_cycle_verify.py`（Jupiter 真实路由完整环：USDC→meme→USDC）
- 实测（09:16 UTC）：BONK -3.58 / -25.80 / **-149.36** bps（10/100/1000 USDC）；WIF -9.73 / -19.95 / -22.57 bps——**全负**
- **金额越大越亏**：BONK 1000 USDC 时 -149bps（滑点非线性，长尾池深度不足）
- mint 探测教训：POPCAT/PENGU/PNUT 地址已失效（not tradable），仅 BONK/WIF 可交易
- **结论：Solana 长尾 meme 也没有套利空间**——与 CEX 侧长尾测试（摆动假象）呼应，「摩擦>价差」在 Solana 全域成立，机会只在事件驱动（下架/清算/新币）

## 待办

- [x] Rust 双实现：solfi-sim `slippage` 子命令（-1.22~-4.12bps 与 Python 一致）
- [x] 长尾池验证：BONK/WIF 全负（-3.6~-149bps）
- [x] 挂 cron 每小时快照环净收益（watchdog，`滑点验证(slippage_verify)` b9de224f71f5）
