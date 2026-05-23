#!/usr/bin/env python3
"""
测试在系统代理下 akshare 能否获取真实资金流数据
"""
import akshare as ak
import pandas as pd
import sys

print("=" * 70)
print(f"Akshare 版本: {ak.__version__}")
print("=" * 70)

# 测试1: 获取板块资金流排名（今日）
print("\n[测试1] 获取板块资金流排名（今日）...")
try:
    df = ak.stock_sector_fund_flow_rank(indicator="今日")
    print("✓ 获取成功!")
    print(f"  数据形状: {df.shape}")
    print(f"  总板块数: {len(df)}")
    print("\n  前10名板块:")
    print(df.head(10).to_string(index=False))
    
    # 保存数据供后续使用
    output_file = "V:/psy/psy/stock/板块资金流_今日.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n  数据已保存到: {output_file}")
    
except Exception as e:
    print(f"✗ 获取失败: {e}")
    print("\n  尝试其他 indicator 参数...")
    
    # 尝试其他参数
    for indicator in ["3日", "5日", "10日"]:
        try:
            print(f"\n  尝试 indicator='{indicator}'...")
            df = ak.stock_sector_fund_flow_rank(indicator=indicator)
            print(f"  ✓ 成功! 数据形状: {df.shape}")
            print(df.head(5).to_string(index=False))
            break
        except Exception as e2:
            print(f"  ✗ 失败: {e2}")

# 测试2: 获取个股资金流排名
print("\n" + "=" * 70)
print("[测试2] 获取个股资金流排名...")
try:
    df_stocks = ak.stock_individual_fund_flow_rank(indicator="今日")
    print("✓ 获取成功!")
    print(f"  数据形状: {df_stocks.shape}")
    print(f"  总股票数: {len(df_stocks)}")
    print("\n  前10名个股:")
    print(df_stocks.head(10).to_string(index=False))
    
    # 保存数据
    output_file2 = "V:/psy/psy/stock/个股资金流_今日.csv"
    df_stocks.to_csv(output_file2, index=False, encoding='utf-8-sig')
    print(f"\n  数据已保存到: {output_file2}")
    
except Exception as e:
    print(f"✗ 获取失败: {e}")

# 测试3: 获取涨停板数据
print("\n" + "=" * 70)
print("[测试3] 获取涨停板数据...")
try:
    # 获取今天的涨停板数据
    import datetime
    today = datetime.datetime.now().strftime("%Y%m%d")
    print(f"  尝试获取 {today} 的涨停板数据...")
    
    df_zt = ak.stock_zt_pool_em(date=today)
    print("✓ 获取成功!")
    print(f"  涨停股票数: {len(df_zt)}")
    print("\n  前10只涨停股票:")
    print(df_zt.head(10).to_string(index=False))
    
    # 保存数据
    output_file3 = f"V:/psy/psy/stock/涨停板_{today}.csv"
    df_zt.to_csv(output_file3, index=False, encoding='utf-8-sig')
    print(f"\n  数据已保存到: {output_file3}")
    
except Exception as e:
    print(f"✗ 获取失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

# 总结
print("\n【总结】")
if 'df' in locals() and not df.empty:
    print("✓ 板块资金流数据获取成功")
    print("  → 可以用于替换估算方法")
else:
    print("✗ 板块资金流数据获取失败")
    print("  → 需要继续排查网络问题")

if 'df_stocks' in locals() and not df_stocks.empty:
    print("✓ 个股资金流数据获取成功")
else:
    print("✗ 个股资金流数据获取失败")

if 'df_zt' in locals() and not df_zt.empty:
    print("✓ 涨停板数据获取成功")
else:
    print("✗ 涨停板数据获取失败")
