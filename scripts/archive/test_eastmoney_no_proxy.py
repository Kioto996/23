#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不使用代理访问东方财富API
"""

import requests
import json

def test_eastmoney_no_proxy():
    """测试不使用代理"""

    # 尝试多个东方财富API端点
    urls = [
        "http://push2.eastmoney.com/api/qt/clist/get",
        "http://83.push2.eastmoney.com/api/qt/clist/get",
        "https://push2.eastmoney.com/api/qt/clist/get",
    ]

    params = {
        "pn": 1,
        "pz": 20,
        "po": 1,
        "np": 1,
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": 2,
        "invt": 2,
        "fid": "f3",
        "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        "fields": "f1,f2,f3,f12,f14",
        "_": 1620000000000
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://quote.eastmoney.com/",
        "Accept": "application/json, text/plain, */*",
    }

    for i, url in enumerate(urls, 1):
        print(f"\n{'='*60}")
        print(f"测试URL {i}: {url}")
        print('='*60)

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)

            print(f"状态码: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")

            resp.encoding = 'utf-8'
            content = resp.text

            print(f"返回内容长度: {len(content)}")
            print(f"前300字符:")
            print(content[:300])

            # 尝试解析JSON
            try:
                data = resp.json()
                print("\n✓ JSON解析成功!")

                if 'data' in data and isinstance(data['data'], dict):
                    if 'diff' in data['data']:
                        stocks = data['data']['diff']
                        print(f"✓ 成功获取 {len(stocks)} 只股票")

                        if len(stocks) > 0:
                            print(f"\n前3只股票示例:")
                            for j, stock in enumerate(stocks[:3], 1):
                                print(f"  {j}. 代码:{stock.get('f12')} 名称:{stock.get('f14')} 价格:{stock.get('f2', 0)/100.0 if stock.get('f2') else 0}")
                            return url, data  # 成功，返回

            except json.JSONDecodeError as e:
                print(f"\n✗ JSON解析失败: {e}")

        except Exception as e:
            print(f"\n❌ 请求失败: {e}")

    print("\n" + "="*60)
    print("所有URL都失败了")
    print("="*60)
    return None, None

def test_sina_finance():
    """测试新浪财经API"""
    print("\n" + "="*60)
    print("测试新浪财经API")
    print("="*60)

    # 新浪财经API
    url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"

    params = {
        "page": 1,
        "num": 20,
        "sort": "symbol",
        "asc": 1,
        "node": "hs_a",
        "symbol": "",
        "_s_r_a": "init"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://finance.sina.com.cn/",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.encoding = 'gbk'
        content = resp.text

        print(f"状态码: {resp.status_code}")
        print(f"返回内容长度: {len(content)}")
        print(f"\n前500字符:")
        print(content[:500])

        # 新浪返回的是JSON数组
        try:
            data = json.loads(content)
            print("\n✓ JSON解析成功!")
            print(f"获取到 {len(data)} 条数据")

            if len(data) > 0:
                print(f"\n前3条示例:")
                for i, item in enumerate(data[:3], 1):
                    print(f"  {i}. {item}")
                return data
        except json.JSONDecodeError as e:
            print(f"\n✗ JSON解析失败: {e}")

    except Exception as e:
        print(f"\n❌ 请求失败: {e}")

    return None

if __name__ == '__main__':
    print("开始测试不同的数据源...")

    # 测试东方财富
    url, data = test_eastmoney_no_proxy()

    if url:
        print(f"\n✅ 成功! 可用的URL: {url}")
    else:
        # 测试新浪财经
        print("\n东方财富失败，尝试新浪财经...")
        data = test_sina_finance()

        if data:
            print("\n✅ 新浪财经API可用!")
        else:
            print("\n❌ 所有数据源都失败了")
