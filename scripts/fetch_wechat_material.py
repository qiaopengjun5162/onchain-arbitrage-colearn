#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_wechat_material.py — 公众号文章素材抓取

用法:
  # 直连抓单篇（免登录，推荐，不经过第三方服务）
  python3 fetch_wechat_material.py --url "https://mp.weixin.qq.com/s/xxxxx" [-o data/wechat_material]

  # 搜公众号（需 down.mptext.top 登录 cookie）
  python3 fetch_wechat_material.py --search "套利" --size 5 --cookie "..."

  # 拉某号文章列表（需 cookie）
  python3 fetch_wechat_material.py --list <fakeid> --begin 0 --size 5 --cookie "..."

依赖: requests + bs4（hermes venv 已装）
安全:
  - 直连模式不经过任何第三方，抓的就是 mp.weixin.qq.com 公开页面。
  - 代理模式（search/list）把请求发到 down.mptext.top，该站持有你的微信会话
    (uin/key/pass_ticket)，风险自担；cookie 只从本地读，不进仓库。
  - cookie 读取顺序: --cookie 参数 > 环境变量 MPTEXT_COOKIE > ~/.hermes/mptext_cookie
"""

import argparse
import html as html_mod
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------- 直连抓单篇 ----------

def fetch_article(url: str, outdir: str) -> dict:
    """抓取单篇公众号文章 → markdown + 图片，返回元信息。"""
    log(f"抓取: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    html = resp.text
    if len(html) < 2000:
        raise RuntimeError("页面过小，疑似被风控或文章已删除")

    soup = BeautifulSoup(html, "html.parser")

    # 元信息（直接在原始 HTML 全文上正则，页面变量常在 2MB+ 处）
    title = _grab(html, r"msg_title\s*=\s*['\"]([^'\"]+)['\"]") or (
        soup.find("meta", property="og:title") or {}
    ).get("content", "").strip()
    title = html_mod.unescape(title) or "untitled"
    nickname = (
        _grab(html, r"var\s+nickname\s*=\s*['\"]([^'\"]+)['\"]")
        or (soup.find("meta", property="og:article:author") or {}).get("content", "")
        or (soup.find("meta", attrs={"name": "author"}) or {}).get("content", "")
        or ""
    ).strip()
    if not isinstance(nickname, str):
        nickname = str(nickname)
    ct = _grab(html, r"var\s+ct\s*=\s*['\"](\d+)['\"]")
    pub_time = datetime.fromtimestamp(int(ct)).strftime("%Y-%m-%d %H:%M") if ct else ""

    # 正文
    content = soup.find(id="js_content")
    if content is None:
        raise RuntimeError("未找到正文 (js_content)，文章可能已被删除或违规")

    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", title).strip("-")[:60]
    date_prefix = datetime.now().strftime("%Y%m%d")
    art_dir = os.path.join(outdir, f"{date_prefix}-{slug}")
    asset_dir = os.path.join(art_dir, "assets")
    os.makedirs(asset_dir, exist_ok=True)

    img_map = {}  # orig src -> relative path
    _collect_images(content, img_map, asset_dir)

    md_body = _blocks_to_md(content, img_map)

    frontmatter = (
        "---\n"
        f"title: {title}\n"
        f"author: {nickname}\n"
        f"publish_time: {pub_time}\n"
        f"source_url: {url}\n"
        f"fetched_at: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        "---\n\n"
    )
    md = frontmatter + md_body + "\n"

    md_path = os.path.join(art_dir, "article.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    n_imgs = len(img_map)
    log(f"完成: {md_path}  (图片 {n_imgs} 张)")
    return {"title": title, "author": nickname, "publish_time": pub_time,
            "path": md_path, "images": n_imgs}


def _grab(html_text, pattern):
    m = re.search(pattern, html_text)
    return m.group(1) if m else None


def _collect_images(node, img_map, asset_dir):
    for img in node.find_all("img"):
        src = img.get("data-src") or img.get("src")
        if not src:
            continue
        if src in img_map:
            img["data-hermes-done"] = img_map[src]
            continue
        try:
            r = requests.get(src, headers=HEADERS, timeout=20)
            r.raise_for_status()
            ext = _sniff_ext(r.content) or _ext_from_url(src) or "jpg"
            fname = f"img{len(img_map)+1:03d}.{ext}"
            fpath = os.path.join(asset_dir, fname)
            with open(fpath, "wb") as f:
                f.write(r.content)
            rel = f"assets/{fname}"
            img_map[src] = rel
            img["data-hermes-done"] = rel
        except Exception as e:
            log(f"图片失败 {src[:60]}: {e}")
            img_map[src] = src  # 保留原链


def _sniff_ext(data):
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _ext_from_url(src):
    path = urllib.parse.urlparse(src).path
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    return ext if ext in {"jpg", "jpeg", "png", "gif", "webp"} else None


def _blocks_to_md(node, img_map):
    """把正文节点转成 markdown。"""
    parts = []
    for child in node.children:
        text = _node_to_md(child, img_map).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts) + "\n"


def _node_to_md(node, img_map):
    if isinstance(node, str):
        t = html_mod.unescape(node).strip()
        return t + ("\n" if t.endswith(("。", "！", "？", ":", "：")) and len(t) > 12 else "")

    name = getattr(node, "name", None)
    if name is None:
        return ""

    if name in ("script", "style", "iframe"):
        return ""
    if name == "br":
        return "\n"
    if name == "hr":
        return "\n---\n"
    if name in ("p", "div", "section"):
        inner = "".join(_node_to_md(c, img_map) for c in node.children)
        inner = re.sub(r"\n{2,}", "\n", inner).strip()
        return inner + "\n\n"
    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        return "#" * level + " " + _inline(node, img_map) + "\n\n"
    if name == "blockquote":
        inner = _node_to_md_plain(node, img_map).strip()
        return "> " + inner.replace("\n", "\n> ") + "\n\n"
    if name == "ul":
        return "\n".join(f"- {_node_to_md(li, img_map).strip()}" for li in node.find_all("li", recursive=False)) + "\n\n"
    if name == "ol":
        return "\n".join(f"{i}. {_node_to_md(li, img_map).strip()}" for i, li in enumerate(node.find_all("li", recursive=False), 1)) + "\n\n"
    if name == "li":
        return _inline(node, img_map)
    if name == "pre":
        code = node.get_text().strip()
        return f"```\n{code}\n```\n\n"
    if name == "code":
        return f"`{node.get_text().strip()}`"
    if name == "a":
        href = node.get("href", "")
        return f"[{_inline(node, img_map).strip()}]({href})"
    if name == "img":
        src = node.get("data-src") or node.get("src") or ""
        rel = img_map.get(src, src)
        return f"![]({rel})"
    # strong/b/em/i/span/others: inline passthrough
    return _inline(node, img_map)


def _node_to_md_plain(node, img_map):
    parts = []
    for c in node.children:
        parts.append(_node_to_md(c, img_map))
    return "".join(parts)


def _inline(node, img_map):
    """inline 级处理：strong/em/a/img 保留，其余取文本。"""
    if isinstance(node, str):
        return html_mod.unescape(node)
    name = getattr(node, "name", None)
    if name is None:
        return ""
    if name in ("strong", "b"):
        return f"**{_inline(node, img_map).strip()}**"
    if name in ("em", "i"):
        return f"*{_inline(node, img_map).strip()}*"
    if name == "br":
        return "\n"
    if name == "a":
        return f"[{_inline(node, img_map).strip()}]({node.get('href','')})"
    if name == "img":
        src = node.get("data-src") or node.get("src") or ""
        return f"![]({img_map.get(src, src)})"
    if name in ("p", "div", "section", "li"):
        return _inline_join(node, img_map)
    return node.get_text() if hasattr(node, "get_text") else ""


def _inline_join(node, img_map):
    return "".join(_inline(c, img_map) for c in node.children)


# ---------- 代理模式（down.mptext.top，需登录 cookie） ----------

def _cookie_arg(cookie: str) -> str:
    if cookie:
        return cookie
    env = os.environ.get("MPTEXT_COOKIE")
    if env:
        return env
    p = os.path.expanduser("~/.hermes/mptext_cookie")
    if os.path.exists(p):
        return open(p).read().strip()
    return ""


def proxy_get(path: str, params: dict, cookie: str):
    ck = _cookie_arg(cookie)
    if not ck:
        raise RuntimeError(
            "代理模式需要 cookie：浏览器登录 down.mptext.top 后，把 Cookie 复制到 "
            "~/.hermes/mptext_cookie（或 --cookie / MPTEXT_COOKIE）。"
        )
    r = requests.get(
        f"https://down.mptext.top{path}",
        params=params,
        headers={**HEADERS, "Cookie": ck,
                 "Referer": "https://down.mptext.top/",
                 "Origin": "https://down.mptext.top"},
        timeout=20,
    )
    return r.json()


def search_accounts(keyword: str, size: int, cookie: str):
    data = proxy_get("/api/web/mp/searchbiz", {"begin": 0, "size": size, "keyword": keyword}, cookie)
    br = data.get("base_resp", {})
    if br.get("ret") != 0:
        raise RuntimeError(f"searchbiz: {br.get('ret')} {br.get('err_msg')}")
    for acc in data.get("list", []):
        print(f"{acc.get('nickname')} | fakeid={acc.get('fakeid')}")
    print(f"total={data.get('total')}")


def list_articles(fakeid: str, begin: int, size: int, keyword: str, cookie: str):
    data = proxy_get("/api/web/mp/appmsgpublish",
                     {"id": fakeid, "begin": begin, "size": size, "keyword": keyword}, cookie)
    br = data.get("base_resp", {})
    if br.get("ret") != 0:
        raise RuntimeError(f"appmsgpublish: {br.get('ret')} {br.get('err_msg')}")
    pub = data.get("publish_page", "{}")
    import json as _json
    page = _json.loads(pub)
    for item in page.get("publish_list", []):
        info = item.get("publish_info", {})
        title = info.get("title", "")
        url = info.get("url", "")
        ts = info.get("update_time", "")
        print(f"{datetime.fromtimestamp(ts).strftime('%m-%d')} | {title} | {url}")


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="公众号文章素材抓取")
    ap.add_argument("--url", help="文章 URL (mp.weixin.qq.com/s/...)，直连模式")
    ap.add_argument("-o", "--outdir", default="data/wechat_material", help="输出目录")
    ap.add_argument("--search", help="搜公众号关键词（代理模式，需 cookie）")
    ap.add_argument("--list", help="拉某号文章列表，参数为 fakeid（代理模式）")
    ap.add_argument("--begin", type=int, default=0)
    ap.add_argument("--size", type=int, default=10)
    ap.add_argument("--keyword", default="", help="列表内关键词过滤")
    ap.add_argument("--cookie", default="", help="down.mptext.top Cookie（或用环境变量/配置文件）")
    args = ap.parse_args()

    if args.url:
        try:
            fetch_article(args.url, os.path.abspath(args.outdir))
        except Exception as e:
            log(f"失败: {e}")
            sys.exit(1)
    elif args.search:
        try:
            search_accounts(args.search, args.size, args.cookie)
        except Exception as e:
            log(f"失败: {e}")
            sys.exit(1)
    elif args.list:
        try:
            list_articles(args.list, args.begin, args.size, args.keyword, args.cookie)
        except Exception as e:
            log(f"失败: {e}")
            sys.exit(1)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
