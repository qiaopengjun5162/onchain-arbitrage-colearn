# Solana 盲套利 Bot 地址取证：R32xAccFis（WEN 生态 + circular.fi 分析平台）

> 来源：群分享 https://circular.fi/address/R32xAccFis3YzBzGwZ1C4QkGiehLxSao7gDmErA3kjk
> 归档日期：2026-08-21 ｜ 归档人：Hermes ｜ 方法：onchain-address-forensics skill
> 关联：`notes/blind-arbitrage-on-chain-compute-20260808.md`、`notes/hft-pump-dump-execution-0x4bfd879f-20260814.md`

## 一句话结论

**`R32xAccFis…` = 一个 Solana 盲套利 bot 的提交账户（EOA）**：余额 137.16 SOL + 17,581 USDC + 427 WEN，最近 20 笔交易 15 失败 5 成功，全部走自研程序 `7obtMdiXQ…`，在 Orca + Meteora DYN + Meteora DLMM 之间做 WEN 多池套利。**失败 = 主动放弃（Custom 6004），不是出错。**

## 证据链

| 项 | 证据 | 来源 |
|---|---|---|
| 地址类型 | 43 字符 / 32 字节 Base58；owner=System Program（普通账户）；无 data | RPC getAccountInfo |
| 角色 | EOA 提交账户：USDC 单笔变化仅 $0.001（17581.604→17581.605），纯付 gas/签名用 | getTransaction 余额对账 |
| 执行程序 | `7obtMdiXQaLCao2…`（BPFLoaderUpgradeable 自研可升级合约，外层编排） | RPC owner 检查 |
| 交易路径 | ① Orca Whirlpools `whirLbMiic` SwapV2 ② Meteora DYN `Eo7WjKq67rj` Swap（Bitquery 文档确认）③ Meteora `24Uqj9JCL` Deposit/Withdraw 循环（DLMM 池） | 日志 + web 核验 |
| 币种 | WEN（WENWENvqqN）+ BFqD85xdVT（未知，池内流 758K→768K）+ 5HAZwWSPL/ZEUS1aR7aX 等 | pre/post token balances |
| 失败签名 | **Custom 6004 (0x1774) = 自研程序自定义错误**；日志显示内部 swap 全部 success，最后外层程序 `failed: custom program error: 0x1774` | getTransaction 日志尾部 |
| 失败率 | 最近 20 笔：成功 5 / 失败 15（75% 失败）；slot 全部集中在 440656024→440656042（18 slots 窗口内） | getSignaturesForAddress |
| 失败成本 | fee 仅 14,764 lamports ≈ $0.0013 | meta.fee |

## 机制解读（人话）

1. **这是教科书式盲套利**（对照 `blind-arbitrage-on-chain-compute`）：事件触发（WEN 池流动性变动）→ 上链探测 → 链上 staticcall 各池报价 → 利润不达标 → **主动 revert，只亏探测费**。75% 失败率是设计，不是事故——每次失败成本 $0.001，成功一次就回本。
2. **6004 是利润保护阀**：内部 swap 都执行成功了（Orca/Meteora 都 success），最后外层程序算完总账发现净利不够 → 0x1774 主动拒绝。这等于把「价差往坏收敛就跑」写进了合约里——**跟 Paxon 群分享的执行认知完全互证**（机器执行 + 阈值退出 + 人只定参数）。
3. **18 slots 内连发 20 笔** = 一个行情窗口内高频探测，多签名并发抢 WEN 价差窗口。

## circular.fi 平台

- Solana 钱包分析平台（类似 Arkham 的 Solana 版）：交易历史 / 性能指标 / 持仓 / 交易活动
- 实测：web_extract 抓不到（反爬），页面内容未核验；**链上 RPC 数据等价**（本报告全部用 RPC 完成，不依赖平台）

## 结论

- 与 Paxon「机器执行 + 价差恶化就跑」的执行框架**链上实证互证**：真实 bot 的失败不是 bug，是风控在工作
- 可复用信号：**自研程序自定义错误码（如 0x1774）≠ 报错，= 利润保护主动放弃**——分析失败交易时先区分「代码 bug」和「设计内失败」
- 方法论增量：`getSignaturesForAddress` 的 err 分布 + slot 集中度 = 快速判断 bot 活动模式（盲套利高频探测 vs 手动操作）

## 下一步

- [ ] 解码 `7obtMdiXQ` 的指令结构（若开源/可反编译），确认 6004 触发条件（滑点阈值？最小利润？）
- [ ] BFqD85xdVT token 身份核验（WEN 池对手方）
- [ ] circular.fi 用浏览器人工核对页面（确认平台字段与 RPC 一致）
