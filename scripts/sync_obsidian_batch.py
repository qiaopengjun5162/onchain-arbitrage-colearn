#!/usr/bin/env python3
"""
Obsidian 增量同步脚本（manifest 驱动）
- 读 notes/<slug>.md
- 补/替换 frontmatter（title/date/type/tags）
- 把正文里 `notes/<slug>.md` 引用重写为 vault 双链 [[中文名]]
- 同时写入真实 vault 和项目内 obsidian/ 镜像
- 不删除任何文件，幂等可重复运行
"""
import os
import re

NOTES = "/Users/qiaopengjun/Code/Solana/onchain-arbitrage-colearn/notes"
VAULT = "/Users/qiaopengjun/Library/Mobile Documents/iCloud~md~obsidian/Documents/ObsidianVault/链上套利共学"
MIRROR = "/Users/qiaopengjun/Code/Solana/onchain-arbitrage-colearn/obsidian"
DATE = "2026-08-08"

# (slug, 目标区块目录, vault中文标题, tag)
MANIFEST = [
    ("robinhood-arb-0xd7121208-address-research-20260808", "02 市场地图", "Robinhood 0xD712 套利地址解剖", "market-map"),
    ("aave-liquidator-0x8d64d775-address-research-20260808", "02 市场地图", "Aave 清算者 0x8d64 解剖", "market-map"),
    ("astro-cex-arbitrage-product-20260808", "02 市场地图", "Astro CEX 套利产品调研", "market-map"),
    ("research-the-person-week2-20260807", "02 市场地图", "清算人研究方法论 Week2", "market-map"),
    ("arbitrage-track-selection-20260808", "03 策略假设", "赛道选择结论", "strategy"),
    ("cex-spread-arb-demo-decision-20260808", "03 策略假设", "跨所价差套利 Demo 决策", "strategy"),
    ("ma-cross-trend-strategy-review-20260808", "06 失败复盘", "MA 均线交叉策略回测复盘", "postmortem"),
    ("group-discussion-flashloan-atomic-arbitrage-20260807", "07 共学群友", "群讨论：原子套利闪电贷", "colearners"),
    ("group-discussion-timestamp-alignment-20260807", "07 共学群友", "群讨论：储备同区块与时间序列对齐", "colearners"),
    ("arbitrage-playbook-text-version", "04 工具与协议", "套利实战手册", "playbook"),
    ("defi-arbitrage-capital-guide", "03 策略假设", "套利资本指南", "strategy"),
    ("monitoring-bot-quickstart", "04 工具与协议", "监控 Bot 入门", "tool"),
    ("l0009-knowledge-graph-v1-20260813", "03 策略假设", "知识图谱 v1 · 阶段二收官", "strategy"),
    ("ai-agent-workflow-tools-20260821", "04 工具与协议", "AI Agent 工作流工具（Ailu + 微信 CLI）", "tool"),
    ("qqq-tqqq-15yr-verify-20260821", "02 市场地图", "QQQ-TQQQ 十五年核验与被动基准", "market-map"),
    ("coolshell-outperform-most-people-20260821", "01 角色与配置", "学习方法论：如何超过大多数人", "methodology"),
    ("funding-arb-execution-delta-spread-20260821", "03 策略假设", "资金费套利执行认知（价差是生死线）", "strategy"),
    ("first-sf-trade-rehearsal-20260822", "03 策略假设", "实操第一课：筛选流水线（牛市叙事→算账→结论）", "strategy"),
    ("mistaken-limit-order-arb-line-20260822", "03 策略假设", "错误限价单事件：别人的错误=我们的猎物", "strategy"),
    ("d18-backtest-event-window-20260822", "03 策略假设", "D18 回测：跨池价差 12 天终审出局", "strategy"),
    ("daily-share-archive-20260822", "07 共学群友", "今日分享批量归档：量化工具+交易哲学", "colearners"),
    ("d17-corridor-spread-histogram-20260821", "02 市场地图", "D17 跨池价差 11 天分布回测", "market-map"),
    ("d18-backtest-event-window-20260821", "02 市场地图", "D18 回测事件窗口标注 v0", "market-map"),
    ("bruce-investment-rules-20260821", "07 共学群友", "Bruce 投资归因规律与套利六级淘汰", "colearners"),
    ("solana-blind-arb-bot-R32xAccFis-20260821", "02 市场地图", "Solana 盲套利 Bot R32xAccFis 取证", "market-map"),
    ("awesome-systematic-trading-collection-20260821", "04 工具与协议", "awesome-systematic-trading 合集核验", "tool"),
    ("hayden-correlated-pairs-amm-cody-20260821", "02 市场地图", "Hayden 相关配对 AMM 与 Cody 实测", "market-map"),
    ("hermes-plugin-ecosystem-verify-20260821", "04 工具与协议", "Hermes 插件生态核验", "tool"),
    ("shiboss-pm-bot-verify-20260821", "07 共学群友", "十老板复盘与 PM bot 标题党核验", "colearners"),
    ("hip3-preipo-perps-entropy-20260821", "02 市场地图", "HIP-3 Pre-IPO Perps 与 Entropy 核验", "market-map"),
    ("hip3-market-scan-csop-etf-20260821", "02 市场地图", "HIP-3 市场实测与 CSOP 海力士 ETF 套利", "market-map"),
    ("market-structure-alpha-5-sources-20260821", "02 市场地图", "市场玩家结构与 Alpha 五来源", "market-map"),
    ("pm-bot-narratives-quant-trading-20260821", "07 共学群友", "PM 机器人叙事与 quant-trading 核验", "colearners"),
    ("whale-intel-verify-20260821", "02 市场地图", "巨鲸情报与浮盈双核验", "market-map"),
    ("dusd-addr-verify-20260821", "03 策略假设", "DUSD 地址核验（收益稳定币家族）", "strategy"),
    ("weekly-meeting-tut-postmortem-20260821", "07 共学群友", "周会实录：TUT 爆仓一手复盘", "colearners"),
    ("sol-whale-verify-20260821", "02 市场地图", "SOL 巨鲸浮盈核验（软造假第三例）", "market-map"),
    ("jito-bam-35ms-20260821", "04 工具与协议", "Jito BAM 拍卖 50ms→35ms 变更", "tool"),
    ("volaset-solana-official-20260821", "03 策略假设", "VolaSet 协议观察与 Solana 官方两帖", "strategy"),
    ("chain-scanning-method-hunter-20260821", "01 角色与配置", "扫链方法论（速度×准确度）", "methodology"),
    ("ramp-x402-agent-payments-20260821", "04 工具与协议", "Ramp × x402：Agent 支付接入企业账本", "tool"),
    ("aave-v3-batch-liquidation-forensics-20260821", "02 市场地图", "Aave V3 批量清算交易取证", "market-map"),
    ("dragon-addr-verify-20260821", "02 市场地图", "龙王地址核验（pre-IPO 主战场）", "market-map"),
    ("finance-knowledge-system-digest-20260821", "01 角色与配置", "金融知识体系终极指南 digest", "methodology"),
    ("guilin-trading-mindset-quant-roadmap-20260821", "01 角色与配置", "桂林交易心法与量化路线图", "methodology"),
    ("nunchi-agent-cli-verify-20260821", "04 工具与协议", "Nunchi agent-cli 核验（HL 14 策略）", "tool"),
    ("hype-whale-verify-20260821", "02 市场地图", "HYPE 巨鲸浮盈核验", "market-map"),
    ("info-gap-repos-verify-20260821", "04 工具与协议", "信息差套利 5 仓库核验", "tool"),
    ("bsc-redeem-collateral-forensics-20260821", "02 市场地图", "BSC redeemCollateral 抵押品赎回取证", "market-map"),
    ("bsc-flashloan-repay-forensics-20260821", "02 市场地图", "BSC execute 闪贷还贷取证", "market-map"),
    ("pm-yesno-lock-verify-20260821", "07 共学群友", "Crypto老鹰 PM 锁利机器人核验", "colearners"),
    ("solana-explorer-update-20260821", "04 工具与协议", "Solana Explorer 新功能", "tool"),
    ("rise-chain-ecosystem-20260821", "02 市场地图", "RISE 链生态观察", "market-map"),
    ("d19-four-direction-comparison-20260823", "03 策略假设", "D19 四方向深度对比表 v1", "strategy"),
    ("binance-etf-contract-arb-20260823", "03 策略假设", "币安 ETF 合约套利（周末窗口）", "strategy"),
    ("cost-model-template-gas-semantic-20260823", "04 工具与协议", "成本模型模板（含 gas 语义检查）", "tool"),
    ("group-share-five-verify-20260823", "07 共学群友", "群分享五连核验（Lighter/筛选法/窄赛道/归集/逆势）", "colearners"),
    ("group-share-triple-verify-20260823", "07 共学群友", "群分享三连核验（ETF套利/a-stock-data/Boros）", "colearners"),
    ("support-resistance-tutorial-20260823", "06 失败复盘", "48K纯白 支撑压力位教程", "postmortem"),
    ("sec-supply-side-reform-20260823", "02 市场地图", "加密供给侧改革与 SEC 代币融资豁免", "market-map"),
    ("hermes-tailscale-server-init-20260823", "04 工具与协议", "Hermes + Tailscale 服务器初始化工作流", "tool"),
    ("hermes-telegram-workstation-20260823", "04 工具与协议", "Hermes + Telegram 多任务工作台", "tool"),
    ("laoying-pm-5min-script-verify-20260823", "07 共学群友", "Crypto老鹰 PM 5min 脚本推广核验（返佣矩阵#1）", "colearners"),
    ("pm-winners-behavior-20260823", "03 策略假设", "PM 赢家行为研究：14,441 地址筛出 12 赢家", "strategy"),
    ("pm-position-building-20260823", "03 策略假设", "PM 仓位构建：50% 胜率怎么赢", "strategy"),
    ("laoying-pm-15min-assistant-verify-20260823", "07 共学群友", "Crypto老鹰 PM 15min 助手推广核验（返佣矩阵#2）", "colearners"),
    ("skew-kurtosis-trading-20260823", "03 策略假设", "偏度/曲率交易：事件窗口=尾部收益化", "strategy"),
    ("pm-concentrated-betting-20260823", "03 策略假设", "PM 极简重注案例：确定性>出手次数", "strategy"),
    ("laoying-pm-news-arb-verify-20260823", "07 共学群友", "Crypto老鹰 PM 新闻套利推广核验（返佣矩阵#3）", "colearners"),
    ("zcash-state-bloat-trump-trades-20260823", "02 市场地图", "Zcash 屏蔽池数据爆炸 + 特朗普账户程序化交易", "market-map"),
    ("term-finance-governance-attack-forensics-20260823", "02 市场地图", "Term Finance 治理攻击取证（份额质押投票权俘获）", "market-map"),
    ("solana-weekly-20260823", "02 市场地图", "Solana 官方周报：币股 RWA 三连击", "market-map"),
    ("solana-native-bstock-lly-mrna-20260823", "03 策略假设", "Solana 原生币股：LLY/MRNA 闭市漂移实测", "strategy"),
    ("taoli-tools-practice-cognition-20260823", "03 策略假设", "taoli tools 实操认知：大部分时间不成交", "strategy"),
]

# slug -> 实际日期（覆盖全局 DATE；manifest 里按笔记实际日期登记）
DATE_OVERRIDES = {
    "l0009-knowledge-graph-v1-20260813": "2026-08-13",
    "ai-agent-workflow-tools-20260821": "2026-08-21",
    "qqq-tqqq-15yr-verify-20260821": "2026-08-21",
    "coolshell-outperform-most-people-20260821": "2026-08-21",
    "funding-arb-execution-delta-spread-20260821": "2026-08-21",
    "first-sf-trade-rehearsal-20260822": "2026-08-22",
    "d17-corridor-spread-histogram-20260821": "2026-08-21",
    "d18-backtest-event-window-20260821": "2026-08-21",
    "bruce-investment-rules-20260821": "2026-08-21",
    "solana-blind-arb-bot-R32xAccFis-20260821": "2026-08-21",
    "awesome-systematic-trading-collection-20260821": "2026-08-21",
    "hayden-correlated-pairs-amm-cody-20260821": "2026-08-21",
    "hermes-plugin-ecosystem-verify-20260821": "2026-08-21",
    "shiboss-pm-bot-verify-20260821": "2026-08-21",
    "hip3-preipo-perps-entropy-20260821": "2026-08-21",
    "hip3-market-scan-csop-etf-20260821": "2026-08-21",
    "market-structure-alpha-5-sources-20260821": "2026-08-21",
    "pm-bot-narratives-quant-trading-20260821": "2026-08-21",
    "whale-intel-verify-20260821": "2026-08-21",
    "dusd-addr-verify-20260821": "2026-08-21",
    "weekly-meeting-tut-postmortem-20260821": "2026-08-21",
    "sol-whale-verify-20260821": "2026-08-21",
    "jito-bam-35ms-20260821": "2026-08-21",
    "volaset-solana-official-20260821": "2026-08-21",
    "chain-scanning-method-hunter-20260821": "2026-08-21",
    "ramp-x402-agent-payments-20260821": "2026-08-21",
    "aave-v3-batch-liquidation-forensics-20260821": "2026-08-21",
    "dragon-addr-verify-20260821": "2026-08-21",
    "finance-knowledge-system-digest-20260821": "2026-08-21",
    "guilin-trading-mindset-quant-roadmap-20260821": "2026-08-21",
    "nunchi-agent-cli-verify-20260821": "2026-08-21",
    "hype-whale-verify-20260821": "2026-08-21",
    "info-gap-repos-verify-20260821": "2026-08-21",
    "bsc-redeem-collateral-forensics-20260821": "2026-08-21",
    "bsc-flashloan-repay-forensics-20260821": "2026-08-21",
    "pm-yesno-lock-verify-20260821": "2026-08-21",
    "d19-four-direction-comparison-20260823": "2026-08-23",
    "binance-etf-contract-arb-20260823": "2026-08-23",
    "cost-model-template-gas-semantic-20260823": "2026-08-23",
    "group-share-five-verify-20260823": "2026-08-23",
    "group-share-triple-verify-20260823": "2026-08-23",
    "support-resistance-tutorial-20260823": "2026-08-23",
    "sec-supply-side-reform-20260823": "2026-08-23",
    "hermes-tailscale-server-init-20260823": "2026-08-23",
    "hermes-telegram-workstation-20260823": "2026-08-23",
    "laoying-pm-5min-script-verify-20260823": "2026-08-23",
    "pm-winners-behavior-20260823": "2026-08-23",
    "pm-position-building-20260823": "2026-08-23",
    "laoying-pm-15min-assistant-verify-20260823": "2026-08-23",
    "skew-kurtosis-trading-20260823": "2026-08-23",
    "pm-concentrated-betting-20260823": "2026-08-23",
    "laoying-pm-news-arb-verify-20260823": "2026-08-23",
    "zcash-state-bloat-trump-trades-20260823": "2026-08-23",
    "term-finance-governance-attack-forensics-20260823": "2026-08-23",
    "solana-weekly-20260823": "2026-08-23",
    "solana-native-bstock-lly-mrna-20260823": "2026-08-23",
    "taoli-tools-practice-cognition-20260823": "2026-08-23",
}

# slug -> vault 中文名（用于重写内部双链，覆盖 vault 已有 + 本轮新增）
LINK_MAP = {
    "arbitrage-framework-first-principles": "套利第一性原理框架",
    "arbitrage-strategy-landscape": "套利策略全景",
    "execution-checklist-5-steps": "执行清单五步法",
    "lp-dynamic-range": "LP 动态区间",
    "case-toll-fee-pool": "收过路费池",
    "boros-pendle-crossex-4leg": "Boros 跨所套利四腿",
    "robinhood-chain-arbitrage-case-20260807": "Robinhood Chain 三角套利实战",
    "learned-arbitrage-projects": "学习过的开源套利项目",
    "zacholme7-resources": "Zacholme7 资源归档",
    "case-stat-arb-0xbdb3ba-450k": "0xbdb3ba 统计套利案例",
    "jaredfromsubway-honeypot-20260807": "JaredFromSubway 蜜罐反杀",
    "toll-fee-pool-backtest-falsified-20260805": "收费站套利回测证伪",
    "excellent-notes-analysis-20260806": "共学优秀笔记分析",
    "hermes-setup-bruce-guide": "Hermes Agent",
    "lifi-crosschain-120-rounds-report": "LI.FI 跨链可执行价差 120 轮实测",
    "lifi-cost-observation-methodology": "LI.FI 成本观测方法论",
    "lifi-experiment-20260806": "LI.FI 跨链实战实验",
    "aggregator-routing": "聚合路由",
    "research-the-person-week2-20260807": "清算人研究方法论 Week2",
    "astro-cex-arbitrage-product-20260808": "Astro CEX 套利产品调研",
    "aave-liquidator-0x8d64d775-address-research-20260808": "Aave 清算者 0x8d64 解剖",
    "robinhood-arb-0xd7121208-address-research-20260808": "Robinhood 0xD712 套利地址解剖",
    "arbitrage-track-selection-20260808": "赛道选择结论",
    "cex-spread-arb-demo-decision-20260808": "跨所价差套利 Demo 决策",
    "ma-cross-trend-strategy-review-20260808": "MA 均线交叉策略回测复盘",
    "group-discussion-flashloan-atomic-arbitrage-20260807": "群讨论：原子套利闪电贷",
    "group-discussion-timestamp-alignment-20260807": "群讨论：储备同区块与时间序列对齐",
    "arbitrage-playbook-text-version": "套利实战手册",
    "defi-arbitrage-capital-guide": "套利资本指南",
    "monitoring-bot-quickstart": "监控 Bot 入门",
    "coolshell-outperform-most-people-20260821": "学习方法论：如何超过大多数人",
    "funding-arb-execution-delta-spread-20260821": "资金费套利执行认知（价差是生死线）",
    "first-sf-trade-rehearsal-20260822": "实操第一课：筛选流水线（牛市叙事→算账→结论）",
    "d17-corridor-spread-histogram-20260821": "D17 跨池价差 11 天分布回测",
    "d18-backtest-event-window-20260821": "D18 回测事件窗口标注 v0",
    "bruce-investment-rules-20260821": "Bruce 投资归因规律与套利六级淘汰",
    "solana-blind-arb-bot-R32xAccFis-20260821": "Solana 盲套利 Bot R32xAccFis 取证",
    "awesome-systematic-trading-collection-20260821": "awesome-systematic-trading 合集核验",
    "hayden-correlated-pairs-amm-cody-20260821": "Hayden 相关配对 AMM 与 Cody 实测",
    "hermes-plugin-ecosystem-verify-20260821": "Hermes 插件生态核验",
    "shiboss-pm-bot-verify-20260821": "十老板复盘与 PM bot 标题党核验",
    "hip3-preipo-perps-entropy-20260821": "HIP-3 Pre-IPO Perps 与 Entropy 核验",
    "hip3-market-scan-csop-etf-20260821": "HIP-3 市场实测与 CSOP 海力士 ETF 套利",
    "market-structure-alpha-5-sources-20260821": "市场玩家结构与 Alpha 五来源",
    "pm-bot-narratives-quant-trading-20260821": "PM 机器人叙事与 quant-trading 核验",
    "whale-intel-verify-20260821": "巨鲸情报与浮盈双核验",
    "dusd-addr-verify-20260821": "DUSD 地址核验（收益稳定币家族）",
    "weekly-meeting-tut-postmortem-20260821": "周会实录：TUT 爆仓一手复盘",
    "sol-whale-verify-20260821": "SOL 巨鲸浮盈核验（软造假第三例）",
    "jito-bam-35ms-20260821": "Jito BAM 拍卖 50ms→35ms 变更",
    "volaset-solana-official-20260821": "VolaSet 协议观察与 Solana 官方两帖",
    "chain-scanning-method-hunter-20260821": "扫链方法论（速度×准确度）",
    "ramp-x402-agent-payments-20260821": "Ramp × x402：Agent 支付接入企业账本",
    "aave-v3-batch-liquidation-forensics-20260821": "Aave V3 批量清算交易取证",
    "dragon-addr-verify-20260821": "龙王地址核验（pre-IPO 主战场）",
    "finance-knowledge-system-digest-20260821": "金融知识体系终极指南 digest",
    "guilin-trading-mindset-quant-roadmap-20260821": "桂林交易心法与量化路线图",
    "nunchi-agent-cli-verify-20260821": "Nunchi agent-cli 核验（HL 14 策略）",
    "hype-whale-verify-20260821": "HYPE 巨鲸浮盈核验",
    "info-gap-repos-verify-20260821": "信息差套利 5 仓库核验",
    "bsc-redeem-collateral-forensics-20260821": "BSC redeemCollateral 抵押品赎回取证",
    "bsc-flashloan-repay-forensics-20260821": "BSC execute 闪贷还贷取证",
    "pm-yesno-lock-verify-20260821": "Crypto老鹰 PM 锁利机器人核验",
}


def build_frontmatter(title: str, tag: str, date: str) -> str:
    return (
        f"---\n"
        f"title: {title}\n"
        f"date: {date}\n"
        f"type: note\n"
        f"tags:\n"
        f"  - onchain-arbitrage\n"
        f"  - {tag}\n"
        f"---\n\n"
    )


def rewrite_links(text: str) -> str:
    def repl(m: re.Match) -> str:
        slug = m.group(1)
        return f"[[{LINK_MAP[slug]}]]" if slug in LINK_MAP else m.group(0)
    return re.sub(r"notes/([A-Za-z0-9\-]+)\.md", repl, text)


def main() -> None:
    synced, missed = [], []
    for slug, ddir, title, tag in MANIFEST:
        src = os.path.join(NOTES, slug + ".md")
        if not os.path.exists(src):
            missed.append(slug)
            print(f"[MISS] {slug}")
            continue
        with open(src, encoding="utf-8") as f:
            content = f.read()
        # 剥离已有 frontmatter（若存在）
        if content.lstrip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].lstrip("\n")
        body = rewrite_links(content)
        date = DATE_OVERRIDES.get(slug, DATE)
        out = build_frontmatter(title, tag, date) + body

        vpath = os.path.join(VAULT, ddir, title + ".md")
        mpath = os.path.join(MIRROR, ddir, title + ".md")
        os.makedirs(os.path.dirname(vpath), exist_ok=True)
        os.makedirs(os.path.dirname(mpath), exist_ok=True)
        with open(vpath, "w", encoding="utf-8") as f:
            f.write(out)
        with open(mpath, "w", encoding="utf-8") as f:
            f.write(out)
        synced.append(f"{ddir}/{title}")
        print(f"[OK] {slug} -> {ddir}/{title}")

    print(f"\n=== 同步完成：{len(synced)} 成功, {len(missed)} 缺失 ===")


if __name__ == "__main__":
    main()
