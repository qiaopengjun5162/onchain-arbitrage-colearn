# Private MEV Protection RPCs: Benchmark Study（OFA 返现原始研究）

> 来源：Greenfield 报告引用（arXiv 2505.19708），用户分享
> 标题：Private MEV Protection RPCs: Benchmark Study（私有 MEV 保护 RPC 基准研究）
> 作者：Paul Janicot、Alex Vinyas（CoW DAO Research）
> 发布：2025-05-26 | 分类：econ.GN（通用经济学）
> 链接：https://arxiv.org/abs/2505.19708
> 归档：2026-08-07（Hermes 记录）

---

## 核心内容（摘要提炼）

1. **以太坊交易供应链巨变**：DeFi 交易从完全依赖公共 mempool，转向 **80% 走私有 RPC**（直接提交给 builder，跳过公共 mempool）
2. **私有 RPC 同时做 OFA**：通过订单流拍卖（Order Flow Auction）捕获 **MEV backrun 返利 + gas 返利**
3. **关键发现：不是所有 RPC/OFA 效果相同**——不同 OFA 设计对交易效率、执行质量影响显著不同
4. **对订单流发起方的含义**：选哪个 OFA 很重要（设计选择直接影响返利和用户体验）

## 与 Greenfield 报告的关联

- 报告引用此论文支撑「OFA 通过延迟且汇总的优先费退款进行返现」的判断
- 论文背景：CoW DAO Research（CoWswap 是 solver 模式代表，也是 Greenfield 投资组合）
- 数字对照：报告说「92% DEX 交易量走私有 mempool」，论文说「80% 私有 RPC」——不同口径（交易量 vs 全部交易），同一趋势

## 对共学的意义

- **solver 模式 / OFA = 散户对抗 MEV 的武器**：把执行外包给专业 solver + 通过 OFA 拿返现，散户不必为排序买单
- 个人套利者视角：理解 OFA 机制 = 理解「私有订单流」这个新战场——未来订单流拍卖会越来越主导以太坊交易供应链

## 备注

- 只有摘要归档；如需全文精读（基准测试方法、各 RPC 对比数据），可拉 PDF 全文
- 作者单位 CoW DAO Research——注意利益相关声明（CoW 是 solver 模式参与者，立场可能偏向 solver）
