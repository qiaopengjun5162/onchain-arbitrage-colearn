# 证据台账（evidence-tracker）

> 由 `scripts/evidence_harvester.py` 自动生成，每日更新。证据期 30 天，到期自动评分。
> 数据源：36 个哨兵 cron 的原始输出。最后更新：2026-08-14 23:30

## 候选状态一览

| 候选 | 状态 | 证据期 | 关键指标 | 到期判定 |
|---|---|---|---|---|
| RWA/币股闭市漂移 | 🟡 收数中 | 6/30d | samples=2161, days_covered=7, dev_bps_median=62.8, dev_bps_mean=70.5 | dev_bps 中位 ≥ 30 且覆盖 ≥ 20 天 ｜ 放弃: 30 天后 dev_bps 中位 < 20（不足以覆盖成本） |
| 链上 perp funding 拥挤度 | 🟡 收数中 | 6/30d | signal_rows=250, zscore_ge2=3, hl_extreme_annual_ge50=33 | 信号数 ≥ 10 且极端事件 ≥ 3 ｜ 放弃: 30 天零信号（拥挤度恒正常） |
| 低容量可行域（#13） | 🟡 收数中 | 2/30d | samples=983, days_covered=5, exit_events=109, max_exit_bps=77.4 | 出轨事件 ≥ 5 次且均值 > 80bps ｜ 放弃: 30 天零出轨（市场持续有效） |
| PM rebalancing 盘口 | 🟡 收数中 | 2/30d | scans=10410, days_covered=3, signal_count=0, reject_top=[('negative_after_fee', 10312), ('below_min_profit', 98)] | 事件期捕获 ≥ 3 次可执行信号 ｜ 放弃: 30 天信号率 < 1%（无事件期） |
| OFT 跨链价差 | 🟡 收数中 | 3/30d | samples=1, net_bps_mean=7.6, net_positive=0, days_covered=1 | 捕获净 > 20bps 可执行窗口 ｜ 放弃: 30 天无新上币窗口（依赖事件） |
| PM 带方向 LP（计划） | 🟡 收数中 | 2/30d | status=manual, note=待 /activity 返佣流水（人工） | 返佣率 vs 被吃单率 vs 胜率 paper 验证通过 ｜ 放弃: 返佣率不可覆盖点差 |

## 详细快照

### RWA/币股闭市漂移
`stock_drift` · 证据期 2026-08-08 起 · 快照数 2

```json
{
  "samples": 2161,
  "days_covered": 7,
  "dev_bps_median": 62.8,
  "dev_bps_mean": 70.5,
  "dev_bps_max": 345.0,
  "pct_ge_30bps": 97.0
}
```

### 链上 perp funding 拥挤度
`perp_funding` · 证据期 2026-08-08 起 · 快照数 2

```json
{
  "signal_rows": 250,
  "zscore_ge2": 3,
  "hl_extreme_annual_ge50": 33
}
```

### 低容量可行域（#13）
`thin_corridor` · 证据期 2026-08-12 起 · 快照数 2

```json
{
  "samples": 983,
  "days_covered": 5,
  "exit_events": 109,
  "max_exit_bps": 77.4,
  "spread_mean_bps": 30.0
}
```

### PM rebalancing 盘口
`pm_rebal` · 证据期 2026-08-12 起 · 快照数 2

```json
{
  "scans": 10410,
  "days_covered": 3,
  "signal_count": 0,
  "reject_top": [
    [
      "negative_after_fee",
      10312
    ],
    [
      "below_min_profit",
      98
    ]
  ]
}
```

### OFT 跨链价差
`oft_crosschain` · 证据期 2026-08-11 起 · 快照数 2

```json
{
  "samples": 1,
  "net_bps_mean": 7.6,
  "net_positive": 0,
  "days_covered": 1
}
```

### PM 带方向 LP（计划）
`pm_lp` · 证据期 2026-08-12 起 · 快照数 2

```json
{
  "status": "manual",
  "note": "待 /activity 返佣流水（人工）"
}
```
