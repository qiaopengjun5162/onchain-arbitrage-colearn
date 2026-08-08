# Solana Rust 工具链不一致：issue #34987

来源：

- https://github.com/solana-labs/solana/issues/34987

## 基本信息

标题：`solana-program v1.18.0` cannot be built because it requires rustc 1.72.0 or newer, while the currently active rustc version is 1.68.0-dev

状态：Closed as not planned

打开时间：2024-01-27

仓库状态：`solana-labs/solana` 已在 2025-01-22 归档，只读。

## 问题

用户使用 Anchor framework 运行 `anchor build`，遇到报错：

```text
error: package `solana-program v1.18.0` cannot be built because it requires rustc 1.72.0 or newer, while the currently active rustc version is 1.68.0-dev
```

但用户在终端里确认 `rustc --version` 是 `1.72.0`。

## 为什么记录

这个问题提醒我们：终端里的 `rustc --version` 不一定等于 `anchor build` / Solana SBF 构建实际使用的 Rust。

Solana/Anchor 构建可能涉及多套版本：

- 系统或 rustup 当前 Rust
- Solana CLI 自带的 platform-tools / SBF Rust
- Anchor / AVM 选择的 Anchor 版本
- `solana-program` crate 版本
- 项目里的 `Cargo.lock`

所以看到 “rustc 太旧” 不能只看全局 `rustc --version`，要查构建链路实际调用的工具链。

## 排查思路

1. 检查基础版本：

```bash
rustc --version
cargo --version
solana --version
anchor --version
avm --version
```

2. 检查项目依赖：

```bash
rg "solana-program|anchor-lang" Cargo.toml Cargo.lock
```

3. 检查是否混用了不匹配的版本：

- `solana-program = 1.18.x`
- Anchor 版本过旧
- Solana CLI / platform-tools 过旧
- `Cargo.lock` 锁住了不兼容版本

4. 优先让 Solana CLI、Anchor、`anchor-lang`、`solana-program` 版本处在同一代，而不是局部升级一个 crate。

5. 如果是旧项目复现，先记录完整版本矩阵，再考虑用隔离环境处理。

## 共学用法

这条 issue 应放进 Solana 环境故障排查清单。

它适合提醒打卡时记录：

- Rust 版本
- Solana CLI 版本
- Anchor/AVM 版本
- `anchor-lang` 版本
- `solana-program` 版本
- 失败命令和完整报错

## 下一步

把 `issue #27598` 和 `issue #34987` 合并整理成一篇：

`Solana / Anchor 构建环境故障排查`

重点覆盖：

- `build-bpf` 到 `build-sbf`
- BPF/SBF 工具路径
- Rust 版本不一致
- Solana CLI / Anchor / crate 版本矩阵
- 旧教程和新工具链冲突
