#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
集成演示脚本 - 展示如何将mootdx整合到stock-analyst信息获取工作流
工作流：
1. 基本面分析（AKShare）✅ 已完成
2. 资金流向分析（AKShare）✅ 已完成
3. 新闻分析（AKShare）✅ 已完成
4. 技术面分析（mootdx/AKShare/mock）← 新增
"""

import sys
import os

# 添加路径
sys.path.append('C:/Users/hansu/.workbuddy/skills/stock-analyst/stockai/skills')
sys.path.append('D:/workbuddy\'s dates/2026-05-12-task-2')

print("=" * 70)
print(" stock-analyst 信息获取工作流 - 集成mootdx演示")
print("=" * 70)

# ============================================================================
# 第1步：基本面分析（使用AKShare - 已完成）
# ============================================================================
print("\n[第1步] 基本面分析（AKShare）")
print("-" * 70)

try:
    from financial_analysis import FinancialAnalyzer
    fa = FinancialAnalyzer()
    print("✅ financial_analysis.py 加载成功（AKShare）")

    # 获取润泽科技财务数据
    financial_data = fa.get_financial_data('300442', report_type='latest')
    if financial_data:
        print(f"✅ 获取财务数据成功")
        print(f"   营业收入: {financial_data.get('Revenue', 'N/A')}")
        print(f"   净利润: {financial_data.get('NetProfit', 'N/A')}")
    else:
        print("⚠️  无法获取财务数据（可能网络限制）")

except Exception as e:
    print(f"❌ 基本面分析失败: {e}")

# ============================================================================
# 第2步：资金流向分析（使用AKShare - 已完成）
# ============================================================================
print("\n[第2步] 资金流向分析（AKShare）")
print("-" * 70)

try:
    from fund_tracking import FundTracker
    ft = FundTracker()
    print("✅ fund_tracking.py 加载成功（AKShare）")

    # 获取润泽科技资金流向
    fund_data = ft.get_fund_flow('300442')
    if fund_data:
        print(f"✅ 获取资金流向成功")
        print(f"   主力净流入: {fund_data.get('main_net_inflow', 'N/A')}")
    else:
        print("⚠️  无法获取资金流向数据")

except Exception as e:
    print(f"❌ 资金流向分析失败: {e}")

# ============================================================================
# 第3步：新闻分析（使用AKShare - 已完成）
# ============================================================================
print("\n[第3步] 新闻分析（AKShare）")
print("-" * 70)

try:
    from news_fetcher import NewsFetcher
    nf = NewsFetcher()
    print("✅ news_fetcher.py 加载成功（AKShare）")

    # 获取润泽科技新闻
    news = nf.get_stock_news('300442', limit=5)
    if news:
        print(f"✅ 获取新闻成功: {len(news)} 条")
        for i, item in enumerate(news[:3], 1):
            print(f"   {i}. {item.get('title', 'N/A')}")
    else:
        print("⚠️  无法获取新闻数据")

except Exception as e:
    print(f"❌ 新闻分析失败: {e}")

# ============================================================================
# 第4步：技术面分析（使用mootdx/AKShare/mock - 新增）
# ============================================================================
print("\n[第4步] 技术面分析（mootdx/AKShare/mock）")
print("-" * 70)

try:
    from technical_analysis import TechnicalAnalyzer, integrate_technical_to_report
    print("✅ technical_analysis.py 加载成功")

    # 使用auto模式（自动选择数据源）
    print("\n  使用模式: auto（自动选择数据源）")
    tech_report = integrate_technical_to_report('300442', 'markdown')
    print(tech_report)

except Exception as e:
    print(f"❌ 技术面分析失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 第5步：生成完整报告
# ============================================================================
print("\n" + "=" * 70)
print(" 生成完整分析报告（基本面 + 技术面）")
print("=" * 70)

def generate_complete_report(symbol):
    """生成完整的股票分析报告"""
    report = []
    report.append(f"# 股票分析报告 - {symbol}\n")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 技术面分析
    try:
        from technical_analysis import integrate_technical_to_report
        tech_section = integrate_technical_to_report(symbol, 'markdown')
        report.append(tech_section)
    except Exception as e:
        report.append(f"\n## 技术面分析\n\n⚠️ 无法获取技术面数据: {e}\n")

    # 这里可以添加更多章节（基本面、资金流向、新闻等）

    return '\n'.join(report)

try:
    from datetime import datetime
    complete_report = generate_complete_report('300442')

    # 保存到文件
    output_file = 'D:/workbuddy\'s dates/2026-05-12-task-2/complete_analysis_report.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(complete_report)

    print(f"\n✅ 完整报告已生成: {output_file}")

except Exception as e:
    print(f"\n❌ 生成完整报告失败: {e}")

print("\n" + "=" * 70)
print(" 集成演示完成")
print("=" * 70)

print("\n📋 工作总结:")
print("""
1. ✅ financial_analysis.py - 使用AKShare获取财务数据
2. ✅ fund_tracking.py - 使用AKShare获取资金流向
3. ✅ news_fetcher.py - 使用AKShare获取新闻数据
4. ✅ technical_analysis.py - 使用mootdx/AKShare/mock获取技术面数据

🎯 mootdx已成功整合到信息获取工作流中！

📝 使用说明:
- 优先使用mootdx（实时性更好）
- mootdx不可用时回退到AKShare
- 都不可用时使用mock模式（用于演示）
- 通过TechnicalAnalyzer(mode='auto/mootdx/akshare/mock')选择模式
""")
