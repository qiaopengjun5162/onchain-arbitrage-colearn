# 停运项目"捡尸体"：残留清算与死亡协议套利

> 来源：Paxon 群内想法（2026-08-07，Hermes 套利共学 Telegram）
> 归档日期：2026-08-07（Hermes 记录）
> 关联：`research-backlog.md`（清算套利条目）；`defi-arbitrage-capital-guide.md`

## 核心思路（假设）

老项目暂停运营/关闭后残留的资产和机制，存在无人争夺或被低估的机会：
- 残留的抵押仓位没人清算 → 清算人折价接手
- 停运协议的赎回/退出窗口 → 凭证折价买入、按规则换回底层
- 沉淀资金、无人认领的奖励/退款/空投
- 死亡代币在 DEX 的残留流动性
- 破产债权二级市场（Mt.Gox/FTX/3AC 式债权折价交易）

## 机会类型分层

| 类型 | 机制 | 案例/参考 | 个人可行性 |
|---|---|---|---|
| 清算残留 | 借贷协议停运/被黑后，跌破清算线的仓位无人清算；清算人还债换抵押品，吃 5-15% 清算奖励 | Cream、bZx/Fulcrum、Rari、Mango(Solana) | 中：多数被 bot 盯，但停运初期有窗口 |
| 停运赎回 | 协议关闭时设赎回窗口，凭证按规则换底层；窗口期流动性差、知晓率低 → 折价 | 各类 yield protocol shutdown | 中高：信息差型，符合个人 edge 定位 |
| 沉淀资金 | 合约/金库里的遗忘资金（失败退款、无人领奖励） | 链上扫描 | 低：取证难、竞争大 |
| 死亡代币流动性 | 死项目代币残留池子，价格与残值脱节 | 老池子 | 低：多为归零资产 |
| 破产债权 | 二级市场折价买债权，等分配 | Mt.Gox、FTX、3AC | 低：需 KYC、周期长、法律风险 |

## 为什么"没人捡"往往是"捡不起来"

1. 清算函数可能被暂停/权限控制——不是想清就能清；
2. 抵押品可能是死币，清算拿到一堆废纸；
3. 残值评估难：停运公告 ≠ 资产真实价值，管理员可能还能改规则；
4. 法律/合规：破产清算、托管、KYC 会拦住散户；
5. 假尸体：项目可能诈尸重启，或"暂停"只是阶段性的。

## 对个人套利者的判断

- 清算竞拍是标准 MEV 业务，普通人拼不过 bot；但**停运公告刚出、赎回窗口刚开、流动性还没到位**的短窗口是信息差机会——符合个人 edge 定位（市场理解+信息差，不拼速度）。
- 需要的能力：停运公告监控（链上 + 官方渠道）、协议机制阅读理解（赎回规则/清算参数）、残值估算。
- 风险预算：当作"低概率高赔率"方向，单次投入小。

## 下一步

- 建立"停运/关停公告"监控源：RugDoc/DefiLlama 停运追踪、协议官方 X、@therealSyanda 类安全账号。
- 选一个已停运借贷协议（如 Cream 残留头寸）做一次真实清算参数调研，验证"残留清算"是否可执行。
- 把"清算机会"加入 OI 监控同级的信号清单。

## 调研结果（2026-08-07，DefiLlama API 实测）

### 监控源更新（2026-08-07 下午，Paxon 分享 DeFi Sphere）

**DeFi Sphere 清算监控**（https://app.defi-sphere.com/liquidations）——清算套利的实时数据源：
- 公开 API：`sphere.data.blockanalitica.com/liquidations`（SPA 背后，实测可用，走 Clash 代理）
  - `GET /liquidations/?networks=X&from_date=&to_date=&sort=-datetime` 清算列表（含 `liquidation_order_index` 去重键、`liquidation_bonus_usd` 清算奖励、protocol、tx_hash）
  - `GET /liquidations/stats/` 统计（笔数/抵押品/债务 + 24h 变化）
  - `GET /liquidations/options/` 支持网络：arbitrum/avalanche/base/ethereum 等
- 覆盖协议：Aave v3、Morpho、Curve Llamalend 等；页面有 Export CSV
- 已实现监控：`scripts/liquidation_monitor.py`（5 网络，24h 回看，$50K 抵押品/$5K 奖励双阈值告警），cron 每 30 分钟 watchdog
- 实测快照（2026-08-07）：以太坊 24h 3 笔（共 $35K），Base 上 Morpho 清算最活跃（单笔 $2.3K）

### 监控源清单（已确认可用）

| 源 | 用途 | 自动化 |
|---|---|---|
| DefiLlama API `/protocols`（走 Clash 代理） | 按 TVL 筛僵尸/尸体协议；TVL 骤降 = 死亡信号 | ✅ 脚本可拉 |
| DefiLlama 分类：Lending(633) + CDP(229) + Liquidations(2) | 借贷类尸体全集 | ✅ |
| rekt.news（leadersboard） | 被黑项目档案（被黑=常见死因） | 手动 |
| 安全账号 X：@PeckShieldAlert / @CertiKAlert / @BlockSecTeam | 攻击/停运第一时间 | 手动 |
| 协议官方 X + DefiLlama 协议页的 url/公告 | 停运公告窗口 | 手动 |

### Cream 案例（"僵尸"而非"尸体"）

- TVL 历史：峰值 ~17.7 亿美元（2021-06）→ 2026-08-07 约 148.6 万美元（-99.2%）。
- 2021-10 被 flash loan 攻击损失 1.3 亿美元后基本停摆，但合约仍可交互。
- 结论：Cream 是"僵尸协议"——活着但萎缩；残留清算是否存在需查 cToken 合约的 liquidation incentive 与 pause 状态（下一步）。

### DefiLlama 实测：借贷类僵尸/尸体清单

- **僵尸候选**（借贷/CDP，TVL 1万~100万，top）：Venus Isolated Pools(97万)、Moola Market(93万)、**Larix(90万, Solana)**、SakeFinance(78万)、WePiggy(68万)、Bastion(67万, Aurora)、Teller(79万) 等。
- **真·尸体**（TVL=0 的借贷/CDP 共 93 个）：Anchor(Terra)、Ruler、Rabbit Finance、LendHub(Heco)、Karura(kUSD)、Mensa(Fantom)、Ramp、Genshiro 等。
- 注意：DefiLlama category 用 "Lending"/"CDP"（不是 borrow）；部分协议 TVL 字段为 null 需 `or 0` 防御。

### 下一步（具体）

1. 写 `scripts/dead_protocol_screener.py`：定期拉 DefiLlama，输出"TVL 骤降 >50%（周环比）+ 借贷类"告警列表 → 尸体监控自动化。
2. 从僵尸列表选 1-2 个有清算机制的（Larix-Solana / Bastion-Aurora / WePiggy-Ethereum），查清算参数（liquidation incentive、pause 状态）验证可执行性。
3. TVL=0 的 93 个尸体里，筛选仍有 cToken/借贷合约可交互的（多数已完全冻结）。
