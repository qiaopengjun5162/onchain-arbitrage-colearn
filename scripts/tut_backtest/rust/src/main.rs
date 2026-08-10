//! TUT 价差窗口回测 · Rust 双实现（骨架 + 核心逻辑）
//!
//! 对齐 Python 版 `analyze_tut_windows.py`：
//!   1. 读 binance_5m / bitget_5m CSV → 算 spread = (close_bn - close_bg) / close_bg
//!   2. detect_windows：|spread| > th 的连续窗口（cooldown=3 bars）
//!   3. 输出窗口统计（数量 / 最长 / 平均 / 方向分布）
//!
//! 用法：cargo run --release -- <binance_5m.csv> <bitget_5m.csv> [--spread-th 0.02]
//! 数据：data/tut_backtest/binance_5m_{d}.csv / bitget_5m_{d}.csv

use std::env;
use std::error::Error;
use std::fs::File;
use std::path::Path;

use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Row {
    // kline 行：open, high, low, close, volume, ts(或 open_time)
    #[serde(rename = "open_time", alias = "ts", default)]
    open_time: String,
    #[serde(rename = "open", default)]
    open: f64,
    #[serde(rename = "high", default)]
    high: f64,
    #[serde(rename = "low", default)]
    low: f64,
    #[serde(rename = "close", default)]
    close: f64,
}

fn load_closes(path: &str) -> Result<Vec<f64>, Box<dyn Error>> {
    let file = File::open(Path::new(path))?;
    let mut rdr = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_reader(file);
    let mut closes = Vec::new();
    for rec in rdr.deserialize() {
        let row: Row = rec?;
        closes.push(row.close);
    }
    Ok(closes)
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

    let bn = load_closes(bn_path)?;
    let bg = load_closes(bg_path)?;
    if bn.len() != bg.len() {
        eprintln!("⚠️ 长度不一致: bn={} bg={}（取 min）", bn.len(), bg.len());
    }
    let n = bn.len().min(bg.len());

    // spread = (bn - bg) / bg
    let spread: Vec<f64> = (0..n)
        .map(|k| if bg[k] != 0.0 { (bn[k] - bg[k]) / bg[k] } else { 0.0 })
        .collect();

    let windows = detect_windows(&spread, th, 3);
    let valid: Vec<(usize, usize)> = windows
        .iter()
        .filter(|(s, e)| e >= s && (e - s + 1) >= min_window)
        .copied()
        .collect();

    println!("=== TUT 价差窗口（Rust 双实现）===");
    println!("bars: {} | spread 阈值: {:.1}% | 最短窗口: {} bars", n, th * 100.0, min_window);
    println!("粗窗口数: {} | 合格窗口(≥{} bars): {}", windows.len(), min_window, valid.len());

    if !valid.is_empty() {
        let lens: Vec<usize> = valid.iter().map(|(s, e)| e - s + 1).collect();
        let max_len = lens.iter().max().unwrap();
        let avg_len = lens.iter().sum::<usize>() as f64 / lens.len() as f64;
        let up = valid.iter().filter(|(s, e)| spread[*s] > 0.0).count();
        println!("最长窗口: {} bars | 平均窗口: {:.1} bars | 正向(bn>bg): {} / 反向: {}",
                 max_len, avg_len, up, valid.len() - up);

        // 最大价差与时刻（最极端窗口——插针痕迹）
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
