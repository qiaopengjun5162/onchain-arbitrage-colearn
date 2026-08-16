#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章合规自查（去 AI 味 + 发布前硬约束）
用法: python3 scripts/compliance_check.py <article.md> [--strict]
检查项:
  1. 冒号 0（正文，标题/表格/代码块/引用豁免）
  2. 破折号 0（正文，同上豁免）
  3. 翻案句 0: 不是.{0,12}而是 + 变体（已不在X在Y / 机会在X不在Y / 取决于X不是Y）
  4. 英译式连接词 0: 反映出|体现出|表明了|揭示了|这意味着|由此可见|说明了
  5. digest ≤120 字符（微信硬限）
  6. 自造说法提示（启发式：引号内 4-8 字短语，仅提示不阻断）
退出码: 0=全过, 1=有违规(--strict 时自造说法也计失败)
"""
import re
import sys
import os

COLON_RE = re.compile(r"：")  # 中文冒号必查
COLON_ASCII_RE = re.compile(r":")  # 英文冒号仅查「非时间/币对」上下文
TIME_OR_PAIR_RE = re.compile(r"[A-Za-z0-9\s#]+\d?:\d[A-Za-z0-9\-]*")  # 09:00 / BITGET:RSPYUSDT 豁免
DASH_RE = re.compile(r"[—–]")
FANAN_RE = re.compile(r"不是.{0,12}而是|已不在.{0,8}在|机会在.{0,8}不在|取决于.{0,8}不是")
CONNECT_RE = re.compile(r"反映出|体现出|表明了|揭示了|这意味着|由此可见|说明了")
SELFCOIN_RE = re.compile(r"[\u201c\u201d][^\u201c\u201d]{3,10}[\u201c\u201d]")

def strip_frontmatter(raw: str) -> tuple:
    """返回 (frontmatter_dict_or_None, body)"""
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return None, raw

def clean_body(body: str) -> list:
    """剥离标题行/表格行/代码块/引用行，返回正文行列表"""
    lines = []
    in_code = False
    for l in body.split("\n"):
        s = l.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not s or s.startswith("#") or s.startswith("|") or s.startswith(">"):
            continue
        lines.append(s)
    return lines

def check_article(path: str, strict: bool = False) -> int:
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    fm_text, body = strip_frontmatter(raw)
    lines = clean_body(body)
    text = "\n".join(lines)

    issues = []

    # 1-4: 逐行检查（定位到具体行）
    for l in lines:
        # moonpub fence 语法行（:::callout / label: / :::）整体豁免——排版语法非正文
        if l.strip().startswith((":::", "label:")):
            continue
        # 英文冒号：先剥掉 URL（https:// 等），只查正文里的裸英文冒号
        no_url = re.sub(r"https?://[^\s)\]\"]+", "", l)
        for m in COLON_ASCII_RE.finditer(no_url):
            if not TIME_OR_PAIR_RE.search(no_url):
                issues.append(f"  英文冒号: …{l[max(0, m.start()-15):m.end()+15]}…")
                break
        for name, pat in [("冒号", COLON_RE), ("破折号", DASH_RE),
                          ("翻案句", FANAN_RE), ("连接词", CONNECT_RE)]:
            m = pat.search(l)
            if m:
                issues.append(f"  {name}: …{l[max(0, m.start()-15):m.end()+15]}…")

    # 5: digest 长度
    digest = None
    if fm_text:
        m = re.search(r"^digest:\s*(.+)$", fm_text, re.M)
        if m:
            digest = m.group(1).strip().strip('"\'')
    if digest is not None:
        n = len(digest)
        if n > 120:
            issues.append(f"  digest {n} 字符 > 120 硬限")

    # 6: 自造说法提示（启发式）
    hints = []
    if fm_text:
        for m in SELFCOIN_RE.finditer(text):
            hints.append(m.group(0))

    print(f"=== 合规自查: {os.path.basename(path)} ===")
    print(f"正文行数: {len(lines)} | 字符数: {len(text)}")
    if digest is not None:
        print(f"digest: {len(digest)} 字符 (≤120 {'✅' if len(digest) <= 120 else '❌'})")

    if issues:
        print(f"❌ 违规 {len(issues)} 处:")
        for i in issues:
            print(i)
    else:
        print("✅ 冒号 0 / 破折号 0 / 翻案句 0 / 连接词 0")

    if hints:
        print(f"💡 自造说法候选 {len(hints)} 处（人工复核是否需读者翻译）:")
        for h in hints[:10]:
            print(f"  {h}")
        if strict:
            print("❌ strict 模式: 自造说法视为失败")

    ok = not issues and (not strict or not hints)
    print(f"\n结果: {'✅ PASS' if ok else '❌ FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    strict = "--strict" in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    code = 0
    for p in paths:
        code |= check_article(p, strict)
    sys.exit(code)
