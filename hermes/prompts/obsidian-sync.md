# Prompt: 同步到 Obsidian

你在帮我把链上套利共学的工作记录整理成 Obsidian 长期知识库笔记。

输入：

```text
<粘贴每日打卡、研究笔记、资料链接或草稿>
```

任务：

1. 判断这份内容应该进入哪类笔记：daily、market、strategy、tool、source、review、draft。
2. 生成 Obsidian frontmatter。
3. 提取可复用观点，而不是机械复制全文。
4. 补充建议双链，使用 `[[概念名]]` 格式。
5. 明确哪些内容只是猜测，哪些有证据。
6. 给出一个下一步验证动作。
7. 删除敏感交易细节、账户规模、密钥、可被滥用的执行细节。

输出格式：

```markdown
---
title:
date:
type:
status:
tags:
source:
related:
---

## 问题

## 结论

## 为什么重要

## 证据

## 假设

## 风险

## 下一步
```
