# Solana SBF 构建故障：issue #27598

来源：

- https://github.com/solana-labs/solana/issues/27598

## 基本信息

标题：Problems with `cargo-build-(bpf|sbf)`

状态：Closed

打开时间：2022-09-05

仓库状态：`solana-labs/solana` 已在 2025-01-22 归档，只读。

## 问题

在 Solana `1.11.10` 工具链和 crates 下：

- `cargo build-bpf` 提示 `cargo-build-bpf` 已废弃，建议使用 `cargo-build-sbf`
- 随后报错找不到 `bpf-tools/rust/lib`
- `cargo build-sbf` / `cargo build-sbf --arch=sbfv2` 构建完成后，在 strip 阶段找不到 `bpf-tools/llvm/bin/llvm-objcopy`

issue 作者判断，相关工具实际可能位于 `sbf-tools/llvm/bin/llvm-objcopy`，而不是 `bpf-tools/llvm/bin/llvm-objcopy`。

## 为什么记录

Solana 开发环境经常同时涉及：

- Solana CLI 版本
- Rust toolchain
- Anchor / AVM
- `cargo build-bpf` 到 `cargo build-sbf` 的迁移
- BPF / SBF 命名变化
- 本地缓存和 release 目录

遇到构建报错时，不能只看业务代码，也要优先确认工具链版本、安装路径和 CLI 子命令是否匹配。

## 排查思路

1. 检查版本：

```bash
solana --version
anchor --version
avm --version
rustc --version
cargo --version
```

2. 确认当前项目使用的是 `build-sbf` 还是旧的 `build-bpf`。

3. 检查 Solana release 目录下 `sdk/bpf/dependencies/` 是否存在 `bpf-tools` 或 `sbf-tools`。

4. 如果报错来自旧版本工具链，优先考虑升级 Solana CLI / Anchor，而不是手动改 release 目录。

5. 如果必须复现旧项目，记录完整版本并隔离环境。

## 共学用法

这条 issue 适合放进 Solana 环境故障排查清单。它提醒我们：

- 构建失败不一定是代码问题。
- 老教程里的 `cargo build-bpf` 可能已经过时。
- Solana / Anchor 环境要记录版本，打卡时也要写清楚。

## 下一步

- 在本机跑一次 Solana / Anchor 版本检查。
- 如果创建 Anchor demo，记录 `anchor build` 和 `anchor test` 输出。
- 后续把常见构建报错整理成 `Solana 环境故障排查` 笔记。
