#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用新浪财经API获取A股股票数据，筛选15元左右的股票
"""

import requests
import json
import time

def fetch_all_stocks_sina(page=1, num=100):
    """
    从新浪财经获取A股股票列表
    """
    url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"

    params = {
        "page": page,
        "num": num,
        "sort": "symbol",
        "asc": 1,
        "node": "hs_a",  # 沪深A股
        "symbol": "",
        "_s_r_a": "init"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://finance.sina.com.cn/",
        "Accept": "application/json, text/plain, */*",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.encoding = 'gbk'
        data = resp.json()
        return data
    except Exception as e:
        print(f"获取第{page}页失败: {e}")
        return None

def fetch_all_a_stocks(max_pages=50):
    """
    获取所有A股股票（分页获取）
    """
    all_stocks = []

    for page in range(1, max_pages + 1):
        print(f"正在获取第 {page}/{max_pages} 页...", end=" ")

        stocks = fetch_all_stocks_sina(page=page, num=100)

        if not stocks or len(stocks) == 0:
            print("无数据，结束")
            break

        all_stocks.extend(stocks)
        print(f"获取到 {len(stocks)} 只，累计 {len(all_stocks)} 只")

        # 如果这一页数据少于100条，说明已经是最后一页
        if len(stocks) < 100:
            print("已到最后一页")
            break

        # 避免请求过快
        time.sleep(0.5)

    return all_stocks

def filter_stocks_around_15_yuan(stocks, target_price=15.0, tolerance=5.0):
    """
    筛选15元左右的股票
    """
    filtered = []

    for stock in stocks:
        try:
            # 当前价
            price = float(stock.get('trade', 0))

            # 涨跌幅
            change_pct = float(stock.get('changepercent', 0))

            # 成交额（元）
            volume = int(stock.get('volume', 0))

            # 换手率
            turnover = float(stock.get('turnoverratio', 0))

            # 市盈率
            pe = float(stock.get('per', 0))

            # 市净率
            pb = float(stock.get('pb', 0))

            # 流通市值（万）
            float_market_cap = float(stock.get('nmc', 0)) / 10000.0  # 转换为亿

            # 总市值（万）
            total_market_cap = float(stock.get('mktcap', 0)) / 10000.0  # 转换为亿

            # 代码和名称
            code = stock.get('code', '')
            name = stock.get('name', '')
            symbol = stock.get('symbol', '')

            # 只保留沪深A股（排除北交所bj）
            if symbol.startswith('bj'):
                continue

            # 筛选15元左右的股票（15±5元）
            if target_price - tolerance <= price <= target_price + tolerance:
                filtered.append({
                    'code': code,
                    'symbol': symbol,
                    'name': name,
                    'price': price,
                    'change_pct': change_pct,
                    'volume': volume,
                    'turnover': turnover,
                    'pe': pe,
                    'pb': pb,
                    'float_market_cap': float_market_cap,
                    'total_market_cap': total_market_cap
                })

        except Exception as e:
            continue

    return filtered

def score_stock(stock):
    """
    给股票打分（满分100）
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
    print("A股15元左右股票筛选器 (新浪财经API)")
    print("=" * 60)

    # 1. 获取所有A股股票
    print("\n正在从新浪财经获取A股股票数据...")
    stocks = fetch_all_a_stocks(max_pages=50)

    if not stocks or len(stocks) == 0:
        print("\n❌ 无法获取股票数据")
        return

    print(f"\n✓ 共获取 {len(stocks)} 只A股股票")

    # 2. 筛选15元左右的股票
    print("\n正在筛选15元左右的股票（10-20元）...")
    filtered = filter_stocks_around_15_yuan(stocks, target_price=15.0, tolerance=5.0)

    print(f"\n找到 {len(filtered)} 只15元左右的股票")

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
    print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'价格':<8} {'涨跌幅%':<10} {'换手率%':<10} {'市盈率':<10} {'评分':<10}")
    print("-" * 60)

    for i, stock in enumerate(filtered[:20], 1):
        print(f"{i:<4} {stock['code']:<8} {stock['name']:<10} {stock['price']:<8.2f} {stock['change_pct']:<10.2f} {stock['turnover']:<10.2f} {stock['pe']:<10.2f} {stock['score']:<10}")

    # 5. 详细分析前2名
    print("\n" + "=" * 60)
    print("前2名详细分析与投资建议")
    print("=" * 60)

    for i in range(min(2, len(filtered))):
        stock = filtered[i]
        print(f"\n【推荐 {i+1}】{stock['name']} ({stock['code']})")
        print(f"  💰 当前价格: {stock['price']:.2f} 元")
        print(f"  📈 涨跌幅: {stock['change_pct']:.2f}%")
        print(f"  🔄 换手率: {stock['turnover']:.2f}%")
        print(f"  📊 市盈率(PE): {stock['pe']:.2f}")
        print(f"  📦 市净率(PB): {stock['pb']:.2f}")
        print(f"  💎 流通市值: {stock['float_market_cap']:.2f} 亿")
        print(f"  🏢 总市值: {stock['total_market_cap']:.2f} 亿")
        print(f"  ⭐ 综合评分: {stock['score']}/100")

        # 投资建议
        print(f"\n  {'='*50}")
        print("  💡 投资建议:")
        print(f"  {'='*50}")

        # 价格分析
        if abs(stock['price'] - 15) <= 1:
            print(f"  ✓ 价格理想（{stock['price']:.2f}元），接近目标价位")
        else:
            print(f"  - 价格为{stock['price']:.2f}元，偏离15元目标较多")

        # 涨跌分析
        if stock['change_pct'] > 3:
            print(f"  ⚠️  当日涨幅较大（{stock['change_pct']:.2f}%），注意追高风险")
        elif stock['change_pct'] < -3:
            print(f"  ⚠️  当日跌幅较大（{stock['change_pct']:.2f}%），注意风险")
        else:
            print(f"  ✓ 当日走势平稳（{stock['change_pct']:.2f}%）")

        # 换手率分析
        if stock['turnover'] > 20:
            print(f"  ⚠️  换手率过高（{stock['turnover']:.2f}%），可能是短期炒作")
        elif stock['turnover'] < 1:
            print(f"  ⚠️  换手率过低（{stock['turnover']:.2f}%），流动性不足")
        else:
            print(f"  ✓ 换手率正常（{stock['turnover']:.2f}%）")

        # 估值分析
        if stock['pe'] > 100:
            print(f"  ⚠️  市盈率过高（{stock['pe']:.2f}），估值偏贵")
        elif stock['pe'] < 0:
            print(f"  ⚠️  市盈率为负（{stock['pe']:.2f}），公司可能亏损")
        elif stock['pe'] <= 30:
            print(f"  ✓ 市盈率合理（{stock['pe']:.2f}），估值健康")
        else:
            print(f"  - 市盈率{stock['pe']:.2f}，估值尚可")

        # 市值分析
        if stock['float_market_cap'] < 20:
            print(f"  ⚠️  流通市值较小（{stock['float_market_cap']:.2f}亿），流动性风险")
        elif stock['float_market_cap'] > 1000:
            print(f"  - 流通市值较大（{stock['float_market_cap']:.2f}亿），上涨空间有限")
        else:
            print(f"  ✓ 流通市值适中（{stock['float_market_cap']:.2f}亿）")

        print(f"\n  📝 综合建议:")
        if stock['score'] >= 80:
            print(f"  🌟 强烈推荐！综合评分{stock['score']}分，各项指标优秀")
        elif stock['score'] >= 70:
            print(f"  👍 推荐关注！综合评分{stock['score']}分，性价比较高")
        elif stock['score'] >= 60:
            print(f"  👀 可以关注，综合评分{stock['score']}分，有一定投资价值")
        else:
            print(f"  ⚠️  谨慎对待，综合评分{stock['score']}分，风险较大")

    # 6. 保存结果
    output_file = 'stocks_15yuan_sina.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered[:50], f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {output_file}")

    print("\n" + "=" * 60)
    print("✅ 分析完成!")
    print("=" * 60)
    print("\n⚠️  免责声明: 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎！")

if __name__ == '__main__':
    main()
