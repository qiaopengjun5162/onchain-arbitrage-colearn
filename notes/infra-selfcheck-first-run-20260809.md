# 基础设施自检哨兵实战记录（2026-08-09）

> 脚本：`scripts/infra_selfcheck.py`（对应 `notes/node-infra-acceptance-checklist-20260808.md` 落地）
> 触发：群讨论「系统没打磨好风控做好根本不敢上仓位」→ 先建基建自检
> 首次运行即抓到 2 个真实数据源问题 + 1 个环境坑

## 运行结果（2026-08-09 01:58 UTC）

| 端点 | 状态 | P50 | P99.9 | 可用 | 说明 |
|---|---|---|---|---|---|
| okx | 🟡 | 496ms | 510ms | 100% | 走代理，P50 偏高属代理常态 |
| bitget | 🟡 | 523ms | 537ms | 100% | 同上 |
| kucoin | 🟡 | 512ms | 522ms | 100% | 同上 |
| gate | 🟡 | 972ms | 991ms | 100% | 最慢，接近 WARN 阈值 |
| helius_rpc | 🔴* | 386ms | 388ms | 0%* | *execute_code 环境无 key 误报；真实 shell 200 |
| jupiter | 🔴→🟡 | 458ms | 460ms | 71% | 旧端点已下线，修好后 5/7 可用 |
| defisphere | 🟢 | 398ms | 414ms | 100% | 修正路径后全通 |
| lifi | 🟡 | 787ms | 992ms | 100% | SD 183ms 抖动大 |

## 发现 1：defisphere 裸路径 404（已修）

- 误用 `https://sphere.data.blockanalitica.com/liquidations` → 404
- 真实调用必须带完整 query params：`sort/networks/from_date/to_date/limit/page`
- `scripts/liquidation_monitor.py` 里的 `fetch_liquidations()` 一直是对的，自检脚本抄错了裸路径

## 发现 2：Jupiter v6 端点已官方下线（已修，含遗留 bug）

- `quote-api.jup.ag/v6/quote` 官方 2025-10-01 弃用（Solana StackExchange + @JupDevRel 公告确认）
- 新端点：`api.jup.ag/swap/v1/quote`（Metis 路由引擎），token mint 必须**小写**（USDC `EPjFWdd5...ZwyTDt1v`）
- **顺手修掉 `scripts/jupiter_quote.py` 的遗留旧端点 bug**（知识库 2026-08-07 已记录新端点，但这个脚本没改）

## 发现 3：execute_code/subprocess 不加载 shell env

- `HELIUS_API_KEY` 在 ~/.zshrc / hermes env 文件里
- execute_code 的 subprocess 环境不继承 → helius_rpc 误报 0%
- 真实 cron/terminal 环境正常（手动验证 200）
- **教训**：自检脚本必须用真实 shell 跑（cron 或 `bash -lc 'source ~/.zshrc && ...'`），不要在 execute_code 里判死刑

## 结论

1. 基础设施自检能抓到真问题——第一跑就发现 Jupiter 断供（脚本 `jupiter_quote.py` 会 404，跨所价差监控 `solana_dex_spread_monitor.py` 用的是新端点没事）
2. **这直接回答「不敢上仓位」**：数据源静默失效（404 不报错、DNS 通但连接挂）是最隐蔽的系统风险——哨兵先于资金发现它
3. 待办：把自检挂 cron（每小时，只报黄/红）、liquidation_monitor 的 API 路径注释里补一句「必须带完整 params」
