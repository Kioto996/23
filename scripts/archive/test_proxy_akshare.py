#!/usr/bin/env python3
"""
使用代理 127.0.0.1:7897 测试获取真实资金流数据
"""
import os
import sys
import requests
import akshare as ak
import pandas as pd
import datetime

print("=" * 70)
print(f"Akshare 版本: {ak.__version__}")
print("=" * 70)

# 配置代理
proxy = "http://127.0.0.1:7897"
os.environ['HTTP_PROXY'] = proxy
os.environ['HTTPS_PROXY'] = proxy

print(f"\n[代理配置]")
print(f"  HTTP_PROXY:  {os.environ.get('HTTP_PROXY')}")
print(f"  HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")

# 测试1: 检查网络连接（通过代理）
print("\n" + "="*70)
print("[测试1] 检查网络连接（通过代理）...")
try:
    response = requests.get("http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&fs=m:90+t:2&fields=f12,f14,f2,f3", 
                        timeout=15)
    if response.status_code == 200:
        print("✓ 代理工作正常，可以访问东方财富 API")
        print(f"  返回数据: {response.text[:200]}")
    else:
        print(f"✗ 访问失败: HTTP {response.status_code}")
except Exception as e:
    print(f"✗ 网络测试失败: {e}")

# 测试2: 使用 akshare 获取板块资金流（通过代理）
print("\n" + "="*70)
print("[测试2] 使用 akshare 获取板块资金流...")
try:
    # 先检查 akshare 是否支持代理
    # 通过 monkeypatch requests 的 proxy 设置
    original_get = requests.get
    original_post = requests.post
    
    def proxy_get(url, **kwargs):
        kwargs.setdefault('proxies', {'http': proxy, 'https': proxy})
        return original_get(url, **kwargs)
    
    def proxy_post(url, **kwargs):
        kwargs.setdefault('proxies', {'http': proxy, 'https': proxy})
        return original_post(url, **kwargs)
    
    requests.get = proxy_get
    requests.post = proxy_post
    
    print("  已注入代理设置，尝试获取板块资金流...")
    df = ak.stock_sector_fund_flow_rank(indicator="今日")
    
    # 恢复原始方法
    requests.get = original_get
    requests.post = original_post
    
    print("✓ 获取成功!")
    print(f"  数据形状: {df.shape}")
    print(f"  总板块数: {len(df)}")
    print("\n  前10名板块:")
    print(df.head(10).to_string(index=False))
    
    # 保存数据
    output_file = "V:/psy/psy/stock/板块资金流_今日_真实.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n  数据已保存到: {output_file}")
    
except Exception as e:
    print(f"✗ 获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 直接爬取东方财富资金流 API（通过代理）
print("\n" + "="*70)
print("[测试3] 直接爬取东方财富板块资金流 API...")
try:
    # 东方财富板块资金流 API
    api_url = "http://push2.eastmoney.com/api/qt/clist/get"
    
    params = {
        'pn': '1',
        'pz': '50',
        'fs': 'm:90+t:2',  # 板块
        'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87'
    }
    
    proxies = {
        'http': proxy,
        'https': proxy
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://data.eastmoney.com/'
    }
    
    response = requests.get(api_url, params=params, headers=headers, proxies=proxies, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and 'diff' in data['data']:
            print("✓ 成功获取板块资金流数据!")
            sectors = data['data']['diff']
            print(f"  板块数量: {len(sectors)}")
            print("\n  前5个板块:")
            for i, item in enumerate(sectors[:5], 1):
                name = item.get('f14', 'N/A')
                zdf = item.get('f3', 'N/A')  # 涨跌幅
                print(f"  {i}. {name} - 涨跌幅: {zdf}%")
        else:
            print("✗ 返回数据格式异常")
            print(f"  返回数据: {data}")
    else:
        print(f"✗ API 请求失败: HTTP {response.status_code}")
        print(f"  响应内容: {response.text[:200]}")
        
except Exception as e:
    print(f"✗ 爬取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试4: 获取涨停板数据（验证代理是否影响已有功能）
print("\n" + "="*70)
print("[测试4] 获取涨停板数据（验证代理不影响已有功能）...")
try:
    today = datetime.datetime.now().strftime("%Y%m%d")
    df_zt = ak.stock_zt_pool_em(date=today)
    
    print("✓ 获取成功!")
    print(f"  涨停股票数: {len(df_zt)}")
    print("\n  前5只涨停股票:")
    print(df_zt.head(5).to_string(index=False))
    
except Exception as e:
    print(f"✗ 获取失败: {e}")

print("\n" + "="*70)
print("测试完成")
print("="*70)

print("\n【结论】")
print("如果测试2或测试3成功 → 可以获取真实资金流数据")
print("如果都失败 → 继续使用基于涨停板的估算方法")
