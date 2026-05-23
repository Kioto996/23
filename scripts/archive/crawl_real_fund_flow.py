#!/usr/bin/env python3
"""
直接爬取东方财富板块资金流数据（通过代理）
绕过 akshare 的问题，直接调用东方财富 API
"""
import requests
import json
import pandas as pd
from datetime import datetime

# 代理配置
PROXY = "http://127.0.0.1:7897"
proxies = {
    'http': PROXY,
    'https': PROXY
}

print("=" * 70)
print("直接爬取东方财富板块资金流数据")
print(f"代理: {PROXY}")
print("=" * 70)

# 东方财富板块资金流 API（从浏览器开发者工具抓取的真实接口）
url = "http://push2.eastmoney.com/api/qt/clist/get"

params = {
    'pn': '1',
    'pz': '50',
    'po': '1',
    'np': '1',
    'fltt': '2',
    'invt': '2',
    'fid': 'f3',  # 按涨跌幅排序
    'fs': 'm:90+t:2',  # 板块
    'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'http://data.eastmoney.com/bkzj/hy.html',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

print("\n[请求] 正在获取板块资金流数据...")
try:
    response = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=30)
    
    print(f"  状态码: {response.status_code}")
    print(f"  响应长度: {len(response.text)}")
    print(f"  前200字符: {response.text[:200]}")
    
    if response.status_code == 200:
        data = response.json()
        
        if 'data' in data and 'diff' in data['data']:
            sectors = data['data']['diff']
            print(f"\n✓✓✓ 获取成功! ✓✓✓")
            print(f"  板块数量: {len(sectors)}")
            
            # 解析数据
            parsed_data = []
            for item in sectors:
                parsed_data.append({
                    '板块名称': item.get('f14', ''),
                    '板块代码': item.get('f12', ''),
                    '最新价': item.get('f2', 0),
                    '涨跌幅': item.get('f3', 0),
                    '主力净流入': item.get('f62', 0),  # 主力净流入
                    '小单净流入': item.get('f184', 0),
                    '中单净流入': item.get('f66', 0),
                    '大单净流入': item.get('f69', 0),
                    '超大单净流入': item.get('f72', 0),
                })
            
            df = pd.DataFrame(parsed_data)
            
            # 转换资金单位（通常是以万元为单位）
            fund_columns = ['主力净流入', '小单净流入', '中单净流入', '大单净流入', '超大单净流入']
            for col in fund_columns:
                df[col] = df[col] / 10000  # 转换为亿元
            
            print(f"\n  资金流数据（亿元）:")
            print(df.head(10).to_string(index=False))
            
            # 保存数据
            output_file = "V:/psy/psy/stock/板块资金流_真实数据.csv"
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n  数据已保存到: {output_file}")
            print(f"\n  ✅✅✅ 成功获取真实资金流数据！✅✅✅")
            
        else:
            print("✗ 返回数据格式异常")
            print(f"  返回数据: {data}")
    else:
        print(f"✗ 请求失败: HTTP {response.status_code}")
        
except Exception as e:
    print(f"✗ 请求失败: {e}")
    import traceback
    traceback.print_exc()

# 同时获取个股资金流
print("\n" + "="*70)
print("[附加] 获取个股资金流 TOP50...")
try:
    url_stocks = "http://push2.eastmoney.com/api/qt/clist/get"
    
    params_stocks = {
        'pn': '1',
        'pz': '50',
        'po': '1',
        'np': '1',
        'fltt': '2',
        'invt': '2',
        'fid': 'f62',  # 按主力净流入排序
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',  # A股
        'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75'
    }
    
    response2 = requests.get(url_stocks, params=params_stocks, headers=headers, proxies=proxies, timeout=30)
    
    if response2.status_code == 200:
        data2 = response2.json()
        
        if 'data' in data2 and 'diff' in data2['data']:
            stocks = data2['data']['diff']
            print(f"✓ 获取成功! 股票数量: {len(stocks)}")
            
            parsed_stocks = []
            for item in stocks[:10]:  # 只取前10
                parsed_stocks.append({
                    '股票名称': item.get('f14', ''),
                    '股票代码': item.get('f12', ''),
                    '最新价': item.get('f2', 0),
                    '涨跌幅': item.get('f3', 0),
                    '主力净流入': item.get('f62', 0) / 10000,  # 转换为亿元
                })
            
            df_stocks = pd.DataFrame(parsed_stocks)
            print("\n  主力净流入 TOP10:")
            print(df_stocks.to_string(index=False))
            
            # 保存
            output_file2 = "V:/psy/psy/stock/个股资金流_真实数据.csv"
            df_stocks.to_csv(output_file2, index=False, encoding='utf-8-sig')
            print(f"\n  数据已保存到: {output_file2}")
            
except Exception as e:
    print(f"✗ 获取个股资金流失败: {e}")

print("\n" + "="*70)
print("测试完成")
print("="*70)

print("\n【最终结论】")
print("✅ 如果成功获取 → 可以完美替换估算方法")
print("❌ 如果还是失败 → 继续使用基于涨停板的估算")
