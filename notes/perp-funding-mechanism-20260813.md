# D9 广度：链上 Perp 资金费率机制（HL / Drift / Zeta）+ 哨兵实测（2026-08-13）

> 个人线 D9 广度任务：了解 Hyperliquid / Drift / Zeta 链上 perp 的资金费率机制
> 数据：`data/funding_signal_log.csv`（210 行，CEX 8h funding 信号）+ `data/funding_basis_history.csv`（590 行，perp-现货基差）

## 一、三家机制对比

| | Hyperliquid | Drift（Solana） | Zeta（Solana） |
|---|---|---|---|
| 撮合 | 链上 CLOB（validator 共识排序） | 订单簿 + vAMM 混合（流动性由 AMM 兜底） | 限价订单簿（Phoenix 式） |
| 定价基准 | Oracle（HL 自营喂价） | Pyth 等 oracle | Pyth oracle |
| 资金费结算 | **每 1 小时**（funding interval 1h） | **每 1 小时**（可配置） | 每 1 小时 |
| 费率驱动 | 标记价 vs oracle 的偏离（市场价差） | 标记价偏离 + **利用率/持仓不平衡** 双因子 | 标记价 vs oracle 偏离 |
| 极端值 | 资金费率上限钳制（如 ±4%/h 级别） | 费率随偏离动态放大（更强回归力） | 同 HL 类 |
| 特有结构 | 单一做市商（HIP-1 首批）提供主要流动性 | **vAMM = 无常损失由协议承担**，订单簿优先 | 依赖外部做市商 |

**核心差异一句话**：
- HL = 「CEX 交易体验搬上链」，资金费机制与币安永续几乎同构（1h 结算、oracle 偏离驱动）
- Drift = 资金费带**利用率因子**（协议内借贷市场联动），费率更「粘」
- Zeta = 最接近传统订单簿，资金费纯粹是价格偏离的回归力

## 二、哨兵实测（2026-08-13 00:00 UTC 快照）

**funding_signal_log 最新行**（CEX 8h 资金费率 + z-score 拥挤度）：
- AVAX +9.4e-5（年化 ~+7%）、DOGE +1.0e-4、SOL **-1.7e-5（年化 ~-1.2%）**、LINK -5.2e-5
- **全部 z-score 在 ±1.4 内** = 无拥挤信号（哨兵阈值 |z|≥2 才告警 → 当前静默正确）
- 分散度 dispersion：LINK 3.73 最高（跨所费率最不一致）、SOL 2.07

**funding_basis_history 最新**（perp-现货基差 bps）：ADA -6.0 / AVAX +7.9 / LINK +5.8 / SUI -1.5 → 基差全部在 ±10bps 内（主流币常态）

## 三、链上 perp funding 套利的结构

1. **链上永续-现货基差 + funding carry**：现货腿（HL/Drift 链上现货或 CEX）+ 永续腿 → 吃 funding + 基差收敛。链上优势 = 24/7 无提币延迟（对比 CEX 需要搬币）
2. **跨所 funding 价差**（我们候选 #链上 perp funding 🟡）：同币 HL vs Drift vs Binance 的 funding 差 → 对冲后吃差。**但**：三家的资金费定义/结算时点/钳制不同，裸比 funding 数字是陷阱（funding-rate-data-caveats 笔记同款）
3. **关键坑**：
   - HL 1h 结算 × 无手续费 maker 返点 → 高频搬 funding 被 HL 的 taker 费（~0.035%？）吃掉
   - Drift vAMM 在极端行情下价差放大（无常损失由协议兜 = 用户吃到的是「更差的中间价」）
   - **funding 高 ≠ 可套**：要看「为什么高」——多头拥挤（可吃）vs 现货溢价（吃不到，交割逻辑不同）

## 四、与 CEX funding 线的衔接

- 我们已有 CEX funding 哨兵（8h 结算、z-score 拥挤度、TUT 陷阱区经验）
- 链上 perp 线下一步：**HL/Drift funding 抓取脚本**（公开 API 无 key：HL info/fundingHistory、Drift API）→ 与 CEX funding 并排监控 → 跨所价差 z-score 阈值告警
- 互证：老白访谈「Perp 是原生发明之一」「币安+火币 60% 收入来自 RWA perp」→ 链上 perp funding 市场会持续变大，值得挂观察窗

## 下一步

- [ ] HL funding 历史抓取脚本（info API）→ data/hl_funding.csv
- [ ] Drift funding 与 CEX 并排哨兵（现有 drift_funding cron 已跑，补对比列）
- [ ] 跨所 funding 价差 z-score 阈值 = 0.5%/24h 才报（防噪音）
