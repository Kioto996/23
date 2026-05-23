#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用代理获取A股股票数据
"""

import requests
import json
import time
from datetime import datetime

# 配置代理
PROXIES = {
    'http': 'http://127.0.0.1:7897',
    'https': 'http://127.0.0.1:7897',
}

def fetch_stock_list_eastmoney():
    """
    从东方财富获取A股股票列表
    """
    url = "http://push2.eastmoney.com/api/qt/clist/get"

    params = {
        'pn': 1,
        'pz': 5000,  # 获取所有股票
        'po': 1,
        'np': 1,
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': 2,
        'invt': 2,
        'fid': 'f3',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',  # A股主板+创业板
        'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152',
        '_': int(time.time() * 1000)
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://quote.eastmoney.com/',
        'Accept': 'application/json, text/plain, */*',
    }

    try:
        print("正在从东方财富获取数据...")
        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=30)
        resp.encoding = 'utf-8'
        data = resp.json()

        if data and 'data' in data and 'diff' in data['data']:
            stocks = data['data']['diff']
            print(f"成功获取 {len(stocks)} 只股票")
            return stocks
        else:
            print(f"返回数据格式异常: {data}")
            return []

    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []

def filter_stocks_around_15_yuan(stocks, target_price=15.0, tolerance=5.0):
    """
    筛选15元左右的股票
    """
    filtered = []

    for stock in stocks:
        try:
            # 当前价
            price = stock.get('f2', 0) / 100.0 if stock.get('f2') else 0

            # 涨跌幅
            change_pct = stock.get('f3', 0) / 100.0 if stock.get('f3') else 0

            # 成交额
            volume = stock.get('f5', 0)

            # 换手率
            turnover = stock.get('f8', 0) / 100.0 if stock.get('f8') else 0

            # 市盈率
            pe = stock.get('f9', 0) / 100.0 if stock.get('f9') else 0

            # 流通市值
            float_market_cap = stock.get('f21', 0) / 100000000.0 if stock.get('f21') else 0

            # 总市值
            total_market_cap = stock.get('f20', 0) / 100000000.0 if stock.get('f20') else 0

            # 代码和名称
            code = stock.get('f12', '')
            name = stock.get('f14', '')

            # 筛选15元左右的股票（15±5元）
            if target_price - tolerance <= price <= target_price + tolerance:
                filtered.append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change_pct': change_pct,
                    'volume': volume,
                    'turnover': turnover,
                    'pe': pe,
                    'float_market_cap': float_market_cap,
                    'total_market_cap': total_market_cap
                })

        except Exception as e:
            continue

    return filtered

def score_stock(stock):
    """
    给股票打分
    """
    score = 0

    # 1. 价格接近15元 (30分)
    price_diff = abs(stock['price'] - 15)
    if price_diff <= 1:
        score += 30
    elif price_diff <= 2:
        score += 25
    elif price_diff <= 3:
        score += 20
    else:
        score += 15

    # 2. 换手率适中 (20分) - 太低的没人玩，太高的可能是炒作
    if 3 <= stock['turnover'] <= 15:
        score += 20
    elif 1 <= stock['turnover'] < 3:
        score += 15
    elif 15 < stock['turnover'] <= 25:
        score += 10

    # 3. 市盈率合理 (20分)
    if 0 < stock['pe'] <= 30:
        score += 20
    elif 30 < stock['pe'] <= 50:
        score += 15
    elif 50 < stock['pe'] <= 100:
        score += 10

    # 4. 流通市值适中 (15分) - 不太大不太小
    if 50 <= stock['float_market_cap'] <= 500:
        score += 15
    elif 20 <= stock['float_market_cap'] < 50:
        score += 12
    elif 500 < stock['float_market_cap'] <= 1000:
        score += 10

    # 5. 涨跌幅 (15分)
    if stock['change_pct'] > 0:
        score += 10
    if abs(stock['change_pct']) < 5:
        score += 5

    return score

def main():
    print("=" * 60)
    print("A股15元左右股票筛选器 (使用代理)")
    print("=" * 60)

    # 1. 获取所有A股股票
    stocks = fetch_stock_list_eastmoney()

    if not stocks:
        print("\n❌ 无法获取股票数据")
        return

    # 2. 筛选15元左右的股票
    print("\n正在筛选15元左右的股票...")
    filtered = filter_stocks_around_15_yuan(stocks, target_price=15.0, tolerance=5.0)

    print(f"\n找到 {len(filtered)} 只15元左右(10-20元)的股票")

    if len(filtered) == 0:
        print("\n❌ 没有找到符合条件的股票")
        return

    # 3. 打分排序
    print("\n正在打分排序...")
    for stock in filtered:
        stock['score'] = score_stock(stock)

    filtered.sort(key=lambda x: x['score'], reverse=True)

    # 4. 显示前20名
    print("\n" + "=" * 60)
    print("TOP 20 推荐股票")
    print("=" * 60)
    print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'价格':<8} {'涨跌幅%':<10} {'换手率%':<10} {'市盈率':<10} {'综合评分':<10}")
    print("-" * 60)

    for i, stock in enumerate(filtered[:20], 1):
        print(f"{i:<4} {stock['code']:<8} {stock['name']:<10} {stock['price']:<8.2f} {stock['change_pct']:<10.2f} {stock['turnover']:<10.2f} {stock['pe']:<10.2f} {stock['score']:<10}")

    # 5. 详细分析前2名
    print("\n" + "=" * 60)
    print("前2名详细分析")
    print("=" * 60)

    for i in range(min(2, len(filtered))):
        stock = filtered[i]
        print(f"\n【推荐 {i+1}】{stock['name']} ({stock['code']})")
        print(f"  当前价格: {stock['price']:.2f} 元")
        print(f"  涨跌幅: {stock['change_pct']:.2f}%")
        print(f"  换手率: {stock['turnover']:.2f}%")
        print(f"  市盈率(PE): {stock['pe']:.2f}")
        print(f"  流通市值: {stock['float_market_cap']:.2f} 亿")
        print(f"  总市值: {stock['total_market_cap']:.2f} 亿")
        print(f"  综合评分: {stock['score']}/100")

        # 简单判断
        print("\n  投资建议:")
        if stock['change_pct'] > 3:
            print("    ⚠️  当日涨幅较大，注意追高风险")
        elif stock['change_pct'] < -3:
            print("    ⚠️  当日跌幅较大，注意风险")
        else:
            print("    ✓ 当日走势平稳")

        if stock['turnover'] > 20:
            print("    ⚠️  换手率过高，可能是短期炒作")
        elif stock['turnover'] < 1:
            print("    ⚠️  换手率过低，流动性不足")
        else:
            print("    ✓ 换手率正常")

        if stock['pe'] > 100:
            print("    ⚠️  市盈率过高，估值偏贵")
        elif stock['pe'] < 0:
            print("    ⚠️  市盈率为负，公司可能亏损")
        else:
            print("    ✓ 市盈率合理")

    # 6. 保存结果
    output_file = 'stocks_15yuan_proxy.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered[:50], f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {output_file}")

    print("\n" + "=" * 60)
    print("✅ 分析完成!")
    print("=" * 60)

if __name__ == '__main__':
    main()
