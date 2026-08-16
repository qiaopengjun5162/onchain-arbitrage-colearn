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
]

# slug -> 实际日期（覆盖全局 DATE；manifest 里按笔记实际日期登记）
DATE_OVERRIDES = {
    "l0009-knowledge-graph-v1-20260813": "2026-08-13",
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
