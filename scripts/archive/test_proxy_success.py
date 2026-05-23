#!/usr/bin/env python3
"""
使用代理 127.0.0.1:7897 测试 akshare 获取真实资金流数据
"""
import os
import sys
import requests

# ⚠️ 必须在导入 akshare 之前设置代理环境变量
proxy = "http://127.0.0.1:7897"
os.environ['HTTP_PROXY'] = proxy
os.environ['HTTPS_PROXY'] = proxy

import akshare as ak
import pandas as pd
import datetime

print("=" * 70)
print(f"Akshare 版本: {ak.__version__}")
print(f"代理设置: {proxy}")
print("=" * 70)

# 验证代理是否生效
print("\n[验证] 检查代理是否生效...")
try:
    r = requests.get('http://ip-api.com/json', timeout=10, 
                   proxies={'http': proxy, 'https': proxy})
    ip_info = r.json()
    print(f"✓ 当前出口IP: {ip_info.get('query', 'N/A')}")
    print(f"  国家: {ip_info.get('country', 'N/A')}")
except Exception as e:
    print(f"✗ 代理验证失败: {e}")

# 测试1: 获取板块资金流排名（今日）
print("\n" + "="*70)
print("[测试1] 获取板块资金流排名（今日）...")
try:
    df = ak.stock_sector_fund_flow_rank(indicator="今日")
    print("✓✓✓ 获取成功! ✓✓✓")
    print(f"  数据形状: {df.shape}")
    print(f"  总板块数: {len(df)}")
    print("\n  前10名板块:")
    print(df.head(10).to_string(index=False))
    
    # 保存数据
    output_file = "V:/psy/psy/stock/板块资金流_今日_真实.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n  数据已保存到: {output_file}")
    print("\n  ✅ 可以用真实数据替换估算方法了！")
    
except Exception as e:
    print(f"✗ 获取失败: {e}")
    print("\n  错误详情:")
    import traceback
    traceback.print_exc()

# 测试2: 获取个股资金流排名
print("\n" + "="*70)
print("[测试2] 获取个股资金流排名（今日）...")
try:
    df_stocks = ak.stock_individual_fund_flow_rank(indicator="今日")
    print("✓✓✓ 获取成功! ✓✓✓")
    print(f"  数据形状: {df_stocks.shape}")
    print(f"  总股票数: {len(df_stocks)}")
    print("\n  前10名个股:")
    print(df_stocks.head(10).to_string(index=False))
    
    # 保存数据
    output_file2 = "V:/psy/psy/stock/个股资金流_今日_真实.csv"
    df_stocks.to_csv(output_file2, index=False, encoding='utf-8-sig')
    print(f"\n  数据已保存到: {output_file2}")
    
except Exception as e:
    print(f"✗ 获取失败: {e}")

# 测试3: 获取涨停板数据（验证不受影响）
print("\n" + "="*70)
print("[测试3] 获取涨停板数据...")
try:
    today = datetime.datetime.now().strftime("%Y%m%d")
    df_zt = ak.stock_zt_pool_em(date=today)
    print("✓ 获取成功!")
    print(f"  涨停股票数: {len(df_zt)}")
    
except Exception as e:
    print(f"✗ 获取失败: {e}")

print("\n" + "="*70)
print("测试完成")
print("="*70)

print("\n【最终结论】")
if 'df' in locals() and not df.empty:
    print("🎉🎉🎉 板块资金流数据获取成功！🎉🎉🎉")
    print("→ 现在可以改写 stock_observation_system_v3.py")
    print("→ 用真实资金流数据替换估算方法")
else:
    print("❌ 板块资金流数据获取失败")
    print("→ 需要继续排查问题")
    print("→ 或者继续使用基于涨停板的估算方法")
