# Polymarket 排行榜「税前口径」实测验证（2026-08-11）

> 触发：X 推文 @runes_leo —— 排行榜收益是税前（gross）；官方手续费=股数×0.07×p×(1-p)，仅吃单方付费；榜前地址真实到手仅 24-45%；榜单排序与真实排序相反；返佣按手续费比例返，返佣多=坏信号。
> 验证：不用信推文，用公开 API 拉真实数据重建。data-api /activity 全类型事件流（TRADE/MAKER_REBATE/TAKER_REBATE/REDEEM）+ 官方手续费公式 + 榜单页 __next_f 流解析。

## 一、结论先行

1. **手续费公式逐档验证正确**：100 股 × 0.07 × p×(1−p) → p=0.50 时 $1.75、p=0.80 时 $1.12、p=0.95 时 $0.33、p=0.99 时 $0.07 —— 与推文数字完全一致。p=0.50 手续费是 p=0.99 的 25 倍（价位决定成本）。
2. **每股手续费实测 0.0122–0.0142**，与推文「每股 $0.011–0.014」吻合。对毛 edge 每股 $0.007–0.016 的吃单型 bot，费用与 edge 同量级 → 直接翻负，推文的机制判断成立。
3. **返佣真实且可量化**（activity 事件流直读）：Djdjdjekekek 最近 11 天 TAKER_REBATE $57,467 + MAKER_REBATE $17,119 = **$74,586**；HomeRunHazard $19,017；swisstony $5,151。返佣是排行榜 gross 之外的真实回流。
4. **榜单确实 gross**：榜单 pnl（月榜 $1,088,012）≈ 纯交易+结算毛盈亏（不含返佣、不扣手续费）——费用是额外成本、返佣是额外收入，两者都不在榜单数字里。
5. **实测抓到一个「榜单 vs 真实方向反转」实例**：HomeRunHazard 月榜 +$453,919，但最近 11 天纯交易 −$121,337（每股 edge −0.0348），扣费后更差——照榜学策略会学到正在亏钱的人（caveat：窗口不齐，月榜覆盖整月）。
6. **修正推文的一个表述**：推文说「榜前地址真实到手只剩 24–45%」。我们测的 3 个地址里，有真实 edge 的（Djdjdjekekek 每股 edge 0.0556 ≈ 4×每股费）到手率 ~82–92%（费上界口径）；24–45% 只适用于「edge≈费用」的吃单 bot 型地址。**机制成立、幅度按地址画像分化**。

## 二、数据与方法

- 榜单：`polymarket.com/leaderboard/overall/monthly/profit` 页面 `self.__next_f.push` 流解析（React Query dehydrated data，queryKey `["/leaderboard","volume","30d",...]` 才是 trader 级 rank/pnl 数组；`profit` 周期页的数组是单笔赢家榜 winRank，勿混）
- 交易重建：`data-api.polymarket.com/activity?user=0x…&limit=500&offset=…`，事件类型 TRADE（side/size/price/usdcSize）+ REDEEM（结算 $1/股）+ MAKER/TAKER_REBATE（返佣）
- 手续费上界 = Σ size×0.07×p×(1−p)（全按吃单算；API 无 taker/maker 标记，真实费用介于 0 与上界之间）
- 纯交易 = ΣSELL − ΣBUY + ΣREDEEM（不含返佣、不含费 = 榜单 gross 口径）
- 窗口：2026-07-31 → 08-11（activity API 翻页封顶 ~5500 事件/地址，月度窗口拿不全；7 天以内数据完整）

## 三、实测表（3 个榜前地址，11 天窗口）

| 地址 | 成交量(股) | 成交额$ | 纯交易$ | 每股毛edge | 每股费(上界) | 返佣$ | 月榜pnl$ |
|---|---|---|---|---|---|---|---|
| Djdjdjekekek（月榜#1 1.09M） | 25.3M | 15.5M | +1,408,703 | +0.0556 | 0.0129 | 74,585 | 1,088,012 |
| swisstony（月榜#2 655K） | 712K | 375K | +72,379 | +0.1017 | 0.0122 | 5,151 | 655,333 |
| HomeRunHazard（月榜#5 454K） | 3.48M | 1.72M | −121,337 | −0.0348 | 0.0142 | 19,017 | 453,919 |

- Djdjdjekekek：25.3M 股/11 天 ≈ 高频 bot；REDEEM 结算 $8.99M 主导盈亏（买赢家拿到结算，典型 hold-to-resolution）；taker 返佣 $57.5K ≈ 费上界 17.6%（返佣比例 25-40% 推测其 taker 费 $150-230K → 真实到手 ~82-92%）
- HomeRunHazard：月榜 +$454K 但近 11 天纯交易为负 —— 「榜单第一未必真第一」的实测反例

## 四、对研究方法论的贡献

1. **gross vs net 是排行榜审计的通用第一刀**：任何带手续费/返佣的场所（Polymarket/CEX 返佣/网格交易所），榜单展示口径必须问「税前还是税后」——与网格回测「0 手续费仍亏、费用与格距同量级」、066 s_min「手续费主导」同构：**成本项与毛利润同量级时，gross 数字是幻觉**。
2. **返佣=坏信号的口诀成立**：taker 返佣按手续费比例返 → 返佣多 = 吃单多 = 费用多；「返佣高」是补贴依赖信号而非盈利能力信号。评估任何交易地址先问：吃单还是挂单？费用多少？返佣多少？
3. **可复用的地址审计管线**：leaderboard 解析（__next_f）→ activity 全事件拉取 → 纯交易/返佣/费三分账 → 对照官方曲线。可接入 onchain-address-forensics 线。

## 五、失败与限制

- activity API 翻页封顶 ~5500 事件/地址（offset 超界返回 400），月度窗口对高频地址拿不全 → 只能用 7-11 天窗口对照，无法严格验证「24-45%」月度精确值
- trades/activity API 无 taker/maker 标记，takerOnly 参数无效 → 费用只能给上界
- 实际费用扣除发生在成交内部，无独立费用流水端点（rebate 有独立事件，费用没有）
- 榜单月/周/日页的 queryKey 结构不同（profit 周期页=单笔赢家榜，trader 级数组在 volume 周期 query 里），解析易混

## 六、下一步

- [ ] 换 API 路径拿月度完整数据（trades API 深度测试 / 多页游标），做 30 天严格对齐
- [ ] taker-tiers batch 端点（页面 queryKey 见 `["taker-tiers","batch",[addresses]]`）→ 直接拿吃单等级验证「吃单型」判定
- [ ] 对「每股 edge≈每股费」的 bot 地址（找 swisstony 型 + 高返佣低 edge 型）验证 24-45% 区间
- [ ] 把本验证接到 onchain-address-forensics：先查 gross/net/rebate 再下结论

## 关联

- 脚本：`scripts/polymarket_leaderboard_fee_verify.py`；数据：`/tmp/polymarket_verify_v3.json`
- 推文：https://x.com/runes_leo/status/2086688671244472701
- 同构结论：`notes/grid-trend-backtest-20260811.md`（费用与 edge 同量级）、`notes/backtest-verify-066-128-20260810.md`（手续费主导）
