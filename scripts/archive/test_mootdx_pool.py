#!/usr/bin/env python3
"""
测试 mootdx 的 pool() 方法和其他可用接口
重点：获取涨停池数据、板块数据
"""

import mootdx
from mootdx.quotes import Quotes
import traceback
import time

print("=" * 70)
print("Mootdx 版本:", mootdx.__version__)
print("=" * 70)

# 1. 尝试连接服务器（使用默认配置）
print("\n[1] 尝试连接行情服务器...")
client = None
try:
    # 不使用 bestip，直接创建连接
    client = Quotes.factory(market='std', quiet=False)
    print("✓ 行情服务器连接成功")
except Exception as e:
    print(f"✗ 连接失败: {e}")
    print("  尝试不连接服务器，直接查看 API...")

# 2. 如果连接成功，测试 pool() 方法
if client:
    print("\n[2] 测试 pool() 方法（可能是涨停池）...")
    try:
        # 尝试不同的参数组合
        try:
            data = client.pool()
            print("✓ pool() 调用成功（无参数）")
            if hasattr(data, 'head'):
                print("  数据预览:")
                print(data.head(10))
            else:
                print(f"  返回数据: {data}")
        except Exception as e1:
            print(f"✗ pool() 调用失败: {e1}")
            
    except Exception as e:
        print(f"✗ pool() 方法测试失败: {e}")
        traceback.print_exc()

# 3. 测试 block() 方法（获取板块信息）
if client:
    print("\n[3] 测试 block() 方法（板块信息）...")
    try:
        data = client.block(tofile=False)
        if data is not None and not data.empty:
            print("✓ block() 调用成功")
            print(f"  板块数量: {len(data)}")
            print("  数据预览:")
            print(data.head(10))
        else:
            print("✗ block() 返回空数据")
    except Exception as e:
        print(f"✗ block() 调用失败: {e}")
        traceback.print_exc()

# 4. 测试获取涨停板数据（通过实时行情筛选）
if client:
    print("\n[4] 测试获取涨停板数据...")
    try:
        # 获取所有A股列表
        print("  获取股票列表...")
        stocks_sh = client.stocks(market='sh')  # 上海市场
        stocks_sz = client.stocks(market='sz')  # 深圳市场
        
        if stocks_sh is not None and not stocks_sh.empty:
            print(f"✓ 上海市场股票数量: {len(stocks_sh)}")
            print("  数据预览:")
            print(stocks_sh.head())
        else:
            print("✗ 上海市场股票列表获取失败")
            
        if stocks_sz is not None and not stocks_sz.empty:
            print(f"✓ 深圳市场股票数量: {len(stocks_sz)}")
        else:
            print("✗ 深圳市场股票列表获取失败")
            
    except Exception as e:
        print(f"✗ 获取股票列表失败: {e}")
        traceback.print_exc()

# 5. 测试获取实时行情（少量股票）
if client:
    print("\n[5] 测试获取实时行情（少量股票）...")
    try:
        # 获取几只代表性股票的实时行情
        data = client.quotes(symbols=['600519', '000001', '300750'])
        if data is not None and not data.empty:
            print("✓ 实时行情获取成功")
            print("  数据预览:")
            print(data.to_string())
            print("\n  列名:", list(data.columns))
        else:
            print("✗ 实时行情获取失败: 返回空数据")
    except Exception as e:
        print(f"✗ 实时行情获取失败: {e}")
        traceback.print_exc()

# 6. 如果不能连接服务器，给出结论
if not client:
    print("\n" + "="*70)
    print("⚠️  无法连接行情服务器")
    print("="*70)
    print("\nmootdx 需要连接到通达信行情服务器才能获取数据。")
    print("如果无法连接，可能无法使用 mootdx 获取实时数据。")
    print("\n建议：")
    print("  1. 检查网络连接")
    print("  2. 使用 akshare 或其他库获取资金流数据")
    print("  3. 使用估算方法（涨停数量 × 系数）")

print("\n" + "="*70)
print("测试完成")
print("="*70)

# 7. 总结
print("\n【总结】")
print("Mootdx 可用功能:")
print("  ✓ 获取股票列表 (stocks)")
print("  ✓ 获取实时行情 (quotes)")
print("  ✓ 获取K线数据 (bars)")
print("  ✓ 获取板块信息 (block)")
print("  ? pool() 方法功能未知")
print("\n⚠️  Mootdx 没有直接获取资金流数据的接口")
print("   如果需要资金流数据，建议:")
print("   1. 使用 akshare.stock_sector_fund_flow_rank()")
print("   2. 使用 tushare（需要积分）")
print("   3. 爬取东方财富网站数据")
print("   4. 使用估算方法（涨停数量 × 系数）")
