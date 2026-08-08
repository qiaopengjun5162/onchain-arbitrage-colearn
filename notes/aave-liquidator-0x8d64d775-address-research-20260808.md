# 0x8d64D775 Aave 清算套利地址调研报告（横纵分析法·取证版）

> 来源：《0x8d64D775-Aave清算套利地址调研报告.pdf》（Paxon 分享 2026-08-08）
> 研究时间：2026-08-07（Asia/Shanghai）| 领域：DeFi 清算 / MEV / 闪电贷
> 关联：`notes/ethereum-aave-position-mgmt-case-20260714.md`（同一 tx 拆解）、`notes/research-the-person-week2-20260807.md`（week2 教学版：17 EOA 画像 + 反编译）
> 研究对象：清算搜索者 EOA + 共享执行合约 + 私有区块构建（BuilderNet）

## 一句话结论

> 用闪电贷无本金抢 Aave/Spark 清算折价，用 Bebop RFQ 精确换回还款资产，再把可见 surplus 报给 BuilderNet 换取排序；**真实利润取决于事后 refund，不是链上那笔 0.5366 ETH 表面转账**。

## 四角色系统

1. **提交账户 0x8d64…A1E05**（EOA）：只负责发现机会、签名、付 gas。90 笔交易、余额 ~0.094 ETH、最新 2026-07-14，持续调用同一选择器 `0xd8f7ffd4`
2. **共享执行合约 0xf057…00004**（未验证，Etherscan 标签 MEV Bot）：~1,456 笔，**被多个不同 EOA 调用**（非独占）。字节码硬编码 Aave V3/V2、SparkLend、Balancer Vault、Bebop PMM 地址 + 白名单函数结构
3. **被清算账户 0x986b…e322**：目标交易 collateralAsset=USDC, debtAsset=LINK, debtToCover=4,191.12 LINK, liquidatedCollateral=35,966.26 USDC
4. **链下参与者**：Bebop 专业做市商 0x51C72848（RFQ 报价）+ BuilderNet fee recipient 0xdAdB0d80（收 coinbase payment）

## 目标交易资金流（tx 0xefe4f89f…e52762d, 区块 25,531,149, 2026-07-14）

```
① Aave V3 FlashLoan：借 4,191.1159 LINK（premium 2.0956 LINK = 0.05%）
② liquidationCall：替借款人还 LINK 债务 → 领 35,966.258484 USDC 抵押品
③ Bebop PMM RFQ：Bot→MM 35,966.2549 USDC + 0.0066 WETH；MM→Bot 4,193.2114 LINK + 0.5432 WETH
   （WETH 净额 = 0.5366204327；LINK 精确等于本金+premium，exact-output 级结算）
④ 精确归还闪电贷 4,193.2114 LINK（本金+premium，差额为 0）
⑤ 解包 0.5366 WETH → 全部付给 block.coinbase（BuilderNet fee recipient）
   gas 0.0003201 ETH | 合约留下 0.003596 USDC 尘埃
```

**关键判断**：0.5366 ETH 是「链上毛机会」，全部给了 BuilderNet，**不能写成净利润**。BuilderNet 事后退款机制下，最终净支付 = 链上 bundle payment − refund，但公开 Etherscan 无法证明退款去向和金额。

## 三历史样本（证明非单一资产脚本）

| 样本 | 借贷协议 | 债务资产 | 抵押品 | 闪电贷来源 | 回补 |
|---|---|---|---|---|---|
| 0xefe4…762d | Aave V3 | LINK | USDC | Aave V3 0.05% | Bebop RFQ |
| 0xd963…c38e | Aave V3 | DAI (227,586) | WETH (141.35) | Aave V3 0.05% | Bebop RFQ |
| 0x84cc…a06a | SparkLend | USDT (2,285.98) | cbBTC (0.0413) | **Balancer Vault 0 fee** | Bebop RFQ |

- 主函数接受嵌套参数（资产/数量/协议类型/结算参数），链下搜索器换 calldata 复用同一执行框架
- **按资产动态选闪贷源**：LINK/DAI 用 Aave，USDT 用 Balancer（该事件 0 fee）
- cbBTC 地址与 Coinbase 官方一致

## 链下搜索器工作流（反推，非源码）

1. 持续监控 Aave V2/V3 + SparkLend 仓位，算 Health Factor
2. 每个机会选最便宜闪贷源（比较 premium/库存/回调 gas）
3. 向 Bebop 取可执行 RFQ（多进多出、self-execute、精确指定买入量）
4. 全链模拟（清算可行性/RFQ 有效性/surplus 为正/最高竞价上限）
5. 编码进 `0xd8f7ffd4` calldata，私有提交 BuilderNet，等竞价与退款

## 系统壁垒（5 层）

仓位索引与触发速度 → 多协议兼容（V2/V3/Spark + 多闪贷源）→ RFQ 流动性（无滑点、不暴露路径）→ 区块竞价/退款优化 → 原子安全（任意失败整体回滚，无半成品状态）

## 无法确认的关键问题

- BuilderNet 实际 refund 金额与收款方（可能≠sender）
- 地址累计净利润/真实成功率（90 笔 vs 1,456 笔口径）
- 多 EOA 是否同一实体（昨晚画像：17 EOA 高度疑似同一运营方，nonce 串行证据）
- 链下数据源、Bebop API 权限等级、报价渠道
- 合约完整 ABI/源码/运营方身份

## 学习复现路线（只读版 7 步）

监听仓位 → 算 HF → 历史重放 liquidationCall → 估回补成本 → 加 flash fee/gas/失败概率/竞价成本 → **BuilderNet refund 单独作不确定变量** → paper simulation 数百~数千样本再谈实盘。

净收益模型：
```
Net = CollateralValue − DebtRepayment − FlashFee − SwapCost − Gas − BuilderPayment + BuilderRefund
```
看不到 refund 时同时报告三场景：保守(refund=0) / 中性(历史退款比例) / 乐观(边际贡献上限)。**不要把 liquidation bonus 当可落袋利润**。

## 证据强度分级

- **已确认**：LiquidationCall 事件、闪贷本金+premium、Bebop 事件与转账、LINK 精确归还、净 WETH 差额、全额付给当块 BuilderNet fee recipient、多 EOA 调用、源码未验证
- **高概率推断**：0x8d64=提交热钱包非利润主账户、私有 bundle 提交、依赖 refund 降成本、白名单共享执行引擎
- **未知**：refund 实际金额、累计净利、实体归属、链下数据源、合约 ABI

## 方法论增量（相对昨晚 week2 版）

1. **链上毛机会 ≠ 净利润**：BuilderNet 竞价全额支付场景下，链上 0.5366 ETH 是「报价」不是「利润」——取证报告必须区分
2. **三场景报告法**：不可观测变量（refund）显式建模，保守/中性/乐观并行
3. **同选择器 + 多 EOA + 多资产 = 长期通用基础设施**的交叉验证方法（单笔交易无法证明，分布才行）
4. 与昨晚反编译结论互证：合约无策略代码（配置驱动执行器）、nonce 串行→17 EOA 并行、变现全走 Bebop RFQ、闪电贷把失败成本压到 gas 级
