#!/usr/bin/env python3
"""Polkadot 作业：裸 RPC 查询 Westend 测试网账户余额（不依赖 polkadot.js）。

方法论对照：
- Substrate: state_getStorage(System.Account) + twox128/blake2_128_concat 存储键
- Solana:   getBalance(account)（账户模型原生支持余额查询）

注意：RPC 调用用系统 curl（绕开 Python 3.9 LibreSSL 的 TLSV1_ALERT 坑）。
"""

import hashlib
import json
import subprocess

import base58
import xxhash

WESTEND = "https://westend-rpc.polkadot.io"
ALICE = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"  # Substrate 开发账户


def rpc(method: str, params: list) -> dict:
    """RPC 调用：系统 curl（现代 TLS 栈）"""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    r = subprocess.run(
        ["curl", "-skL", "--max-time", "30", "-H", "Content-Type: application/json",
         "-d", body, WESTEND],
        capture_output=True, text=True, timeout=45,
    )
    return json.loads(r.stdout)


def ss58_to_pubkey(addr: str) -> bytes:
    raw = base58.b58decode(addr)
    # SS58: [前缀(1-2B) | pubkey(32B) | 校验(2B)]；取最后 34 字节的前 32
    return raw[-34:-2]


def twox128(data: bytes) -> bytes:
    return xxhash.xxh64(data, seed=0).digest() + xxhash.xxh64(data, seed=1).digest()


def blake2_128_concat(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=16).digest() + data


def storage_key_system_account(pubkey: bytes) -> str:
    key = twox128(b"System") + twox128(b"Account") + blake2_128_concat(pubkey)
    return "0x" + key.hex()


def main():
    print("=" * 60)
    print("Polkadot 作业 · 裸 RPC 查询 Westend 余额（对照 Solana）")
    print("=" * 60)

    chain = rpc("system_chain", [])
    print(f"\n📡 链: {chain.get('result')}")

    pubkey = ss58_to_pubkey(ALICE)
    print(f"👛 地址: {ALICE}")
    print(f"   pubkey(hex): {pubkey.hex()}")

    key = storage_key_system_account(pubkey)
    r = rpc("state_getStorage", [key])
    val = r.get("result")
    if not val:
        print("   ⚠️ 存储为空（账户不存在，余额 = 0）")
        return

    raw = bytes.fromhex(val[2:])
    print(f"   AccountInfo 原始数据: {len(raw)} bytes")

    # AccountInfo: nonce u32 + consumers u32 + providers u32 + sufficients u32 + AccountData(u128×4)
    nonce = int.from_bytes(raw[0:4], "little")
    consumers = int.from_bytes(raw[4:8], "little")
    providers = int.from_bytes(raw[8:12], "little")
    free = int.from_bytes(raw[16:32], "little")
    reserved = int.from_bytes(raw[32:48], "little")
    misc_frozen = int.from_bytes(raw[48:64], "little")
    fee_frozen = int.from_bytes(raw[64:80], "little")

    print(f"   nonce: {nonce} | consumers: {consumers} | providers: {providers}")
    print(f"   free:     {free} Planck = {free/1e12:.6f} WND")
    print(f"   reserved: {reserved} Planck = {reserved/1e12:.6f} WND")
    print(f"   frozen:   misc={misc_frozen} fee={fee_frozen}")
    print(f"   可动用 (free - fee_frozen): {(free-fee_frozen)/1e12:.6f} WND")
    print("   (1 WND = 1e12 Planck；WND 是 Westend 测试网币，无价值)")


if __name__ == "__main__":
    main()
