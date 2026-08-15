# 两帖归档：三角套利 TG 骗局原始陈述 + 冰火岛开源套利工具清单（2026-08-15）

> 归档：2026-08-15（Hermes 记录，Paxon 群内分享）
> 来源 1：受害者陈述 https://x.com/ray10168/status/2087914974215827778（@RAY10168，2026-08-13）
> 来源 2：GitHub 开源列表 https://x.com/wepoets1107/status/2088217033557315961（@wepoets1107 张无忌，2026-08-14）
> 关联：`notes/haasonline-scam-bot-case-20260814.md`、`notes/polymarket-arbitrage-math-framework.md`（⚠️ 来源账号=骗子）

## 一、三角套利 TG 机器人骗局：受害者原始陈述（与 HaasOnline 案例同源）

**关键事实**（原始帖文 48👍 5RT，归档 `sources/tg-triangle-arb-scam-ray10168_20260815.json` + 4 图）：

- 骗子：**「套利豪仔」@pritipatelfgoo**——受害者描述「翻了他过往的文章，感觉都是在正经分析量化跟套利」
- 流程：X 推广三角套利 TG 机器人 → 新建钱包输入私钥（受害者犹豫过，但以往链上 TG 机器人也常这种模式）→ 转入 4.1 BNB → 第一天正常
- 破绽：宣称「套利手续费 1%」实扣的是**本金** 1%（精算才发现）
- 爆发：一天后机器人报错要求再转 6 BNB → 警觉但已来不及 → **钱包秒被转空**
- 事后：套利豪仔和「客服」是一伙的

**⚠️ 人设立信闭环（本次归档的核心发现）**：@pritipatelfgoo 正是 08-07 归档的「Polymarket 套利数学原理」笔记分享者（arXiv 2608.00666 论文搬运）——**骗子先用正经论文分析立人设（8/7），两周后推 TG 机器人收割（8/13）**。完美印证受害者原话。该笔记已打警示标记。

**骗术画像**：搬运正经论文/分析立人设 → 推 TG 机器人 → 诱导输入私钥 → 小额试运行正常（养信任）→ 大额转入后秒空。

## 二、冰火岛社区 GitHub 开源清单（期权 + 量化策略，30 仓库）

**作者**：张无忌 @wepoets1107，155👍 28RT。自称「所有项目测试稳定才上传」。

**仓库抽查结果**（2026-08-15，5 个代表性仓库全部真实存在 + 代码验真）：

| 仓库 | Star | 定位 | 验真 |
|---|---|---|---|
| options-eye | 11 | Deribit 期权 IV 曲面异常扫描器 | ✅ 存在 |
| icefire-options-workbench | 25 | 本地 BTC/ETH 期权看板（Gamma/Skew/IV） | ✅ 存在 |
| backpack-arbitrage | 44 | **Backpack 资金费率套利交易脚本**（ccxt 4.x） | ✅ 代码已抽查 |
| btc-yield-enhancer | 68 | Deribit 现货 maker 网格 | ✅ 存在 |
| chanlun-trade-signal | 19 | 缠论交易信号工作台 | ✅ 存在 |

**backpack-arbitrage 代码审计**（与套利最相关，拉取 `bpx_arb_ccxt.py` 33KB 全文扫描）：
- ✅ ccxt 标准库（含 SDK 迁移说明），Flask 本地看板
- ✅ API key 从环境变量读取（`BPX_PUBLIC_KEY`/`BPX_SECRET_KEY` via `os.environ.get`），无硬编码
- ✅ 配置文件读取（.env 风格 `k=v` 写入 environ）
- ✅ DRY_RUN 默认开启（`BPX_LIVE=1` 才实盘）
- ✅ 无 eval/exec/subprocess、无网络外发、无私钥/助记词特征
- ✅ 附 `bpx-arbitrage-plan.md` / `bpx-signal-plan.md`（策略规划文档，说明是认真做项目）

**判断**：与骗局账号（套利豪仔）形成对照——开源 + 可审计 + 默认 dry-run = 正常工具特征；私钥诱导 + 收益截图 + 闭环 TG = 骗局特征。**任何工具「是否开源可审计」是第一道过滤器。**

## 三、对我们研究线的增量

1. **反诈清单再+1 信号**：「搬运正经分析立人设」是骗子前置动作——**归档任何 X 分享的「分析文」时，若分享者后续被证实为骗子，笔记必须打来源警示**（已对 polymarket-arbitrage-math-framework 执行）
2. **工具验证三问升级**：代码可审计吗 → 默认 dry-run 吗 → key 怎么管理？三问全过才谈得上试用
3. **backpack-arbitrage 与我们的关系**：资金费率套利已有 4 条研究线（青蛙 488 天回测/李胜利 1200%/跨所 carry/期现模型），此仓库是「Backpack 单所」实现——可作参考实现，不新增研究线
4. **期权方向**（options-eye 等 12 个工具）超出当前 21 天共学范围，记入 backlog 观察，不展开

## 四、待办

- [ ] 若后续再归档 @pritipatelfgoo 相关内容，先查本笔记警示标记
- [ ] 冰火岛其余 25 仓库如需使用再逐个验真（本次已覆盖与套利最相关的 5 个）
