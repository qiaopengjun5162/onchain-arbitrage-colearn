# Solana 研究问题

## 市场地图

- Solana Foundation 官方课程里哪些章节最适合补交易、账户、程序和客户端基础？
- Solana Playground 能否作为快速复现实验和教学 demo 的入口？
- Solana Cookbook 里哪些基础示例可以转成套利研究脚手架？
- creatorsand/solana-co-learn 里有哪些适合作为每日打卡练习的任务？
- Anchor 的账户模型、IDL 和测试框架如何帮助复现协议交互？
- Anchor Installation 里的本地环境检查项能否转成一份共学前置 checklist？
- Wallet Adapter Example 能否作为 Solana watcher / demo UI 的钱包连接基础？
- 旧版 Solana CLI 的 `cargo build-bpf` / `cargo build-sbf` 报错应该如何定位到工具链版本和路径问题？
- `rustc --version` 显示够新，但 `anchor build` 仍提示 rustc 过旧时，实际使用的是哪个 Rust 工具链？
- Notion Solana 资料页里有哪些可复用的学习路径、工具链接或项目案例？
- Solana 上主要 DEX 的流动性分布在哪里？
- Jupiter 路由变化是否能提前暴露流动性迁移？
- Titan DART 的公共 endpoint 1 rps 限制适合做哪些低频观察，不适合做哪些实时策略？
- Meteora DLMM / Orca Whirlpool / Raydium CLMM 的价差和深度如何比较？

## 执行质量

- priority fee 提升对交易落地率的影响有多大？
- compute units 设置不合理会造成什么失败？
- 不同 RPC 对延迟和稳定性的影响如何测量？
- Jito bundle 和普通交易路径的差异如何量化？

## Perp

- Drift 的 funding、oracle、liquidation 数据如何采集？
- 极端行情下 funding 和价差会如何变化？
- 清算机会是否已经高度自动化和拥挤？

## MEV

- 哪些 MEV 类型在 Solana 上最卷？
- 哪些 MEV 更依赖低延迟基建？
- 哪些只适合作为安全研究，不适合个人实盘？
- 原子套利作为"基建就是 edge"的极端案例，个人要自建到什么程度的基建才够入场？参照系：circular.fi（待核实，见 `atomic-arb-and-circular.md`）

## 数据层

- 是否需要自己跑节点？
- Helius / Triton / Geyser 分别适合什么场景？
- Helius Dashboard 里哪些指标能帮助评估 RPC、Webhook 和 API 的稳定性？
- 只用公开 API 能做到什么程度？
- WebSocketKing 能否用来快速验证 Solana/交易所 WebSocket 数据格式？
- Solana Explorer 和 Solscan 的信息展示有什么差异？
- Solscan 适合人工核验哪些信息，哪些信息必须靠自建脚本或 RPC 补充？

## Hermes Agent

- Hermes 能否每天扫描 Solana 官方文档、DEX 文档、Jito 更新和黑客松奖项？
- Hermes 能否把新信息转成“可验证假设”？
- Hermes 能否审查 Paper Trading 结果中被高估的部分？
