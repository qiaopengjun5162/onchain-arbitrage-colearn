# X 长文存档 · 2026-08-06 · LI.FI 跨链套利执行与 Agent 集成

> 状态：已发布（X 长文）
> 原文链接：https://x.com/brucexu_eth/status/2085022891339554855
> 发布时间：2026-08-05 22:19 (UTC-7) / 2026-08-06 北京
> 关联笔记：notes/2026-08-06-group-sharing.md（第四节 LI.FI）
> 标签：#链上套利 #LI.FI #Agent

---

# 套利共学｜从发现价差到执行：如何接入 LI.FI 实现跨链套利和 AI Agent 集成

链上发现一个价差，只是套利流程的开始。最后能不能执行，要看资金从哪里来、走哪条路、多久到达、实际收到多少，以及中间会损耗多少。

执行之前也不能只看两个市场的价格。至少要先拿到真实 Quote，检查服务费、Bridge 或 Swap 费用、Gas、滑点、Price Impact、最低到手数量和预计耗时。最好再做一次链上模拟。只有这些数字都放进去之后，才能判断这个机会是不是还有利润。

这是为什么需要 LI.FI 的原因，在跨链交易和资金调度这块，LI.FI 是很重要的基础工具。它把不同 Chain、Bridge、DEX 和 Solver 接到统一的 API 里，让系统可以查询 Route、构造交易，并持续跟踪跨链状态。

## 先看一个真实例子：Ethereum USDC 到 Arbitrum USDC

我先用一个最简单的场景说明。假设我们有 1,000 USDC 在 Ethereum，但发现 Arbitrum 上有一个可能的交易机会。在模拟测算中，如果我们忽略了实际交易执行的磨损，可能就会假设在 Arbitrum 上面也有 1000 USDC 进行套利执行。实际情况呢？

我让 Agent 对 LI.FI 的 /v1/quote 做了一次真实只读请求。输入是 Ethereum 上的 1,000 USDC，目标是 Arbitrum 上的原生 USDC，滑点参数设为 0.5%。请求使用公开占位地址，只获取未签名交易，没有广播任何链上交易。

```
curl --get 'https://li.quest/v1/quote' \
  --data-urlencode 'fromChain=1' \
  --data-urlencode 'toChain=42161' \
  --data-urlencode 'fromToken=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48' \
  --data-urlencode 'toToken=0xaf88d065e77c8cC2239327C5EDb3A432268e5831' \
  --data-urlencode 'fromAmount=1000000000' \
  --data-urlencode 'fromAddress=0x1111111111111111111111111111111111111111' \
  --data-urlencode 'slippage=0.005'
```

USDC 有 6 位 decimals，所以 1000000000 代表 1,000 USDC。当时返回的主要结果是：

- Route 工具：Eco
- 输入：1,000 USDC
- 预计到手：997.5 USDC
- 最低到手：997.5 USDC
- LI.FI Service Fee：2.5 USDC，也就是 0.25%
- Ethereum Gas 估算：约 0.2456 美元
- 预计执行时间：7 秒
- transactionRequest：已返回未签名交易数据

这次 Route 里，LI.FI 的固定服务费已经先从 1,000 USDC 中扣除，剩余 997.5 USDC 再通过 Eco 跨到 Arbitrum。API 返回的 feeCosts 清楚写了 percentage: 0.0025，也就是 0.25%。同时，gasCosts 给出了源链 Gas 的 Token、数量和美元估值。

0.25% 也可以写成 25 bps。Bps 是 basis points，中文一般叫基点：

- 1 bps = 0.01%
- 25 bps = 0.25%
- 1,000 USDC 的 25 bps = 2.5 USDC
- 10,000 USDC 的 25 bps = 25 USDC

如果把这次请求里的 LI.FI Service Fee 和 Gas 放在一起，显性的执行成本约为 2.7455 美元，相当于 27.455 bps。这里还没有计算机会发现后的价格变化、目标市场成交滑点、资金占用和失败成本。

对于普通跨链转账，25 bps 未必是最主要的问题。但套利机会的边际经常只有几十个 bps，这个磨损就很高。假设表面价差只有 20 bps，光 LI.FI Service Fee 就已经超过它；即使价差是 40 bps，扣完 Gas、目标交易滑点和延迟风险后，也未必还剩下利润。

这次报价还有一个值得注意的地方：toAmount 和 toAmountMin 都是 997.5 USDC，说明这条 Eco Route 给出的最低到手与预计到手相同。但这只是这一次、这个金额和这个时点的 Quote，不能外推到其他 Route。换一个金额、时间、Token 或 Bridge，结果都可能变化。

> 备注：默认 LI.FI 新注册用户抽点是 25 bps，但是实际使用时会根据调用量提供优惠的方案，比如大流量客户可以有较低的抽点。
> 对普通用户来说，统一 Route、状态跟踪和失败处理本身有价值。但对套利策略来说，25 bps 会直接抬高 Break-even Spread。策略至少要覆盖 LI.FI Service Fee、两端交易成本、Gas、Slippage、Price Impact、Latency 和失败概率，之后剩下的才是利润。
> 因此，我也有在内部推进专属套利场景的优惠 bps 方案，届时可以公布给大家提供福利。如果你是比较大的套利团队，可以联系我获得优惠报价 https://t.me/brucexu_eth 如果你是学习套利的新团队，欢迎登记信息，等后面我拿到优惠方案后可以为大家添加，登记信息表 https://docs.google.com/forms/d/e/1FAIpQLScjhus2oM718UCkiT7zAi4qcnjPTeuh2e1gNxxJJFGsUZo2jg/viewform 。

## 从这个例子理解 LI.FI 的工作原理

LI.FI 做的第一件事，是把 Chain、Token 和工具标准化。你集成一家，就瞬间拥有了大部分区块链、token price 等数据，也可以任意 swap 和 bridge。同时也会给你做好实际价格的计算、手续费等处理。

接下来，LI.FI 会在它接入的 Bridge、DEX 和 Solver 中寻找可以执行的路径。简单场景可以调用 /quote，拿到一个最佳的单步 Route 和 transactionRequest。如果要比较多个候选，或者处理更复杂的多步流程，可以调用 /advanced/routes，再为每一个 Step 生成交易数据。

Quote 最重要的是下面的一些数据：

- toAmount：预计收到多少
- toAmountMin：考虑滑点后最低保证多少
- feeCosts：LI.FI、Bridge、DEX 或其他工具收取的费用
- gasCosts：预计需要的链上 Gas
- executionDuration：预计完成时间
- tool 和 includedSteps：实际走了哪些工具和步骤
- transactionRequest：等待钱包签名的交易数据

交易广播之后，还要继续调用 /status。跨链流程可能返回 PENDING、DONE 或 FAILED，DONE 下面还可能是 COMPLETED、PARTIAL 或 REFUNDED。

## LI.FI 到底是什么

LI.FI 比较官方的定义是链上流动性的路径和执行层。它聚合 Bridge、DEX、Solver 和 DeFi Protocol，并通过统一的 API、SDK、Widget、CLI 和 MCP Server 提供查询与执行能力。

对套利系统来说，可以把 LI.FI 理解成执行基础设施，它不是策略系统。策略系统负责回答"哪里可能有机会"和"扣完所有成本后是否值得做"；LI.FI 负责回答"资金具体怎么走""这条 Route 现在要付出多少成本""如何构造交易"和"执行到哪一步了"。

LI.FI 目前常见的服务包括：

- Bridge：在不同 Chain 之间移动资产。
- Swap：在同一条链或跨链流程中完成 Token 兑换。
- Intents：用户描述想得到的结果，由 Solver 提供报价并执行。
- Composer：把 Bridge、Swap、Deposit、Stake 等步骤组合成一条 DeFi Flow。
- Earn：查询不同 Protocol 的收益机会，并通过 Composer 执行 Deposit。
- Token Service：查询支持的 Token、地址、decimals、priceUSD 和验证状态。
- Gas API：查询不同 Chain 的 Gas Price 和 Gas Suggestion。
- Status Service：跟踪跨链交易，处理完成、部分完成、退款和失败。
- 基本上主流全套的 DeFi 都有集成

比较好的做法是参考下面的操作，将其集成到你的 Agent 系统里面使用，需要什么调用什么。不需要过度在这里研究和学习每一个产品。

## 如何注册和使用 LI.FI Portal

打开 LI.FI Partner Portal 后，可以使用邮箱注册账号。Portal 主要用于管理 Integrations、API Keys、Analytics、Audit Log、Team 和 Treasury。

注册后的基本流程是：

1. 使用邮箱注册，并完成邮箱验证。
2. 创建或确认一个 Integration，设置自己的 integrator string。
3. 在 Portal 中创建 API Key，并保存在后端环境变量里。不要直接发给 Agent，此外，只会显示一次。
4. 先调用 /v1/keys/test 检查 Key，再测试 /chains、/tokens、/tools 和 /quote。
5. 在 Analytics 和 Audit Log 中观察实际调用与集成活动。

LI.FI 的公开 API 不带 Key 也能调用，但额度较低。API Key 主要用于提高 Rate Limit。不要把 x-lifi-api-key 写进前端 JavaScript、公开仓库、截图或文章。Widget 本身不要求把 API Key 放到前端。

## 把 LI.FI 接入 Hermes / Codex / Claude Code 等等

LI.FI 已经提供了面向 Agent 的文档、MCP Server、CLI 和 Agent Skills。对 Hermes 这类可以调用工具的 Agent 来说，MCP 是最直接的接入方式。

首先，最简单的安装方式就是让你的 AI Agent 来安装，你只需要把下面文档发给它就可以了：

> 参考 https://docs.li.fi/agents/overview 帮我安装相关的 MCP、CLI、Skills 等。然后做几个基础功能测试。

如果你喜欢手动或者想了解更多细节，可以参考下面的简单步骤。LI.FI 的 Hosted MCP 地址是：

> https://mcp.li.quest/mcp

Hermes 原生支持远程 HTTP MCP Server。最小配置可以写进 ~/.hermes/config.yaml：

```
mcp_servers:
  lifi:
    url: "https://mcp.li.quest/mcp"
```

如果需要更高 Rate Limit，可以把 API Key 放进 ~/.hermes/.env，然后在 MCP 配置中引用环境变量，不要把真实 Key 直接写进文章或提交到 Git：

```
mcp_servers:
  lifi:
    url: "https://mcp.li.quest/mcp"
    headers:
      X-LiFi-Api-Key: "${LIFI_API_KEY}"
```

MCP Server 会把 get-chains、get-token、get-quote、get-allowance 和 get-status 等能力暴露成结构化工具。Agent 不需要自己拼接每一个 HTTP 请求。

不过，LI.FI MCP Server 本身是只读的。它会返回 unsigned transactionRequest，但不会替用户签名，也不会广播交易。Hermes 可以自动完成 Token 查询、Quote、Route 比较、成本计算和 Status 跟踪；涉及 Approve、签名、广播和扩大仓位时，应该交给隔离的钱包执行层，并加上明确的金额、滑点、Token/Bridge allowlist 和人工审批规则。这个未来再实践吧，如果你做自动化套利，会需要写脚本。

## LI.FI 常见套利场景举例

### 跨链套利

同一个 Token 在不同 Chain 或不同市场之间出现价格差时，LI.FI 可以计算资产跨链和兑换的实际 Route。这里必须把跨链耗时考虑进去。很多套利窗口只有几秒，普通跨链流程却未必具有原子性。Quote 看起来盈利，不代表资产到达目标链时机会还存在。

更可行的做法往往是在多条链预先准备资金，先在两端完成交易，再用 LI.FI 做库存再平衡。这样可以把"抓机会"和"跨链调仓"拆开。

### Token Price 和 Token Service

套利系统需要先确认 Token 地址、decimals、链和资产版本。USDC、USDC.e 或 Wrapped Token 如果识别错误，后面的价格比较会完全失真。LI.FI 的 /token 和 /tokens 可以返回 Token Metadata、priceUSD 和验证状态。

LI.FI Token Service 使用了 CoinGecko 的数据，覆盖 40+ 链 200+ 万的资产价格。详细说明 https://x.com/lifiprotocol/status/2070122519278018767

比如在我写文章的时候，Ethereum USDC 的 priceUSD 返回约为 0.9999764084，验证状态为 verified。这个数字可以用于 Route 成本估值，但交易机会仍要以实际 Pool 或 Order Book 的可成交价格为准。

### Route 比较和同链 Swap

LI.FI 不只处理 Bridge，也可以比较同链 Swap 和多步 Route。套利系统可以同时请求几个候选路径，比较 toAmountMin、Gas、Fee、Duration 和工具风险。有时输出最多的 Route 并不是最适合的 Route，因为它可能更慢、步骤更多，或者失败后的恢复更麻烦。

### 多链库存再平衡

当套利策略在 Ethereum、Arbitrum、Base 等 Chain 上预置资金后，交易会逐渐把库存推向一边。LI.FI 可以在不要求极低延迟的时段做 Rebalancing，把资金重新分配到需要的 Chain。这个场景通常比"发现价差后临时跨链"更适合普通跨链工具。

### Intents、Composer 和 Earn

Intents 适合让 Solver 围绕一个目标结果竞争执行。Composer 可以在跨链后继续 Deposit、Stake 或调用其他 DeFi Protocol。Earn 则负责发现和进入收益机会。这些能力不等于套利策略，但可以扩展资金管理的后续动作，例如套利结束后把闲置 Stablecoin 调到收益仓位。

## API 调用也有风控边界

LI.FI 默认对请求是没有收费的。但每次 Quote 和 Route 查询都会消耗 LI.FI 的计算资源与 Rate Limit。只把 API 当作免费行情源，持续高频抓取，而没有真实集成或执行需求，容易触发限流和风控。

当前官方限制中，未认证的 /quote 和 /advanced/routes 默认各为每两小时 75 次；Partner Portal 创建的 API Key 默认是 100 requests per minute，Quote 相关接口按两小时滚动窗口计算。超限会返回 HTTP 429 和 RateLimitError。如果持续超限、尝试用多个 Key 或 IP 绕过限制，或者对服务造成性能影响，LI.FI 可能临时封锁 API Key。

套利系统要做好缓存和调用治理：

- /chains、/tokens 和 /tools 这类变化较慢的数据不要每次重查。缓存到你的系统。
- 用户输入和策略扫描要 debounce 或 batch，不要对同一参数反复轮询。
- 读取并记录 ratelimit-limit、ratelimit-remaining 和 ratelimit-reset。
- 收到 429 后按 reset 时间退避，不要换 Key 绕过。
- 真正高频或生产级用途，应通过 Portal 申请适合的额度和商业方案。可以随时联系我。

## 一个可以马上完成的实验

这篇文章最后留一个实操：用 1,000 USDC 或者更有意义的 pair 做一次只读 Route 评估，不执行交易。可以让你的 Agent 来协助你完成。

1. 调用 /chains 和 /tokens，确认 Ethereum、Arbitrum 和两边 USDC 的地址与 decimals。
2. 调用 /quote，获取 Ethereum USDC 到 Arbitrum USDC 的 Route。
3. 记录 toAmount、toAmountMin、feeCosts、gasCosts、executionDuration 和 tool。
4. 再调用一次 /advanced/routes，比较不同候选 Route。
5. 从目标 DEX 或 CEX 获取实际可成交价格和深度。
6. 计算 Break-even Spread：

> 最低所需价差
> = LI.FI Service Fee
> + Bridge / DEX / Solver Fee
> + 源链与目标链 Gas
> + 两端交易滑点和 Price Impact
> + 延迟、失败与资金占用成本

写下结论：这个机会是否可执行？如果不可执行，主要卡在 Fee、Gas、Slippage、Liquidity 还是 Latency？

第一轮只做 Quote、比较和模拟，不签名，不广播。等成本模型跑通后，再决定是否使用可承受归零的小额资金做一次真实验证。

## 扩展资料

- LI.FI 官方介绍：https://docs.li.fi/introduction/introduction
- API、认证与安全：https://docs.li.fi/api-reference/introduction
- Rate Limits：https://docs.li.fi/api-reference/rate-limits
- Fees and Monetization：https://docs.li.fi/faqs/fees-monetization
- Agent Integration：https://docs.li.fi/agents/overview
- LI.FI MCP Server：https://docs.li.fi/mcp-server/overview
- Hermes MCP 文档：https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- Partner Portal：https://portal.li.fi/
