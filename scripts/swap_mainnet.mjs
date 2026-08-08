#!/usr/bin/env node
/**
 * D3 主线：mainnet 真实小额 swap（0.01 SOL → USDC）
 * 流程：quote → build → 组装 v0 交易 → 签名 → 发送 → 确认 → Solscan 链接
 *
 * 安全：私钥从 ~/.config/solana/id.json 本地读取签名，不打印、不传输。
 * 代理：api.jup.ag 被墙，走 Clash 代理 127.0.0.1:7890（quote/build 请求）。
 * RPC：mainnet Helius（发送用）。
 */
import {
  Connection, Keypair, PublicKey, VersionedTransaction,
  TransactionMessage, AddressLookupTableAccount,
} from "@solana/web3.js";
import fs from "fs";
import os from "os";
import path from "path";
import { pathToFileURL } from "url";

const PROXY = "http://127.0.0.1:7890";
const API = "https://api.jup.ag/swap/v2";
const HELIUS_KEY = process.env.HELIUS_API_KEY || "";
if (!HELIUS_KEY) {
  console.error("ERROR: 请设置 HELIUS_API_KEY 环境变量（export HELIUS_API_KEY=...）");
  process.exit(1);
}
const RPC = `https://mainnet.helius-rpc.com/?api-key=${HELIUS_KEY}`;
const SOL = "So11111111111111111111111111111111111111112";
const USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const AMOUNT = 10_000_000; // 0.01 SOL
const SLIPPAGE_BPS = 100;  // 1%

// ---- 默认 dry-run：只到签名不广播。显式 --send 才花主网 Gas ----
const SEND = process.argv.includes("--send");

// ---- proxy fetch ----
const fetchProxy = async (url) => {
  const res = await fetch(url, { signal: AbortSignal.timeout(20000), dispatcher: undefined });
  // node 24 fetch 不支持 proxy dispatcher 直接参数，用环境变量方式：这里通过 https-proxy-agent 太重，
  // 直接改用 undici ProxyAgent if available, 否则回退。这里简单方案：child curl via proxy。
  return res;
};

const fetchViaProxy = async (url) => {
  const { execSync } = await import("child_process");
  const out = execSync(`curl -s --max-time 20 -x ${PROXY} "${url}"`, { maxBuffer: 10 * 1024 * 1024 });
  return JSON.parse(out.toString());
};

// ---- 1. quote ----
const quoteParams = new URLSearchParams({
  inputMint: SOL, outputMint: USDC, amount: String(AMOUNT), slippageBps: String(SLIPPAGE_BPS),
});
const quote = await fetchViaProxy(`${API}/quote?${quoteParams}`);
if (quote.error) { console.error("quote error:", quote.error); process.exit(1); }
console.log("✅ quote:", (AMOUNT / 1e9).toFixed(3), "SOL →", (Number(quote.outAmount) / 1e6).toFixed(2), "USDC");
console.log("   minOut:", (Number(quote.otherAmountThreshold) / 1e6).toFixed(2), "USDC | impact:", quote.priceImpactPct, "%");

// ---- 2. build ----
const wallet = Keypair.fromSecretKey(
  Uint8Array.from(JSON.parse(fs.readFileSync(path.join(os.homedir(), ".config/solana/id.json"), "utf-8")))
);
const buildParams = new URLSearchParams({
  inputMint: SOL, outputMint: USDC, amount: String(AMOUNT),
  taker: wallet.publicKey.toBase58(), slippageBps: String(SLIPPAGE_BPS),
});
const build = await fetchViaProxy(`${API}/build?${buildParams}`);
if (build.error) { console.error("build error:", build.error); process.exit(1); }
console.log("✅ build: route =", build.routePlan.map(r => r.swapInfo.label).join(" → "));
console.log("   setup:", build.setupInstructions.length, "| swap:", !!build.swapInstruction, "| ALTs:", Object.keys(build.addressesByLookupTableAddress || {}).length);

// ---- 3. assemble v0 tx ----
const connection = new Connection(RPC, "confirmed");
const payer = wallet.publicKey;
const ixs = [
  ...build.computeBudgetInstructions,
  ...build.setupInstructions,
  build.swapInstruction,
  ...(build.cleanupInstruction ? [build.cleanupInstruction] : []),
].map(ix => ({
  programId: new PublicKey(ix.programId),
  keys: ix.accounts.map(a => ({
    pubkey: new PublicKey(a.pubkey), isSigner: a.isSigner, isWritable: a.isWritable,
  })),
  data: Buffer.from(ix.data, "base64"),
}));

// lookup tables
const altAddrs = Object.keys(build.addressesByLookupTableAddress || {});
const altAccounts = [];
for (const addr of altAddrs) {
  const info = await connection.getAddressLookupTable(new PublicKey(addr)).catch(() => null);
  if (info?.value) altAccounts.push(info.value);
}
const bh = await connection.getLatestBlockhash("finalized");
const msg = new TransactionMessage({
  payerKey: payer, recentBlockhash: bh.blockhash, instructions: ixs,
}).compileToV0Message(altAccounts);
const tx = new VersionedTransaction(msg);
tx.sign([wallet]);

// ---- 4. send（仅 --send 时广播，否则 dry-run 结束）----
if (!SEND) {
  console.log("⏸️ dry-run 模式：已到签名完成，未广播（主网 0 花费）");
  console.log("   想真发交易：node swap_mainnet.mjs --send");
  process.exit(0);
}
console.log("🚀 sending 0.01 SOL → USDC on mainnet ...");
const sig = await connection.sendTransaction(tx, { skipPreflight: false, preflightCommitment: "confirmed" });
console.log("   tx:", sig);
console.log("   confirming ...");
const conf = await connection.confirmTransaction({ signature: sig, ...bh }, "confirmed");
console.log("   confirmed:", conf.value.err === null ? "✅ SUCCESS" : `❌ ${JSON.stringify(conf.value.err)}`);

// ---- 5. solscan ----
console.log(`\n🔗 Solscan: https://solscan.io/tx/${sig}`);
