# Nunchi agent-cli 核验：HL 14 策略开源（2026-08-21 群分享）

> 来源：https://x.com/xincctnnq/status/2032772661722624497（币圈女菩萨 Pizza，104k followers，517 likes）
> Repo：https://github.com/Nunchi-trade/agent-cli
> 归档日期：2026-08-21 ｜ 核验方法：GitHub API + README

## 核验结论

- ✅ **repo 真实存在**：515 stars，Python，2026-02-25 创建，2026-08-17 仍在更新
- 14 个策略：做市/动量/套利/LLM 驱动（APEX 多槽编排 + REFLECT 夜间复盘 + Radar 机会筛选 + Pulse 动量检测 + Guard 跟踪止损）
- 形态：独立 CLI / Claude Code skill / OpenClaw AgentSkill / **MCP server（24 tools）**
- 483 测试通过，MIT license，有 docs/app/research 完整生态

## 与我们的关系

1. **「公开开源策略 = 无 edge」今天第 6 次验证**（套利豪仔/awesome/quant-trading/PM bot×2/本 repo）——但帖主自己说了正确的话：「开源策略能学到逻辑但别直接上真金白银，先模拟盘跑两周看回撤」——**难得有良心的推广**
2. **真正可参考的**：MCP server 形态（24 tools）——与我们 Hermes 的 native MCP 对接直接相关；APEX orchestrator + REFLECT 复盘架构与我们「机器执行+人只定阈值」理念同构
3. 策略逻辑本身（基差/资金费率收割/做市/网格）我们都已研究过——无新增量

## 结论

- 工具形态可参考（MCP server 集成模式），策略本身无增量
- 「开源≠能赚钱」再次确认；帖主风控提示与我们的认知一致
- 无新研究动作
