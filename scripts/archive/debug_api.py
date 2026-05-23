#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试API返回内容
"""

import requests
import json

# 配置代理
PROXIES = {
    'http': 'http://127.0.0.1:7897',
    "https": "http://127.0.0.1:7897",
}

def test_eastmoney():
    """测试东方财富API"""
    url = "http://push2.eastmoney.com/api/qt/clist/get"

    params = {
        "pn": 1,
        "pz": 20,  # 只获取20条测试
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "http://quote.eastmoney.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        print("正在请求东方财富API...")
        print(f"URL: {url}")
        print(f"Params: {params}")

        resp = requests.get(url, params=params, headers=headers, proxies=PROXIES, timeout=30)

        print(f"\n状态码: {resp.status_code}")
        print(f"编码: {resp.encoding}")
        print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")

        # 尝试解码
        resp.encoding = 'utf-8'
        content = resp.text

        print(f"\n返回内容长度: {len(content)}")
        print(f"\n前500字符:")
        print(content[:500])

        # 尝试解析JSON
        try:
            data = resp.json()
            print("\n✓ JSON解析成功!")
            print(f"数据结构: {list(data.keys())}")

            if 'data' in data:
                print(f"data键存在")
                if isinstance(data['data'], dict) and 'diff' in data['data']:
                    stocks = data['data']['diff']
                    print(f"成功获取 {len(stocks)} 只股票")
                    print(f"\n前3只股票示例:")
                    for i, stock in enumerate(stocks[:3], 1):
                        print(f"  {i}. {stock}")
        except json.JSONDecodeError as e:
            print(f"\n✗ JSON解析失败: {e}")

    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_eastmoney()
