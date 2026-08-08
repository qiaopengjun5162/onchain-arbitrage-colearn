# 链上实验课：可执行的 Uniswap V2 双语课程

日期：2026-08-05

来源：https://onchain-lab-lessons.vercel.app/

自述：A bilingual, executable Uniswap V2 course for onchain engineers（中英双语、可执行）。

## 形态

- 18 课，中英双语
- 每课配套可运行的测试（`corepack pnpm test`，Foundry `forge test -vvvv` 看完整调用 Trace）
- 围绕一笔基准 Swap 展开：第 1 课建立完整路径（授权 -> Router02 -> Pair），后续每课改变这笔交易的一个部分
- vendored uniswap-v2-core / periphery 源码，无需 RPC 本地跑
- 最后一课落到真实链：PancakeSwap V2 与 BSC Swap 证据

## 课程目录

1. 基准 Swap
2. 从 OKX Wallet 到 Pair（钱包签名、calldata、收据的完整阶段）
3. Factory、排序与 CREATE2
4. 流动性与 LP Mint
5. AMM 数学、Fee 与舍入
6. Router02 Swap 入口
7. Pair Swap 内部机制
8. Reserve、Event 与 Trace（用收据还原交易 = 核查 bot 利润计算的方法）
9. 多跳 Path（路由搜索和跨池套利的基础）
10. WBNB 与原生 BNB 路径
11. 移除流动性与 Permit
12. 协议费 Mint
13. Skim、Sync 与异常 Token
14. Router02 的 Fee-on-Transfer 支持
15. TWAP 与累计价格（预言机抗操纵原理）
16. Flash Swap（先拿货、原子操作、再还款 = 原子套利的资金基础）
17. 本地安全与经济风险（交易排序风险，MEV 的前置课）
18. PancakeSwap V2 与 BSC Swap 证据

## 对本项目的价值

### 套利基本功的直接对应

- 第 5 课（AMM 数学、Fee、舍入）= 成本模型里"滑点和价格冲击"的精确算法
- 第 9 课（多跳）= 跨池套利路由的基础
- 第 15 课（TWAP）= 预言机风险判断能力（币股 LP 的预言机风险也靠这个底子）
- 第 16 课（Flash Swap）= 原子套利不需要本金的机制原理
- 第 17 课（排序风险）= backlog #6 MEV 训练材料的平替/前置，而且是可执行版本

### 和 Solana 线的互补

Solana 线研究的是另一条链的执行机制，这套课把 EVM 侧 AMM 的底层吃透。两边对照着学，"账户模型 vs 全局状态"、"Pair 乐观转出 vs Solana 原子指令"这些差异会变成自己的理解，而不是背下来的名词。

### 打卡友好

每课有明确的可验证产出（测试通过、Trace、日志），天然符合残酷共学"证据优先"的打卡要求。一课就是一天打卡。

## 用法建议

- 按顺序过，每天 1-2 课，跑通测试再打卡
- 第 5、9、15、16 课是套利方向的重心，值得二刷
- 跑的时候让 AI 陪读：逐行问 Router/Pair 的调用为什么这么设计，把问答沉淀进笔记
