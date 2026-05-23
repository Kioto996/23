#!/usr/bin/env python3
"""
测试 mootdx 获取 A股数据的能力 - 简化版
重点：正确连接服务器，获取可用数据
"""

import mootdx
from mootdx.quotes import Quotes
import traceback

print("=" * 60)
print("Mootdx 版本:", mootdx.__version__)
print("=" * 60)

# 1. 使用 bestip=True 自动选择最佳服务器
print("\n[1] 测试连接行情服务器 (bestip=True)...")
try:
    client = Quotes.factory(market='std', bestip=True)
    print("✓ 行情服务器连接成功")
    
    # 查看 client 有哪些方法
    methods = [m for m in dir(client) if not m.startswith('_')]
    print(f"\n可用方法 ({len(methods)}个):")
    for i, m in enumerate(methods, 1):
        print(f"  {i:2d}. {m}")
        
except Exception as e:
    print(f"✗ 连接失败: {e}")
    traceback.print_exc()
    client = None

# 2. 如果连接成功，测试获取实时行情
if client:
    print("\n[2] 测试获取实时行情...")
    try:
        # 获取贵州茅台(600519)和平安银行(000001)的实时行情
        data = client.stocks(symbols=['600519', '000001'])
        if data is not None and not data.empty:
            print("✓ 实时行情获取成功:")
            print(data.to_string())
        else:
            print("✗ 实时行情获取失败: 返回空数据")
    except Exception as e:
        print(f"✗ 实时行情获取失败: {e}")
        traceback.print_exc()

# 3. 测试获取涨停板数据
if client:
    print("\n[3] 测试获取涨停板数据...")
    try:
        # 查看是否有涨停板相关方法
        if hasattr(client, 'zt_pool'):
            data = client.zt_pool()
            print("✓ zt_pool 方法存在")
            print(data.head() if hasattr(data, 'head') else data)
        elif hasattr(client, 'limit_up'):
            data = client.limit_up()
            print("✓ limit_up 方法存在")
            print(data.head() if hasattr(data, 'head') else data)
        else:
            print("✗ 未找到涨停板相关方法")
            print("  可用方法中可能包含: stocks, bars, index, etc.")
    except Exception as e:
        print(f"✗ 涨停板数据获取失败: {e}")

# 4. 测试获取K线数据（验证连接可用性）
if client:
    print("\n[4] 测试获取K线数据...")
    try:
        # 获取贵州茅台最近5天的日K数据
        data = client.bars(symbol='600519', frequency=9, offset=5)  # frequency=9 是日线
        if data is not None and not data.empty:
            print("✓ K线数据获取成功:")
            print(data.to_string())
        else:
            print("✗ K线数据获取失败: 返回空数据")
    except Exception as e:
        print(f"✗ K线数据获取失败: {e}")
        traceback.print_exc()

# 5. 查看 mootdx.reader 模块（读取本地通达信数据）
print("\n[5] 测试 mootdx.reader 模块...")
try:
    from mootdx.reader import Reader
    print("✓ Reader 模块可用")
    print("  Reader 用于读取本地通达信数据，需要配置通达信安装路径")
except Exception as e:
    print(f"✗ Reader 模块测试失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

# 6. 总结
print("\n【总结】")
print("Mootdx 主要功能:")
print("  1. 获取实时行情 (stocks)")
print("  2. 获取K线数据 (bars)")
print("  3. 读取本地通达信数据 (reader)")
print("\n⚠️  注意: mootdx 可能没有直接获取资金流数据的接口")
print("  资金流数据可能需要使用其他库 (如 akshare, tushare 等)")
