# -*- coding: utf-8 -*-
"""A股多维度数据采集 - 带文件日志"""
import akshare as ak
import pandas as pd
import json
import os
import sys
from datetime import datetime

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, 'screening_log.txt')

def log(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg, flush=True)

def safe_float(val, default=0.0):
    try:
        if pd.isna(val) or val in ('-', '', None):
            return default
        return float(val)
    except:
        return default

# 清空日志
open(LOG_FILE, 'w').close()

log(f"START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# === 1. 涨幅排行 ===
log("\n[1] Getting top gainers...")
try:
    df = ak.stock_zh_a_spot_em()
    log(f"  Total stocks: {len(df)}")
    log(f"  Columns: {list(df.columns)[:10]}")

    df = df[~df['名称'].str.contains('ST|停牌|退', na=False)]
    df = df[df['涨跌幅'] > 1.0]
    df = df[df['涨跌幅'] < 9.5]
    df = df[df['最新价'] > 2]
    df = df.sort_values('涨跌幅', ascending=False).head(60)

    result = []
    for _, row in df.iterrows():
        result.append({
            'code': str(row['代码']).zfill(6),
            'name': row['名称'],
            'price': safe_float(row['最新价']),
            'change_pct': safe_float(row['涨跌幅']),
            'volume_ratio': safe_float(row.get('量比', 0)),
            'turnover_rate': safe_float(row.get('换手率', 0)),
            'market_cap': safe_float(row.get('总市值', 0)) / 1e8,
            'high': safe_float(row.get('最高', 0)),
            'low': safe_float(row.get('最低', 0)),
        })

    with open(os.path.join(OUT_DIR, 'top_gainers.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"  [OK] {len(result)} stocks saved")
    for r in result[:15]:
        log(f"    {r['code']} {r['name']} +{r['change_pct']}% vol_ratio:{r['volume_ratio']} turnover:{r['turnover_rate']}%")
except Exception as e:
    log(f"  [ERR] {type(e).__name__}: {e}")

# === 2. 主力资金流入排行 ===
log("\n[2] Getting main fund flow...")
try:
    df = ak.stock_individual_fund_flow_rank(indicator="今日")
    df = df.sort_values('主力净流入-净额', ascending=False)
    df = df[~df['名称'].str.contains('ST', na=False)]
    df = df[df['涨跌幅'] < 9.5]

    result = []
    for _, row in df.head(40).iterrows():
        result.append({
            'code': str(row.get('代码', '')).zfill(6),
            'name': row.get('名称', ''),
            'change_pct': safe_float(row.get('涨跌幅', 0)),
            'main_net_inflow': safe_float(row.get('主力净流入-净额', 0)) / 1e4,
            'main_pct': safe_float(row.get('主力净流入-净占比', 0)),
        })

    with open(os.path.join(OUT_DIR, 'main_fund_flow.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"  [OK] {len(result)} stocks saved")
    for r in result[:10]:
        log(f"    {r['code']} {r['name']} +{r['change_pct']}% main_inflow:{r['main_net_inflow']:.0f}w pct:{r['main_pct']:.1f}%")
except Exception as e:
    log(f"  [ERR] {type(e).__name__}: {e}")

# === 3. 行业板块 ===
log("\n[3] Getting industry sectors...")
try:
    df = ak.stock_board_industry_name_em()
    if '涨跌幅' in df.columns:
        df = df.sort_values('涨跌幅', ascending=False)

    result = []
    for _, row in df.head(20).iterrows():
        result.append({
            'name': row.get('板块名称', ''),
            'change_pct': safe_float(row.get('涨跌幅', 0)),
            'up_count': int(safe_float(row.get('上涨家数', 0))),
            'down_count': int(safe_float(row.get('下跌家数', 0))),
            'lead_stock': row.get('领涨股票', ''),
        })

    with open(os.path.join(OUT_DIR, 'sector_hotspots.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"  [OK] {len(result)} sectors saved")
    for r in result[:10]:
        log(f"    {r['name']} +{r['change_pct']}% up:{r['up_count']} down:{r['down_count']} lead:{r['lead_stock']}")
except Exception as e:
    log(f"  [ERR] {type(e).__name__}: {e}")

# === 4. 概念板块 ===
log("\n[4] Getting concept sectors...")
try:
    df = ak.stock_board_concept_name_em()
    if '涨跌幅' in df.columns:
        df = df.sort_values('涨跌幅', ascending=False)

    result = []
    for _, row in df.head(20).iterrows():
        result.append({
            'name': row.get('板块名称', ''),
            'change_pct': safe_float(row.get('涨跌幅', 0)),
            'up_count': int(safe_float(row.get('上涨家数', 0))),
            'lead_stock': row.get('领涨股票', ''),
        })

    with open(os.path.join(OUT_DIR, 'concept_hotspots.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"  [OK] {len(result)} concepts saved")
    for r in result[:10]:
        log(f"    {r['name']} +{r['change_pct']}% up:{r['up_count']} lead:{r['lead_stock']}")
except Exception as e:
    log(f"  [ERR] {type(e).__name__}: {e}")

log(f"\nDONE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
