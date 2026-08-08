# Anza Wallet Adapter Example

来源：

- https://github.com/anza-xyz/wallet-adapter
- https://anza-xyz.github.io/wallet-adapter/example/

## 定位

Anza Wallet Adapter 是 Solana 应用的模块化 TypeScript 钱包适配器和组件库。Example 页面是它的在线示例。

它适合用来学习：

- 连接钱包
- 切换或选择网络
- 获取钱包地址
- 构造交易
- 请求用户签名
- 发送交易
- 展示钱包连接状态

## 和套利研究的关系

前期研究不需要急着做交易执行，但后续如果要做 watcher UI、Paper Trading dashboard、手动确认交易 demo 或小型协议交互工具，钱包连接是基础能力。

它可以作为：

- Solana 前端 demo 模板
- Anchor 客户端交互示例的前端入口
- 手动验证交易构造和签名流程的参考

## 安全边界

- 前端 demo 不应该自动交易。
- 默认只连 devnet 或 localhost。
- 不在代码中写死私钥或敏感 RPC key。
- 实盘交易前必须有人手动确认交易内容、账户、金额、滑点和目标程序。

## 下一步

1. 阅读 GitHub README、`APP.md`、`PACKAGES.md` 和 example。
2. 做一个只读钱包连接 demo：连接钱包并显示地址、余额、network。
3. 后续再接入 Solana Explorer / Solscan 链接，方便人工核验地址和交易。
