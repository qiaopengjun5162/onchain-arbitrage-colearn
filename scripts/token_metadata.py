#!/usr/bin/env python3
"""Solana Token Metadata 读取（Python 版）— 对应 Metaplex JS 的 toMetadataAccount 解法

原理（notes/solana/token-metadata-fetch-method.md）：
- token 的展示元数据（名称/符号/URI）不在 mint 账户里，存在 Metaplex Token Metadata 程序的 PDA
- metadataAccount = PDA("metadata", METAPLEX_PROGRAM_ID, mint_address)
- 三步：推导 PDA → RPC getAccountInfo → 解析 bytes

注意（2026-08-08 实测教训）：
- PDA 推导必须用官方库（solana-py 的 Pubkey.find_program_address / Rust solana-sdk）
- 自实现 base58 + sha256 + on-curve 检查的纯算法推导**结果错误**（bump 检查是 ed25519 曲线点验证，
  不是简单的 h[0] < 0xF0）——自研轮子不可靠，官方实现 bump=255 结果不同

用法：
  python token_metadata.py --mint <MINT_ADDRESS>          # 查单个
  python token_metadata.py --mint ... --raw               # 打印原始字段
  python token_metadata.py --mint-list <file.txt>         # 批量（每行一个 mint）

依赖：hermes venv python3.11 + requests + solana（solana-py，uv 安装）
"""

import argparse
import base64
import json
import os
import struct
import sys
from pathlib import Path

import requests
from solders.pubkey import Pubkey

PROXY = os.environ.get("PROXY", "http://127.0.0.1:7890")
METAPLEX_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"


def get_helius_key() -> str:
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("HELIUS_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return ""


HELIUS_KEY = get_helius_key()
RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}"


def derive_metadata_account(mint: str) -> str:
    """metadataAccount = PDA(seed=["metadata", program_id, mint]) — 官方实现"""
    meta_prog = Pubkey.from_string(METAPLEX_PROGRAM_ID)
    mint_pk = Pubkey.from_string(mint)
    pda, _bump = Pubkey.find_program_address(
        [b"metadata", bytes(meta_prog), bytes(mint_pk)], meta_prog
    )
    return str(pda)


# ---------- Metadata 解析 ----------
def parse_metadata(raw: bytes) -> dict:
    """解析 Metaplex MetadataAccount 数据（简化版，覆盖常用字段）"""
    out = {}
    pos = 0

    def u8():
        nonlocal pos
        v = raw[pos]
        pos += 1
        return v

    def u32():
        nonlocal pos
        v = struct.unpack_from("<I", raw, pos)[0]
        pos += 4
        return v

    def u64():
        nonlocal pos
        v = struct.unpack_from("<Q", raw, pos)[0]
        pos += 8
        return v

    def string():
        nonlocal pos
        n = u32()
        v = raw[pos:pos + n].decode("utf-8", errors="replace")
        pos += n
        return v.split("\x00")[0]   # 去掉固定长度字段的 \x00 填充

    out["key"] = u8()                    # 1 = MetadataV1
    out["update_authority"] = str(Pubkey.from_bytes(raw[pos:pos + 32])); pos += 32
    out["mint"] = str(Pubkey.from_bytes(raw[pos:pos + 32])); pos += 32
    out["name"] = string()
    out["symbol"] = string()
    out["uri"] = string()
    out["seller_fee_basis_points"] = struct.unpack_from("<H", raw, pos)[0]; pos += 2
    return out


def rpc(method, params):
    resp = requests.post(
        RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=20,
        proxies={"https": PROXY} if os.environ.get("NO_PROXY") != "1" else None,
    )
    return resp.json().get("result")


def fetch_metadata(mint: str) -> dict:
    """完整流程：推导 PDA → 读账户 → 解析"""
    meta_addr = derive_metadata_account(mint)
    info = rpc("getAccountInfo", [meta_addr, {"encoding": "base64"}])
    if not info or not info.get("value"):
        return {"mint": mint, "metadata_account": meta_addr, "error": "无 metadata 账户（可能未初始化）"}
    data_b64 = info["value"]["data"][0]
    raw = base64.b64decode(data_b64)
    meta = parse_metadata(raw)
    meta["mint"] = mint
    meta["metadata_account"] = meta_addr
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mint", help="token mint 地址")
    ap.add_argument("--mint-list", help="批量：每行一个 mint 的文本文件")
    ap.add_argument("--raw", action="store_true", help="打印原始字段")
    args = ap.parse_args()

    if not HELIUS_KEY:
        print("ERROR: 未找到 HELIUS_API_KEY", file=sys.stderr)
        return 1

    mints = []
    if args.mint:
        mints.append(args.mint)
    if args.mint_list:
        with open(args.mint_list) as f:
            mints += [l.strip() for l in f if l.strip()]

    if not mints:
        print("用法: python token_metadata.py --mint <MINT>", file=sys.stderr)
        return 1

    for mint in mints:
        meta = fetch_metadata(mint)
        if "error" in meta:
            print(f"{mint[:8]}... {meta['error']}")
            continue
        print(f"\n=== {meta.get('symbol', '?')} ({mint[:12]}...) ===")
        print(f"  name:   {meta.get('name', '?')}")
        print(f"  symbol: {meta.get('symbol', '?')}")
        print(f"  uri:    {meta.get('uri', '?')[:80]}")
        print(f"  fee:    {meta.get('seller_fee_basis_points', 0)} bps")
        print(f"  meta:   {meta.get('metadata_account', '?')[:12]}...")
        if args.raw:
            print(f"  RAW: {json.dumps(meta, ensure_ascii=False)[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
