#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
15元左右A股筛选 - 使用腾讯财经API（国内直连，无需代理）
数据源：腾讯财经 qt.gtimg.cn
"""

import requests
import re
import pandas as pd
import time
from datetime import datetime

# ==================== 配置 ====================
TARGET_PRICE = 15.0      # 目标价位（元）
PRICE_TOLERANCE = 5.0     # 价格容忍区间（±元）
MIN_PRICE = 10.0
MAX_PRICE = 20.0
MIN_AMOUNT = 0.5          # 最小成交额（亿元）
MAX_PICK = 10              # 最多返回几只
# ================================================

def get_all_stock_codes():
    """获取沪深A股代码列表（通过腾讯财经）"""
    # 使用腾讯财经的板块接口获取沪深A股列表
    # 沪市主板
    sh_url = "http://qt.gtimg.cn/q=s_sh000001"
    # 实际上我们需要通过另一个方式获取全量代码
    # 这里使用AKShare的不同数据源（新浪财经）
    try:
        import akshare as ak
        # 尝试用新浪数据源
        df = ak.stock_info_a_code_name()
        print(f"获取到 {len(df)} 只股票代码")
        return df
    except:
        return pd.DataFrame()


def fetch_realtime_quote(stock_code: str) -> dict:
    """
    获取单只股票实时行情（腾讯财经API）
    腾讯API格式：v_sh600001="1~股票名~代码~价格~涨跌~涨跌幅~..."
    """
    # 判断市场前缀
    code = stock_code.strip()
    if code.startswith("6"):
        prefix = "sh"
    elif code.startswith("0") or code.startswith("3"):
        prefix = "sz"
    else:
        return None

    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        r = requests.get(url, timeout=5)
        r.encoding = "gbk"
        text = r.text.strip()
        # 解析：v_sh600001="1~贵州茅台~600001~...
        m = re.search(r'"(.+)"', text)
        if not m:
            return None
        fields = m.group(1).split("~")
        if len(fields) < 37:
            return None
        return {
            "代码": code,
            "名称": fields[1],
            "最新价": float(fields[3]) if fields[3] else 0,
            "涨跌幅": float(fields[5]) if fields[5] else 0,
            "成交量": float(fields[6]) if fields[6] else 0,   # 手
            "成交额": float(fields[7]) if fields[7] else 0,   # 万元
            "换手率": float(fields[9]) if fields[9] else 0,
            "市盈率": float(fields[15]) if fields[15] else 0,
            "流通市值": float(fields[17]) if fields[17] else 0, # 亿元
            "总市值": float(fields[18]) if fields[18] else 0,    # 亿元
            "涨停价": float(fields[30]) if fields[30] else 0,
            "跌停价": float(fields[31]) if fields[31] else 0,
        }
    except Exception as e:
        return None


def batch_fetch(codes: list, batch_size=50):
    """批量获取行情（腾讯支持批量查询）"""
    results = []
    total = len(codes)
    
    for i in range(0, total, batch_size):
        batch = codes[i:i+batch_size]
        # 构造批量查询字符串
        q_str = ",".join(
            ("sh" if c.startswith("6") else "sz") + c 
            for c in batch
        )
        url = f"http://qt.gtimg.cn/q={q_str}"
        try:
            r = requests.get(url, timeout=10)
            r.encoding = "gbk"
            for line in r.text.strip().split("\n"):
                m = re.search(r'q "(.*)"', line)
                if not m:
                    continue
                fields = m.group(1).split("~")
                if len(fields) < 17:
                    continue
                try:
                    results.append({
                        "代码": fields[2],
                        "名称": fields[1],
                        "最新价": float(fields[3]) if fields[3] else 0,
                        "涨跌幅": float(fields[5]) if fields[5] else 0,
                        "成交量": float(fields[6]) if fields[6] else 0,
                        "成交额": float(fields[7]) if fields[7] else 0,
                        "换手率": float(fields[9]) if fields[9] else 0,
                        "市盈率": float(fields[15]) if fields[15] else 0,
                        "流通市值": float(fields[17]) if fields[17] else 0,
                        "总市值": float(fields[18]) if fields[18] else 0,
                    })
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            print(f"  批次 {i//batch_size+1} 失败: {e}")
        time.sleep(0.2)
        if (i // batch_size) % 10 == 0:
            print(f"  已处理 {min(i+batch_size, total)}/{total} ...")
    
    return results


def analyze_hot_sectors(df: pd.DataFrame) -> list:
    """分析热门板块（通过涨幅排名靠前的股票所属板块）"""
    # 简化版：按涨跌幅取前50，认为它们是热门股
    top = df.sort_values("涨跌幅", ascending=False).head(50)
    return top["名称"].tolist()


def score_stock(row) -> float:
    """综合评分"""
    score = 0.0
    # 价格接近15元加分
    price = row["最新价"]
    price_dist = abs(price - 15.0)
    if price_dist <= 3:
        score += (3 - price_dist) * 5  # 越接近15分越高
    
    # 涨跌幅合理（0~5% 最佳）
    chg = row["涨跌幅"]
    if 0 <= chg <= 5:
        score += chg * 2
    elif chg < 0:
        score += chg * 0.5  # 小跌也可以
    
    # 换手率（太高可能是炒作，太低不活跃）
    turnover = row["换手率"]
    if 2 <= turnover <= 15:
        score += min(turnover, 10) * 0.5
    
    # 流通市值（太小容易操纵，太大涨不动）
    mkt_cap = row["流通市值"]
    if 50 <= mkt_cap <= 500:
        score += 5
    elif 20 <= mkt_cap < 50:
        score += 3
    
    # 市盈率（正值且不太高）
    pe = row["市盈率"]
    if 0 < pe <= 30:
        score += 3
    elif 30 < pe <= 50:
        score += 1
    
    return round(score, 1)


def main():
    print("=" * 60)
    print("15元左右A股筛选（腾讯财经数据源）")
    print("=" * 60)
    
    # 第一步：获取股票代码列表
    print("\n[1/4] 获取A股代码列表...")
    codes_df = get_all_stock_codes()
    if codes_df.empty:
        print("❌ 无法获取股票列表，尝试直接筛选已知热门股...")
        # 备选：直接分析几只15元附近的股票
        test_codes = [
            "000001", "000002", "600000", "600016", "600019",
            "000725", "600239", "000100", "600808", "000709"
        ]
        results = batch_fetch(test_codes)
        df = pd.DataFrame(results)
        print(f"  获取到 {len(df)} 只股票")
        print(df.to_string(index=False))
        return
    
    # 只取部分样本（全量太大，先取3000只抽样）
    codes = codes_df["code"].astype(str).tolist()[:1000]  # 先跑1000只测试
    print(f"  共 {len(codes_df)} 只，本次抽样 {len(codes)} 只进行测试")
    
    # 第二步：批量获取行情
    print("\n[2/4] 批量获取实时行情（腾讯财经API）...")
    results = batch_fetch(codes, batch_size=50)
    df = pd.DataFrame(results)
    print(f"  成功获取 {len(df)} 只股票行情")
    
    if df.empty:
        print("❌ 未获取到行情数据")
        return
    
    # 第三步：筛选
    print(f"\n[3/4] 筛选 conditions：")
    print(f"  价格区间: {MIN_PRICE} ~ {MAX_PRICE} 元")
    print(f"  成交额下限: {MIN_AMOUNT} 亿元")
    
    mask = (
        (df["最新价"] >= MIN_PRICE) &
        (df["最新价"] <= MAX_PRICE) &
        (df["成交额"] >= MIN_AMOUNT * 10000)  # 腾讯API成交额单位是万元
    )
    filtered = df[mask].copy()
    print(f"  筛选后剩余 {len(filtered)} 只")
    
    # 第四步：评分排序
    print("\n[4/4] 综合评分...")
    filtered["评分"] = filtered.apply(score_stock, axis=1)
    filtered = filtered.sort_values("评分", ascending=False)
    
    # 输出结果
    print("\n" + "=" * 60)
    print(f"TOP {MAX_PICK} 推荐（15元左右A股）")
    print("=" * 60)
    
    top = filtered.head(MAX_PICK)
    show_cols = ["代码", "名称", "最新价", "涨跌幅", "换手率", "市盈率", "流通市值", "评分"]
    show_cols = [c for c in show_cols if c in top.columns]
    print(top[show_cols].to_string(index=False))
    
    # 保存
    out = f"stock_pick_{datetime.now().strftime('%Y%m%d')}.csv"
    top.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n✅ 结果已保存: {out}")


if __name__ == "__main__":
    main()
