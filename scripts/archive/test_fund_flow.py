#!/usr/bin/env python3
"""
测试获取主力资金流向数据
使用akshare的资金流向API
"""

import akshare as ak
import pandas as pd

print("=== 测试获取主力资金流向数据 ===\n")

# 测试1: 板块资金流向
print("测试1: 板块资金流向 (东方财富)")
try:
    # 修复参数名：indicator 而不是 indiactor
    df = ak.stock_sector_fund_flow_rank(indicator="今日")
    print(f"✅ 成功! 数据形状: {df.shape}")
    print(f"\n列名: {df.columns.tolist()}")
    print(f"\n前5行:")
    print(df.head())
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "="*60 + "\n")

# 测试2: 个股资金流向
print("测试2: 个股资金流向 (东方财富)")
try:
    df2 = ak.stock_individual_fund_flow_rank(indicator="今日")
    print(f"✅ 成功! 数据形状: {df2.shape}")
    print(f"\n列名: {df2.columns.tolist()}")
    print(f"\n前3行:")
    print(df2.head(3))
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "="*60 + "\n")

# 测试3: 大盘资金流向
print("测试3: 大盘资金流向")
try:
    df3 = ak.stock_market_fund_flow()
    print(f"✅ 成功! 数据形状: {df3.shape}")
    print(f"\n前5行:")
    print(df3.head())
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "="*60 + "\n")

# 测试4: 尝试通过涨停板数据反推资金流向
print("测试4: 通过涨停板数据估算板块强度")
try:
    df4 = ak.stock_zt_pool_em(date='20260514')
    if '所属行业' in df4.columns:
        sector_counts = df4['所属行业'].value_counts()
        print("板块涨停数 TOP10:")
        for sector, count in sector_counts.head(10).items():
            # 简单估算：涨停数 * 平均流通市值 * 涨幅
            print(f"  {sector}: {count}只涨停 (估算资金强度: {count * 10}分)")
except Exception as e:
    print(f"❌ 失败: {e}")
