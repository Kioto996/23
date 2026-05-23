#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
寻找15元以下有上涨空间的A股
基于 AKShare 1.18.60 源码参数，修正了 URL 和请求参数
"""

import sys
import json
import time
import random
import requests
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime

# ==================== 配置区域 ====================
MAX_PRICE = 15.0        # 最高股价（元）
MIN_PRICE = 2.0         # 最低股价（元）
MIN_CHANGE_PCT = -5.0   # 最小涨幅（允许小跌）
MAX_CHANGE_PCT = 10.0   # 最大涨幅（%）
MIN_AMOUNT = 0.3         # 最小成交额（亿元）
MAX_ANALYZE = 15         # 最大分析数量
VERBOSE = True
PROXY = "http://127.0.0.1:7897"  # Clash 代理
# ==================================================

# 东方财富是国内网站，不走代理
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
})

def log(msg: str):
    if VERBOSE:
        print(msg)


def fetch_page(url: str, params: Dict, page: int, timeout: int = 15):
    """带重试的页面获取"""
    params = params.copy()
    params["pn"] = str(page)
    for attempt in range(3):
        try:
            r = session.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            if data.get("data") and data["data"].get("diff"):
                return data
        except Exception as e:
            log(f"  第 {attempt+1} 次重试... ({e})")
            time.sleep(1 + attempt)
    return None


def get_all_stocks() -> pd.DataFrame:
    """
    从东方财富API获取所有A股实时行情
    参数完全对照 AKShare 1.18.60 源码
    """
    log("=" * 80)
    log("步骤1: 从东方财富API获取A股实时行情...")
    log("=" * 80)

    url = "http://82.push2.eastmoney.com/api/qt/clist/get"
    base_params = {
        "pn": "1",
        "pz": "100",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f12",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
        "fields": (
            "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,"
            "f12,f13,f14,f15,f16,f17,f18,"
            "f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
        ),
    }

    # 第一页：确定总页数
    log("  获取第一页数据...")
    data = fetch_page(url, base_params, 1)
    if not data or not data.get("data"):
        log("  ❌ 无法获取数据，请检查网络/代理")
        return pd.DataFrame()

    total = data["data"]["total"]
    per_page = len(data["data"]["diff"])
    total_pages = (total + per_page - 1) // per_page
    log(f"  共计 {total} 只股票，{total_pages} 页")

    all_diff = list(data["data"]["diff"])

    import tqdm
    for page in tqdm.tqdm(range(2, total_pages + 1), desc="获取行情", leave=False):
        time.sleep(random.uniform(0.3, 0.8))
        d = fetch_page(url, base_params, page)
        if d and d.get("data"):
            all_diff.extend(d["data"]["diff"])

    df = pd.DataFrame(all_diff)
    # 重命名列（对照 AKShare 源码）
    col_map = {
        "f1": "index", "f2": "最新价", "f3": "涨跌幅", "f4": "涨跌额",
        "f5": "成交量", "f6": "成交额", "f7": "振幅", "f8": "换手率",
        "f9": "市盈率-动态", "f10": "量比", "f12": "代码", "f14": "名称",
        "f15": "最高", "f16": "最低", "f17": "今开", "f18": "昨收",
        "f20": "总市值", "f21": "流通市值", "f22": "涨速",
        "f23": "市净率", "f24": "60日涨跌幅", "f25": "年初至今涨跌幅",
    }
    df = df.rename(columns=col_map)
    numeric_cols = ["最新价", "涨跌幅", "成交量", "成交额", "换手率",
                    "总市值", "流通市值"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    log(f"  ✅ 共获取 {len(df)} 只股票行情")
    return df


def filter_stocks(df: pd.DataFrame) -> pd.DataFrame:
    """按条件筛选股票"""
    log("=" * 80)
    log("步骤2: 筛选符合条件的股票...")
    log("=" * 80)

    if df.empty:
        return df

    mask = (
        (df["最新价"] >= MIN_PRICE) &
        (df["最新价"] <= MAX_PRICE) &
        (df["涨跌幅"] >= MIN_CHANGE_PCT) &
        (df["涨跌幅"] <= MAX_CHANGE_PCT) &
        (df["成交额"] >= MIN_AMOUNT * 1e8)  # 亿元转元
    )
    result = df[mask].copy()
    result = result.sort_values("涨跌幅", ascending=False)
    log(f"  ✅ 筛选出 {len(result)} 只符合条件的股票")
    return result


def calculate_score(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术评分（简化版）"""
    if df.empty:
        return df
    # 这里只做基础评分，详细技术分析可后续扩展
    df = df.copy()
    df["技术评分"] = (
        df["涨跌幅"].clip(lower=0) * 2 +
        df["换手率"].clip(upper=20) * 0.5 +
        df["量比"].clip(upper=5) * 5
    ).round(1)
    return df


def main():
    df = get_all_stocks()
    if df.empty:
        log("❌ 未获取到数据，退出")
        return

    filtered = filter_stocks(df)
    if filtered.empty:
        log("❌ 没有符合条件的股票")
        return

    scored = calculate_score(filtered)
    top = scored.head(MAX_ANALYZE)

    log("=" * 80)
    log(f"TOP {len(top)} 推荐股票：")
    log("=" * 80)
    cols = ["代码", "名称", "最新价", "涨跌幅", "成交额", "换手率", "技术评分"]
    cols = [c for c in cols if c in top.columns]
    print(top[cols].to_string(index=False))

    # 保存结果
    out = f"low_price_stocks_{datetime.now().strftime('%Y%m%d')}.csv"
    top.to_csv(out, index=False, encoding="utf-8-sig")
    log(f"\n✅ 结果已保存到 {out}")


if __name__ == "__main__":
    main()
