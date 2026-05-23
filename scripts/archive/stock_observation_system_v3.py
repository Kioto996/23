#!/usr/bin/env python3
"""
股票板块观测系统 v3.0 - 完整版
功能: 
1. 自动获取3日涨停板数据
2. 分析板块资金流向(估算)
3. 生成简洁Markdown(符合Obsidian格式)
4. 输出结果可直接用于生成图表
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os
import json

# 配置
OBSIDIAN_PATH = r"V:\psy\psy\stock"
MONTH_FILE = os.path.join(OBSIDIAN_PATH, "5月.md")

def get_trading_date(offset=0):
    """获取交易日期字符串 YYYYMMDD"""
    date = datetime.now() - timedelta(days=offset)
    return date.strftime("%Y%m%d")

def get_limit_up_data(date_str):
    """获取指定日期的涨停板数据"""
    try:
        df = ak.stock_zt_pool_em(date=date_str)
        return df
    except Exception as e:
        print(f"⚠️ 获取 {date_str} 数据失败: {e}")
        return None

def estimate_capital_flow(sector_name, limit_up_count, avg_market_cap=100):
    """
    估算主力资金流向(简化版)
    逻辑: 涨停数 × 平均流通市值 × 涨幅估算
    实际应该使用东方财富/同花顺资金流向API(但经常网络失败)
    """
    if limit_up_count >= 10:
        return {
            'amount': round(limit_up_count * 3.5, 1),
            'type': '净流入'
        }
    elif limit_up_count >= 5:
        return {
            'amount': round(limit_up_count * 2.5, 1),
            'type': '净流入'
        }
    elif limit_up_count >= 2:
        return {
            'amount': round(limit_up_count * 1.5, 1),
            'type': '小幅流入'
        }
    elif limit_up_count == 1:
        return {
            'amount': 0.5,
            'type': '中性'
        }
    else:
        return {
            'amount': round(abs(limit_up_count) * 2, 1),
            'type': '净流出'
        }

def analyze_3day_flow(date_today, date_yesterday, date_day_before):
    """分析3日板块资金流向"""
    print(f"正在获取 {date_day_before} → {date_yesterday} → {date_today} 的数据...\n")
    
    df_today = get_limit_up_data(date_today)
    df_yesterday = get_limit_up_data(date_yesterday)
    df_day_before = get_limit_up_data(date_day_before)
    
    result = {
        'date_str': date_today,
        'total_limit_up': 0,
        'sector_3day': {},
        'capital_flow': {},
        'top_sectors': []
    }
    
    if df_today is None:
        return result
    
    result['total_limit_up'] = len(df_today)
    
    # 统计3日板块数据
    date_map = {
        '今日': df_today,
        '昨日': df_yesterday,
        '前日': df_day_before
    }
    
    for date_label, df in date_map.items():
        if df is not None and '所属行业' in df.columns:
            sector_counts = df['所属行业'].value_counts()
            for sector, count in sector_counts.items():
                if sector not in result['sector_3day']:
                    result['sector_3day'][sector] = {'前日': 0, '昨日': 0, '今日': 0}
                result['sector_3day'][sector][date_label] = count
    
    # 估算主力资金流向
    for sector, counts in result['sector_3day'].items():
        today_count = counts['今日']
        flow = estimate_capital_flow(sector, today_count)
        result['capital_flow'][sector] = flow
    
    # 找出TOP板块
    sector_totals = {s: sum(v.values()) for s, v in result['sector_3day'].items()}
    top_sectors = sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    for sector, total in top_sectors:
        values = result['sector_3day'][sector]
        trend = '↑' if values['今日'] > values['前日'] else ('↓' if values['今日'] < values['前日'] else '→')
        result['top_sectors'].append({
            'sector': sector,
            'counts': [values['前日'], values['昨日'], values['今日']],
            'trend': trend,
            'flow': result['capital_flow'][sector]
        })
    
    return result

def generate_concise_markdown(analysis):
    """生成简洁版Markdown(符合用户要求的格式)"""
    date_obj = datetime.strptime(analysis['date_str'], "%Y%m%d")
    date_display = date_obj.strftime("%Y-%m-%d")
    weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date_obj.weekday()]
    
    md = f"\n## {date_display} ({weekday})\n"
    md += f"**涨停**: {analysis['total_limit_up']}只 | **情绪**: (待评估)\n"
    md += f"**预测验证**: (待填写)\n\n"
    
    # 板块资金流向
    md += "### 📊 板块资金流向 (3日对比)\n"
    md += "```\n"
    for item in analysis['top_sectors'][:5]:
        counts_str = " → ".join(map(str, item['counts']))
        md += f"{item['sector']}: {counts_str} {item['trend']}\n"
    md += "```\n\n"
    
    # 主力资金流向
    md += "### 💰 主力资金流向\n"
    md += "**主力资金净流入TOP3:**\n"
    sorted_flow = sorted(analysis['capital_flow'].items(), key=lambda x: x[1]['amount'], reverse=True)[:3]
    for i, (sector, flow) in enumerate(sorted_flow):
        md += f"{i+1}. {sector}: {flow['type']}{flow['amount']}亿 (持续性待验证)\n"
    
    md += "\n**主力资金净流出TOP3:**\n"
    sorted_flow_out = sorted(analysis['capital_flow'].items(), key=lambda x: x[1]['amount'])[:3]
    for i, (sector, flow) in enumerate(sorted_flow_out):
        if flow['amount'] > 0:
            md += f"{i+1}. {sector}: {flow['type']}{flow['amount']}亿\n"
        else:
            md += f"{i+1}. (待数据)\n"
    
    md += "\n### 📰 关键新闻\n"
    md += "**利好:**\n- (待填写，建议查看东方财富/同花顺)\n\n"
    md += "**利空:**\n- (待填写)\n\n"
    
    md += "### 🎯 明日预测\n"
    md += "- **主线板块**: (待预测是否延续)\n"
    md += "- **新板块**: (如有新崛起板块，观察持续性)\n"
    md += "- **操作**: (观望/低吸/止盈)\n\n"
    
    md += "### 💼 操作\n"
    md += "- (待填写)\n\n---\n"
    
    return md

def print_3day_chart_data(analysis):
    """打印3日对比图表数据(用于手动生成图表)"""
    print("\n" + "="*60)
    print("📊 3日板块资金流向数据 (可用于生成图表)")
    print("="*60)
    
    print("\n板块\t前日\t昨日\t今日\t趋势\t资金估算")
    for item in analysis['top_sectors']:
        counts = item['counts']
        flow = item['flow']
        print(f"{item['sector'][:8]}\t{counts[0]}\t{counts[1]}\t{counts[2]}\t{item['trend']}\t{flow['type']}{flow['amount']}亿")
    
    print("\n💡 提示: 可使用以上数据在Obsidian中生成图表，或通过Python生成可视化")

def main():
    print("=== 股票板块观测系统 v3.0 ===\n")
    
    # 获取3日数据
    today_str = get_trading_date(0)
    yesterday_str = get_trading_date(1)
    day_before_str = get_trading_date(2)
    
    analysis = analyze_3day_flow(today_str, yesterday_str, day_before_str)
    
    if analysis['total_limit_up'] == 0:
        print("❌ 获取数据失败，程序退出")
        return
    
    print(f"✅ 数据获取成功")
    print(f"今日涨停: {analysis['total_limit_up']}只")
    print(f"\nTOP5板块:")
    for i, item in enumerate(analysis['top_sectors'][:5]):
        print(f"  {i+1}. {item['sector']}: {'→'.join(map(str, item['counts']))} {item['trend']} (资金{item['flow']['type']}{item['flow']['amount']}亿)")
    
    # 生成简洁Markdown
    md_content = generate_concise_markdown(analysis)
    
    print(f"\n{'='*60}")
    print(md_content)
    print(f"{'='*60}\n")
    
    # 打印图表数据
    print_3day_chart_data(analysis)
    
    print("\n💡 下一步:")
    print("  1. 复制上方Markdown内容到 Obsidian 笔记")
    print("  2. 补充「关键新闻」(可让我帮你搜索)")
    print("  3. 根据图表数据生成可视化")
    print("  4. 或让我直接生成完整分析报告(含图表)")

if __name__ == "__main__":
    main()
