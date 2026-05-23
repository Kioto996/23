#!/usr/bin/env python3
"""
测试带代理配置的 akshare，获取真实资金流数据
"""
import os
import sys
import akshare as ak
import requests
import pandas as pd

print("=" * 70)
print(f"Akshare 版本: {ak.__version__}")
print("=" * 70)

# 配置代理（从系统读取或手动配置）
# Windows 系统代理通常需要从注册表或环境变量读取
# 这里尝试几种常见方式

print("\n[1] 检查当前网络配置...")
print(f"  HTTP_PROXY: {os.environ.get('HTTP_PROXY', '(未设置)')}")
print(f"  HTTPS_PROXY: {os.environ.get('HTTPS_PROXY', '(未设置)')}")

# 测试网络连接
print("\n[2] 测试网络连接（直接访问东方财富）...")
try:
    # 测试能否访问东方财富网
    test_url = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&fs=m:90+t:2&fields=f12,f14,f2,f3,f62,f184"
    response = requests.get(test_url, timeout=10)
    if response.status_code == 200:
        print("✓ 可以访问东方财富 API")
        print(f"  返回数据长度: {len(response.text)}")
        print(f"  前100字符: {response.text[:100]}")
    else:
        print(f"✗ 访问失败: HTTP {response.status_code}")
except Exception as e:
    print(f"✗ 网络测试失败: {e}")

# 测试3: 尝试获取板块资金流（使用 working API）
print("\n[3] 尝试获取板块资金流（使用涨停板数据推算）...")
try:
    # 获取今日涨停板数据
    import datetime
    today = datetime.datetime.now().strftime("%Y%m%d")
    df_zt = ak.stock_zt_pool_em(date=today)
    
    print(f"✓ 获取今日({today})涨停板数据成功")
    print(f"  涨停股票数: {len(df_zt)}")
    
    # 按行业分组，计算涨停数量
    if '所属行业' in df_zt.columns:
        sector_count = df_zt['所属行业'].value_counts()
        print(f"\n  行业涨停数量 TOP10:")
        print(sector_count.head(10))
        
        # 保存行业涨停数据
        output_file = "V:/psy/psy/stock/行业涨停统计_今日.csv"
        sector_count.to_csv(output_file, encoding='utf-8-sig')
        print(f"\n  数据已保存到: {output_file}")
    else:
        print("  ⚠️  数据中无'所属行业'列，尝试其他列...")
        print(f"  可用列: {list(df_zt.columns)}")
        
except Exception as e:
    print(f"✗ 获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试4: 尝试直接爬取东方财富资金流页面
print("\n[4] 尝试直接爬取东方财富资金流数据...")
try:
    # 东方财富板块资金流页面 API
    # 这个 URL 可能需要从浏览器开发者工具中抓取
    api_url = "http://push2.eastmoney.com/api/qt/clist/get"
    
    params = {
        'pn': '1',
        'pz': '50',
        'fs': 'm:90+t:2',  # 创业板板块
        'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://data.eastmoney.com/'
    }
    
    response = requests.get(api_url, params=params, headers=headers, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and 'diff' in data['data']:
            print("✓ 成功获取板块数据!")
            print(f"  板块数量: {len(data['data']['diff'])}")
            print("\n  前5个板块数据:")
            for i, item in enumerate(data['data']['diff'][:5], 1):
                print(f"  {i}. {item.get('f14', 'N/A')} - 涨跌幅: {item.get('f3', 'N/A')}")
        else:
            print("✗ 返回数据格式异常")
            print(f"  返回数据: {data}")
    else:
        print(f"✗ API 请求失败: HTTP {response.status_code}")
        
except Exception as e:
    print(f"✗ 爬取失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n【结论】")
print("1. 如果测试4成功 → 可以用爬取的数据替换估算方法")
print("2. 如果测试4失败 → 建议:")
print("   a) 手动配置代理: set HTTP_PROXY=http://proxy:port")
print("   b) 使用估算方法（基于涨停数量）")
print("   c) 考虑使用 tushare（需要积分）")
