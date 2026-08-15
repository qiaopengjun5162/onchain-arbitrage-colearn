# HaasOnline 外衣三角套利 scam bot 拆解（2026-08-14）

> 来源：BlockBloomer 公众号/X 反诈帖（Paxon 群内分享截图 OCR）
> 定位：安全铁律落地案例——「表面套利程序背后上传私钥」的现实版（对应 Bruce 工具文安全警告）

## 一句话

一个披着 HaasOnline 外衣的「LP 三角套利 TG 机器人」骗局：Telegram bot + 完整 GitBook + 收益截图 + 专业终端图包装，核心骗术是**要求导入私钥/助记词**；官方已辟谣，已知受害者损失 4.1 BNB。

## 骗局包装特征（识别模板）

| 包装层 | 具体手法 | 红旗 |
|---|---|---|
| 品牌 | 自称「被 Haas 合并后速度提升」| 官方从未合并此类产品 |
| 文档 | 完整 GitBook，「AES-256 分片加密私钥，内存中短暂重组代签」| 高深话术翻译 = 后端可重组你的私钥并控制签名 |
| 安全背书 | 「安全与合约」页引导去 BscScan 验证合约 | **不给可核验的部署地址/BscScan 链接/第三方审计**，代码是 inferred/find similar 反编译片段 |
| 收益展示 | 黑绿星球专业终端图 + 收益截图 | 与「比特迪克」@owudjcalt 推广同品牌同界面同叙事（至少高度相似） |
| 引流 | Telegram 机器人（t.me/HaasArbitrage_）+ 推广帖 | 导流到 TG = 脱离可审计环境 |

## 证据链（按时间）

1. **8-11**：HaasOnline 官方 @haasonline 回复推广者「套利豪仔」@pritipatelfgoo 已删除推广帖：*"This is a SCAM. And is not haasbot and not affiliated with Haasonline or its products"*——官方辟谣 ✅
2. **8-13**：@RAY10168 公开陈述：看完推广后在新钱包输入私钥转入 **4.1 BNB**；一天后机器人要求再转 **6 BNB**，随后钱包资产被秒转空
3. 当事人公开了钱包地址和自称的资金流入地址

## 归因边界（重要）

- 上述为**当事人公开陈述**；「资金流入地址 = 骗子地址」的归因**仍需独立链上核验**（BscScan 查该地址是否实际收款/转出）
- 未核验前不写死结论——这是取证纪律（呼应 gross-vs-net 方法论：陈述≠证据）

## 对照我们的安全铁律

Bruce 工具文安全五规则全部适用：
1. 独立小额热钱包——受害者用的是「新钱包」✅ 正确做法，但转入 4.1 BNB 就破了小额原则
2. 不明/未开源套利程序 = 私钥上传风险——**这个案例就是活教材**
3. 真执行前必修：独立 Signer 签名机 + API Key 不提现 + allowance 管控

## 识别 check（进群友反诈清单）

- [ ] 是否要求导入私钥/助记词？→ 任何「代签」说辞 = 一票否决
- [ ] 能否给出可核验部署地址 + BscScan 链接 + 第三方审计？
- [ ] 官方品牌是否承认？(X 搜官方账号回复)
- [ ] 界面/叙事是否与已知骗局高度相似？
- [ ] 收益截图 = gross 口径？(老规矩：先过 5 问)

## 关联

- `notes/solana-prikey-security-20260809.md`（私钥安全主笔记）
- `notes/execution-reality-infra-latency-20260814.md`（Bruce 工具文安全五规则）
- 反诈信息来源：BlockBloomer 公众号（OCR 截图），原文 x.com/haasonline/status/... 与 x.com/RAY10168/status/...（链接未完整捕获，可后续补）
- **原始链接已补（2026-08-15）**：受害者陈述 `x.com/ray10168/status/2087914974215827778`（2026-08-13，48👍5RT，完整帖文+4 图归档 `sources/tg-triangle-arb-scam-ray10168_20260815.json` + `sources/tg_triangle_arb_scam_img1-4.*`）
- 帖文关键细节：骗子「套利豪仔」@pritipatelfgoo（→ 与 HaasOnline 同一伙？）；TG 机器人「套利手续费 1%」实扣**本金** 1%；一天后要求再转 6 BNB 触发警觉但已来不及，钱包秒空
- **人设立信闭环（2026-08-15 归档时发现）**：@pritipatelfgoo 正是 08-07 归档的「Polymarket 套利数学原理」笔记分享者（`notes/polymarket-arbitrage-math-framework.md`，arXiv 2608.00666 论文搬运）——完美印证受害者原话「翻了他过往的文章，感觉都是在正经分析量化跟套利」。**骗术画像 = 先搬运正经论文/分析立人设 → 再推 TG 机器人 → 诱导输入私钥**。该笔记已打警示标记（内容可独立核验但引用以论文为准）。
