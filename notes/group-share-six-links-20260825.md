# 群分享六连发核验（2026-08-25 D21）

> 触发：用户连发 6 条 X 链接（Bruce×2 / Solana 官方 / Crypto老鹰 / Chosmos110 / WY_mask）
> 处理：全部 fxtwitter 抓取全文 → 逐条核验 → 分层利用（可集成/可提取/备查）

## 逐条核验

### ① Bruce v4 Hook 恶意池技术分析（brucexu_eth 2091888306049220613）⭐ 最有价值
- 内容：4008 字长文，从聚合器从业者视角拆解 BNB Chain WBNB/USDC v4 Hook 池攻击——**模拟报价 0% 手续费、真实成交 12.8% LP fee**
- **三个机制（新知识）**：
  1. **gas 环境区分模拟/执行**：恶意 Hook 读执行时 gas——高 gas 的 eth_call 模拟落入低费率分支（报价便宜），真实交易 gas 低落入高费率分支（收 12.8%）；同 calldata 只改 call gas 可复现不同返回值（gas=1M→10%、16M→0.5%、30M→0%）
  2. Uniswap v4 Hook 动态费能力本身正常，恶意在把「模拟 vs 真实」也写进费率逻辑；0x800000 只是 dynamic-fee flag 不是 800% 费率，真实费率看 Swap event fee 字段（本案 fee=128000=12.8%）
  3. **amountOutMin 盲区**：只查整条路线总输出，不逐池查 fee；其他步骤 positive price improvement 可掩盖被抽走的价值
- **与库内互证**：08-24 已归档同一事件（青蛙那帖，Swap 事件 fee=128000）→ 本条是机制级深挖，补上「gas 环境」攻击向量
- **可执行项**：我们的报价核验方法论（LI.FI quote 污染/51bps 滑点指纹）可加**第 4 指纹 = 模拟 gas ceiling vs 实际 gas 的费率分支差异**（对 v4 Hook 池报价做 gas 敏感性测试）

### ② Polymarket 天气套利（Crypto老鹰 laoyingkhq 2092145302568571195）⚠️ 返佣帖但机制属实
- 内容：「每周靠天气套利稳定 2200 刀」+ HondaCivic 账户 + **via=YINGGE888 返佣链接 + PolyCop 跟单 bot ref=YINGGE888**
- **返佣识别**：via= 返佣 + 跟单 bot + 高收益话术（月赚一万刀）= 标准返佣引流（与 Crypto老鹰 08-21 案例同款,skill 有档）→ **数字不采信**
- **机制核验（属实！）**：web_search 证实 Polymarket 天气市场**明确锚定 NOAA 机场气象站**——西雅图市场规则「NOAA at the Seattle-Tacoma International Airport Station」、芝加哥=机场站；老鹰帖说 NYC=拉瓜迪亚、达拉斯=洛夫菲尔德 ✅
- **信息差本质**：市场锚定机场站温度（气象站点数据），散户看市中心温度——两者 3-8°F 差 → 机构/机器人吃官方数据 vs 散户预期的差价
- **可执行项（机制可复制）**：天气市场 = 数据源确定性套利（规则写明 NOAA 站点）——核验「机场站 vs 市中心温度差」是否存在稳定偏差，若 PM 天气市场定价跟随天气 App（市中心）而结算用机场站 → 可做；需先拉几个城市温度市场的结算 vs 定价数据

### ③ Bruce 套利周会纪要（brucexu_eth 2092151224359346259）— 内容帖
- 内容：周会信息密度高——Taoli.Tools 双边对冲、TUT 从吃资金费变爆仓、爆仓后「捡尸体」、1inch 稳定币脚本、废弃 DeFi 老合约、Agent 自动化环节；学生 2W RMB→A7 历程（隐私未放）
- 定性：方法论内容，无具体 claim → 归档提取
- **可提取项**：「爆仓后捡尸体」与我们「事件驱动吃尸体」哨兵互证；Agent 自动化环节 = 我们的 cron 哨兵集群同思路；可能最后一期+精英群
- 注：BAM 笔记关联——Bruce 的跨所反向对冲做法①已被 D20 收敛率实证否决（期望值负），周会提及的「双边对冲」需注意区分

### ④ @solana 官方 Virtuals agent tokenization（2091918581755793520）— 官方可信
- 内容：Virtuals 在 Solana 上线 **agent tokenization**——把 AI agent 变成可拥有、可融资、可上链运营的业务
- 定性：官方号（4.1M 粉）可信源；AI Agent × Web3 交叉 = 用户关注方向（qintopia 架构师视角）
- **可提取项**：agent tokenization = AI×支付/融资新原语，与 Hackathon 方向（Agent×Payments）相关；记入关注清单

### ⑤ Chosmos110 Lighter 价差套利工具（2091868979505832157）— 工具帖+小实盘
- 内容：RobinHood Lighter ↔ Lighter 价差套利工具视频讲解 + 引用帖「200U 本金盈利 2U 左右」（昨天实盘）
- 定性：工具帖（08-22 已归档 Lighter V0.3 同作者）；200U→2U=1% 单日样本，小金额实盘=流程学费不是盈利验证（skill 教训）
- 定性：蚂蚁搬家策略（小额高频跨所价差）与我们跨所线相关，但工具不接入（第三方闭源 API key 风险）

### ⑥ WY_mask 费率套利平台合集（2092013078263079227）— 工具帖
- 内容：perpdexlist.com/arbitrage（年化收益计算器）+ 5 平台合集（Loris Tools/CoinGlass/Sharpe 等）
- 核验：perpdexlist.com/arbitrage 是 JS 渲染 SPA（curl 只拿到标题）→ 待浏览器核验；平台合集与我们的 funding scanner 数据源重叠
- 定性：工具参考；我们的 `funding_spread_scanner.py` + `funding_basis_viz.py` 已覆盖同类功能，perpdexlist 的价值=年化计算口径参考

## 分层利用

| 层 | 条目 | 动作 |
|---|---|---|
| 可集成 | ① v4 Hook gas 指纹 | 报价核验方法论加第 4 指纹（模拟 gas 敏感性测试） |
| 可集成 | ② 天气套利机制 | 核验 PM 天气市场「机场站结算 vs 市中心定价」偏差（数据源确定性套利候选） |
| 可提取 | ③④ | 捡尸体/Agent 自动化/agent tokenization 进关注清单 |
| 备查 | ⑤⑥ | Lighter 工具更新 + perpdexlist 待浏览器核验 |

## 红旗

- ② 是返佣帖（via=YINGGE888 + PolyCop ref），「2200 刀/周」「月赚一万刀」数字不采信；机制（机场站锚定）经核验属实可研究
- ① 的攻击「危害不亚于 MEV 夹子且更隐蔽」——聚合器 quote 污染类风险的机制级认知

## ② 深核验补记（天气套利机制验证完成）

`notes/pm-weather-arb-verify-20260825.md`：
- **温差实测（open-meteo 30 天）**：Chicago +4.0°F（机场更热）、LA -10.8°F（机场更冷）、NYC +0.1°F（无差）——老鹰「3-8°F」属实,LA 更大
- PM 天气市场确认存在且活跃（11 bin 日结,slug=highest-temperature-in-{city}-on-{date}-2026,规则锚定 NOAA 机场站）
- ⚠️ open-meteo ≠ NOAA 站点实测（Chicago 8-20:PM 结算 76-77 vs open-meteo ORD 79）——温差结论必须用 NOAA 源重验
- 下一步：逐城市确认锚定站点 + NOAA 重算 + CLOB 定价历史偏差统计
