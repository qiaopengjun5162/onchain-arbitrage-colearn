# TapeOut 跨市场套利实操（2026-08-27）

> 触发：用户 Paxon 群内实操分享（两天赚 1K+）——不是宣传帖，是本人验证过的真实盈利路径
> 方法：web_search 核验项目 + 机制结构化
> 结论：**机制成立（跨市场订单簿不互通 = 手动撮合），「发现力」是核心 alpha**

## 一、项目背景：TapeOut（BNB Chain）

- TapeOut = 链上硬件构建系统（官方 @Blonskr，曾获 CZ 关注）：用 BNB 买 NAND/LATCH/晶体管等基础组件 → Canvas 上连接成电路 → 流片（Tape Out）→ 工作台启动挖 $BEM
- 组件为 **ERC-1155** 格式，流动性天然低于同质化代币
- 官方市场合约：`0xCC42ba5De0...Eb8087`（NAND 最新价 ~0.0062 BNB，流通 346.8K，市值 ~$1.5M，持仓 965 地址）
- 官方市场早期特性：**只有买单侧、缺卖单挂单**，收 1% 手续费 → 买卖撮合效率低

## 二、Firsto：第三方聚合交易终端

- `tapeout.firsto.ai`（v2.1，@Martin_sen / GM23 团队开发）
- 功能：**支持买单、卖单双边挂单**；官方订单 Firsto 不加收（官方 1% 原样）；Firsto 自有市场挂单 0%、吃单 0.5%（较官方低 50%）
- 官方 @Blonskr 公开认可第三方建设（「这是优秀协议必须经历的，一起建设更开放的 TapeOut」）→ 非恶意分叉，是生态补位

## 三、套利机制（用户实操验证）

**核心信息差：官方市场与 Firsto 订单簿不互通**

- 你在**官方市场挂买单 → Firsto 上会显示**
- 但 **Firsto 上的挂单 → 官方市场不显示**
- 官方市场竞争更小、大家的挂价更低；很多卖家习惯直接在官方市场卖 → 能以**低于市场价很多**收到货
- 收货后挂 Firsto 卖（Firsto 买家多、挂价高）→ 赚跨市场价差

**执行参数（用户实测）**：
- 晶体管（1155）流动性差，等于手动撮合
- 3 BNB 做一次，稳妥约赚 **10%**
- 矿机线（大头）：做「最优首创」矿机（最优首创算力加成高）→ 自己不怎么挖，加价卖到市场
- ⚠️ 用户自警：目前所有东西成本都很高，谨慎进场

## 四、核验结论

1. Firsto 真实存在且功能属实（双边挂单/低手续费/官方认可）✅
2. 官方市场只有买单侧 = 信息差来源属实 ✅
3. 机制本质：**跨市场订单簿不互通的流动性套利**——与 CEX 搬砖同构，但更原始（无自动撮合、靠手动、容量小）
4. 收益数字（3 BNB ~10%）来自用户本人实操，可信度高于群分享帖

## 五、可执行项

- **P0 跨市场价差雷达**（把「发现」机器化）：
  - 先探 Firsto API（SPA 应用，JS bundle 里挖接口，参考 spa-api-scraping 方法）
  - 官方市场订单簿走链上合约读（0xCC42...8087）
  - 算「官方买价 vs Firsto 卖价」跨市场价差，超阈值报警 → 复用 anomalous_order_radar 模式
- **P1 矿机最优属性扫描**（可选）：理解属性体系后扫「最优首创」类组件溢价
- **风险提示**：项目早期（卖单市场开放数日）、地板 0.0018→0.05 BNB 已 100x（behemoth 巨兽扫货）、官方规则朝令夕改前科（对照用户 08-21 天气市场翻车）、成本高

## 六、红旗

- 早期项目 + 高波动（NAND 地板 100x）→ 接盘风险
- 官方规则变更可随时消灭信息差（如官方补双边挂单）→ 信息差套利是**快变量**，雷达要抢在规则变化前

## 七、跨市场价差雷达已落地（2026-08-27 夜）

**API 地图（spa-api-scraping 挖出）**：
- `GET https://api-tapeout.firsto.ai/health` — 官方市场地址 0xA6a8...16E4、810 市场、619 开放买单
- `GET /v1/markets` — 810 市场（cpu 721 合约 + transistors 1155 合约 + assets 带最新价）
- `GET /v1/book/{transistors_addr}/{tokenId}` — **聚合订单簿**（官方+Firsto），每单带 `venue: official|ours` ← 核心
- `GET /v1/market/{addr}/{tokenId}/overview?limit=100` — 行情+成交
- `GET /v1/account/{addr}/...` — 公开账户查询（balances/orders/portfolio）
- `POST /v1/circuit-bids|asks|order-request|quote` — 交易操作（发布挂单）
- `wss stream-api-tapeout.firsto.ai` — 实时流

**关键发现**：
1. **官方市场卖单 = 0**（LATCH asks 全 venue=ours）——「官方只有买单侧」实锤
2. 官方买单深度碾压 Firsto：TapeOut/LATCH 官方 37 档/23.6万个 vs Firsto 最优 0.00790 仅 1 个量（Top3 加权后 Firsto 反而 -28%）
3. 810 市场仅 41 个有成交价；不同市场的 NAND 是不同 1155 合约，**不可跨市场搬**——套利只发生在同市场的官方场 vs Firsto 场
4. 快照时刻（22:15）主市场无肉：TapeOut/NAND 净 -519bps、Blonskr_No1/NAND 平价；唯一正差 Genesis/LATCH +1894bps 但金额灰尘级（0.009 BNB）

**落地**：`scripts/firsto_cross_market_scan.py`（5 官方市场 × NAND/LATCH，分 venue 算价差，净价差≥1.5% 且金额≥0.1 BNB 报警）+ cron `2c8dc44b4cac` 每 15 分钟 watchdog

**含义**：价差是动态的，用户「3 BNB 一次 10%」发生在特定时刻（Firsto 高价买单深的时候）——雷达的价值 = 持续监控，价差扩大瞬间报警，机器盯盘替代手动刷两个页面

## 八、矿机线（721 电路 NFT）API 探明（2026-08-27 深夜）

**结论：电路市场无 REST 查询端点，数据源 = SSE 实时流**

- `stream-api-tapeout.firsto.ai/v1/stream/circuits`（EventSource）——心跳帧含关键合约：
  - `circuit_collections: 0x68224f668083c29e9800be2a646d42d18cedf7e2`（= factoryAddress）
  - `official_circuit_market: 0x6feebbebc07bcb90bd1ac8b0cf9baa4f0ff2b46f`
  - `circuit_exchange: 0xb17d0f8487123774f430d3b5708c7bb4143b68d8`
- 电路订单 = 签名卖单（signed asks）+ 出价池（bid pools），POST /v1/circuit-bids|asks 发布
- /v1/book 与 /v1/market 对电路合约地址全部 400 → 不能像元件线那样直接拉订单簿

**元件 vs 电路 API 对比**：
| | 元件（1155 NAND/LATCH） | 电路（721 NFT） |
|---|---|---|
| 行情查询 | REST /v1/book + /v1/market ✓ | 无 REST，SSE 流 |
| 订单类型 | venue=official/ours 聚合 | signed asks + bid pools |
| 自动化 | ✅ 雷达已上线 | 需 SSE 长连收集器 |

**下一步（未完成）**：电路 SSE 收集器——后台长连挂 /v1/stream/circuits，收电路集合/出价池/签名卖单存 JSONL，建矿机行情库 → 才能算「矿机价 vs 元件成本（NAND+LATCH+流片费）」的组装套利空间（用户大头线）
