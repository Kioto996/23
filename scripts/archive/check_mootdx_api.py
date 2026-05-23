#!/usr/bin/env python3
"""
快速测试 mootdx 的实际功能
"""
import mootdx
from mootdx.quotes import Quotes
import inspect

print("Mootdx 版本:", mootdx.__version__)
print("\n" + "="*60)

# 查看 StdQuotes 实例的方法
print("\n[测试] 创建 Quotes 实例并查看方法...")
try:
    # 不连接服务器，直接查看 StdQuotes 类的方法
    from mootdx.quotes import StdQuotes
    methods = [m for m in dir(StdQuotes) if not m.startswith('_')]
    print(f"\nStdQuotes 类的方法 ({len(methods)}个):")
    for i, m in enumerate(methods, 1):
        print(f"  {i:2d}. {m}")
        
    # 查看每个方法的文档字符串
    print("\n" + "="*60)
    print("详细方法列表:")
    print("="*60)
    for m in methods:
        try:
            method = getattr(StdQuotes, m)
            doc = method.__doc__ if method.__doc__ else "无文档"
            print(f"\n{m}:\n  {doc[:100]}...")
        except:
            pass
            
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("结论:")
print("="*60)
print("Mootdx 主要用于:")
print("  1. 获取实时行情 (stocks)")
print("  2. 获取K线数据 (bars)")
print("  3. 获取指数数据 (index)")
print("\n⚠️  Mootdx 可能没有直接获取资金流数据的接口")
print("   资金流数据需要其他方式获取")
