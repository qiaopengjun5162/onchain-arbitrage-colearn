//! TUT 价差窗口回测 · Rust 双实现 v2（时间对齐版）
//!
//! 对齐 Python 版 `analyze_tut_windows.py`：
//!   1. 读 binance_5m / bitget_5m CSV → (ts, close) 对
//!   2. ts 归一化到毫秒（秒级自动 ×1000，Python 版同款单位防御）
//!   3. **inner join on ts 对齐**（两边都有记录的时间戳才配对；Python: bn.merge(bg, on="ts")）
//!   4. spread = (close_bn - close_bg) / close_bg，只在交集上算
//!   5. detect_windows：|spread| > th 的连续窗口（cooldown=3 bars）
//!   6. 输出窗口统计 + 对齐诊断（交集/单边条数）
//!
//! 用法：cargo run --release -- <binance_5m.csv> <bitget_5m.csv> [--spread-th 0.02] [--min-window 6]
//! 数据：data/tut_backtest/binance_5m_{d}.csv / bitget_5m_{d}.csv
//! 单事件日跑法：binance_5m_20260808.csv 这类多日文件需先合并（Python 版 concat 后同逻辑）

use std::env;
use std::error::Error;
use std::fs::File;
use std::path::Path;

use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Row {
    #[serde(rename = "open_time", alias = "ts", default)]
    ts: i64,
    #[serde(rename = "open", default)]
    open: f64,
    #[serde(rename = "high", default)]
    high: f64,
    #[serde(rename = "low", default)]
    low: f64,
    #[serde(rename = "close", default)]
    close: f64,
}

/// ts 归一化到毫秒：< 1e12 视为秒级（Python 版 OI 曾踩秒 bug，同款防御）
fn ts_ms(ts: i64) -> i64 {
    if ts < 1_000_000_000_000 {
        ts * 1000
    } else {
        ts
    }
}

/// 读 (ts_ms, close)，按 ts 升序稳定排序（Python: sort_values("ts")）
fn load_ts_closes(path: &str) -> Result<Vec<(i64, f64)>, Box<dyn Error>> {
    let file = File::open(Path::new(path))?;
    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_reader(file);
    let mut rows = Vec::new();
    for rec in rdr.deserialize() {
        let row: Row = rec?;
        rows.push((ts_ms(row.ts), row.close));
    }
    rows.sort_by_key(|r| r.0);
    rows.dedup_by_key(|r| r.0); // Python: drop_duplicates("ts")
    Ok(rows)
}

/// inner join on ts：两序列均升序，双指针归并（Python: merge(on="ts", how=inner)）
fn align(a: &[(i64, f64)], b: &[(i64, f64)]) -> Vec<(i64, f64, f64)> {
    let mut out = Vec::new();
    let (mut i, mut j) = (0, 0);
    while i < a.len() && j < b.len() {
        match a[i].0.cmp(&b[j].0) {
            std::cmp::Ordering::Less => i += 1,
            std::cmp::Ordering::Greater => j += 1,
            std::cmp::Ordering::Equal => {
                out.push((a[i].0, a[i].1, b[j].1));
                i += 1;
                j += 1;
            }
        }
    }
    out
}

/// |spread| > th 的连续窗口（cooldown_bars 根 bar 内的分离合并为一个窗口）。
fn detect_windows(spread: &[f64], th: f64, cooldown_bars: usize) -> Vec<(usize, usize)> {
    let mut windows = Vec::new();
    let mut i = 0;
    let n = spread.len();
    while i < n {
        if spread[i].abs() > th {
            let start = i;
            let mut last = i;
            let mut j = i + 1;
            while j < n {
                if spread[j].abs() > th {
                    last = j;
                } else if j > last + cooldown_bars {
                    break;
                }
                j += 1;
            }
            windows.push((start, last));
            i = j;
        } else {
            i += 1;
        }
    }
    windows
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("用法: tut_window_rs <binance_5m.csv> <bitget_5m.csv> [--spread-th 0.02] [--min-window 6]");
        std::process::exit(1);
    }
    let bn_path = &args[1];
    let bg_path = &args[2];
    let mut th = 0.02;
    let mut min_window = 6;
    let mut i = 3;
    while i < args.len() {
        match args[i].as_str() {
            "--spread-th" => {
                i += 1;
                th = args[i].parse()?;
            }
            "--min-window" => {
                i += 1;
                min_window = args[i].parse()?;
            }
            _ => {}
        }
        i += 1;
    }

    let bn = load_ts_closes(bn_path)?;
    let bg = load_ts_closes(bg_path)?;

    // 时间对齐（v2 核心）：inner join on ts，而非按 index 硬对齐
    let aligned = align(&bn, &bg);
    if aligned.is_empty() {
        eprintln!("❌ 两序列无共同时间戳（ts 单位/时区不一致？）。bn={} bg={}",
                  bn.len(), bg.len());
        std::process::exit(2);
    }

    // 诊断：单边条数（时间戳未对齐的 bar）
    let mut bn_only = 0;
    let mut bg_only = 0;
    {
        let (mut i, mut j) = (0, 0);
        while i < bn.len() && j < bg.len() {
            match bn[i].0.cmp(&bg[j].0) {
                std::cmp::Ordering::Less => { bn_only += 1; i += 1; }
                std::cmp::Ordering::Greater => { bg_only += 1; j += 1; }
                std::cmp::Ordering::Equal => { i += 1; j += 1; }
            }
        }
        bn_only += bn.len() - i;
        bg_only += bg.len() - j;
    }

    let spread: Vec<f64> = aligned
        .iter()
        .map(|(_, cb, cg)| if *cg != 0.0 { (cb - cg) / cg } else { 0.0 })
        .collect();

    let windows = detect_windows(&spread, th, 3);
    let valid: Vec<(usize, usize)> = windows
        .iter()
        .filter(|(s, e)| e >= s && (e - s + 1) >= min_window)
        .copied()
        .collect();

    println!("=== TUT 价差窗口（Rust 双实现 v2 · ts 对齐）===");
    println!("bn bars: {} | bg bars: {} | 对齐交集: {} | bn 单边: {} | bg 单边: {}",
             bn.len(), bg.len(), aligned.len(), bn_only, bg_only);
    println!("spread 阈值: {:.1}% | 最短窗口: {} bars", th * 100.0, min_window);
    println!("粗窗口数: {} | 合格窗口(≥{} bars): {}", windows.len(), min_window, valid.len());

    if !valid.is_empty() {
        let lens: Vec<usize> = valid.iter().map(|(s, e)| e - s + 1).collect();
        let max_len = lens.iter().max().unwrap();
        let avg_len = lens.iter().sum::<usize>() as f64 / lens.len() as f64;
        let up = valid.iter().filter(|(s, e)| spread[*s] > 0.0).count();
        println!("最长窗口: {} bars | 平均窗口: {:.1} bars | 正向(bn>bg): {} / 反向: {}",
                 max_len, avg_len, up, valid.len() - up);

        let (max_idx, max_abs) = spread
            .iter()
            .enumerate()
            .map(|(k, v)| (k, v.abs()))
            .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap())
            .unwrap();
        println!("最大 |spread|: {:.2}% @ bar {}（{}）", max_abs * 100.0, max_idx,
                 if spread[max_idx] > 0.0 { "bn 高于 bg" } else { "bg 高于 bn" });

        println!("\n窗口明细（前 10）:");
        for (k, (s, e)) in valid.iter().take(10).enumerate() {
            let dir = if spread[*s] > 0.0 { "bn高" } else { "bg高" };
            println!("  #{} bars {}-{} ({} bars) 方向:{}", k + 1, s, e, e - s + 1, dir);
        }
    } else {
        println!("无合格窗口（阈值内无持续价差）");
    }

    Ok(())
}
