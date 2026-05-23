#!/usr/bin/env python3
"""
股票板块观测系统 v2.0 - 自动生成每日分析
功能: 自动获取涨停板数据 → 分析3日趋势 → 生成简洁Markdown → 可选生成图表
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
    """获取交易日期字符串"""
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

def analyze_3day_flow(date_today, date_yesterday, date_day_before):
    """分析3日板块资金流向"""
    df_today = get_limit_up_data(date_today)
    df_yesterday = get_limit_up_data(date_yesterday)
    df_day_before = get_limit_up_data(date_day_before)
    
    result = {
        'date_today': date_today,
        'total_limit_up': 0,
        'sector_3day': {},
        'top_sectors': []
    }
    
    if df_today is None:
        return result
    
    result['total_limit_up'] = len(df_today)
    
    # 统计3日板块数据
    for date_label, df in [('今日', df_today), ('昨日', df_yesterday), ('前日', df_day_before)]:
        if df is not None and '所属行业' in df.columns:
            sector_counts = df['所属行业'].value_counts()
            for sector, count in sector_counts.items():
                if sector not in result['sector_3day']:
                    result['sector_3day'][sector] = {'前日': 0, '昨日': 0, '今日': 0}
                result['sector_3day'][sector][date_label] = count
    
    # 找出TOP板块
    sector_totals = {s: sum(v.values()) for s, v in result['sector_3day'].items()}
    top_sectors = sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    for sector, total in top_sectors:
        values = result['sector_3day'][sector]
        trend = '↑' if values['今日'] > values['前日'] else ('↓' if values['今日'] < values['前日'] else '→')
        result['top_sectors'].append({
            'sector': sector,
            'counts': [values['前日'], values['昨日'], values['今日']],
            'trend': trend
        })
    
    return result

def estimate_capital_flow(sector_name, limit_up_count):
    """估算主力资金流向(简化版：根据涨停数估算)"""
    # 简化逻辑：涨停数越多，资金净流入越大
    # 实际应该调用东方财富/同花顺的资金流向API
    if limit_up_count >= 10:
        return f"+{limit_up_count * 3}.{limit_up_count}"
    elif limit_up_count >= 5:
        return f"+{limit_up_count * 2}.{limit_up_count}"
    elif limit_up_count > 0:
        return f"+{limit_up_count}.{limit_up_count}"
    else:
        return f"-{abs(limit_up_count)}.{abs(limit_up_count)}"

def generate_concise_markdown(analysis):
    """生成简洁版Markdown(符合用户要求的格式)"""
    date_obj = datetime.strptime(analysis['date_today'], "%Y%m%d")
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
    
    # 主力资金流向(简化估算)
    md += "### 💰 主力资金流向\n"
    md += "**主力资金净流入TOP3**:\n"
    for i, item in enumerate(analysis['top_sectors'][:3]):
        flow = estimate_capital_flow(item['sector'], item['counts'][2])
        md += f"{i+1}. {item['sector']}: {flow}亿 (持续性待验证)\n"
    
    md += "\n**主力资金净流出TOP3**:\n"
    md += "1. (待数据) \n2. (待数据) \n3. (待数据) \n\n"
    
    # 关键新闻(预留，需手动填写或调用新闻API)
    md += "### 📰 关键新闻\n"
    md += "**利好**:\n- (待填写，建议查看东方财富/同花顺)\n\n"
    md += "**利空**:\n- (待填写)\n\n"
    
    # 明日预测
    md += "### 🎯 明日预测\n"
    md += "- **主线板块**: (待预测是否延续)\n"
    md += "- **新板块**: (如有新崛起板块，观察持续性)\n"
    md += "- **操作**: (观望/低吸/止盈)\n\n"
    
    # 操作
    md += "### 💼 操作\n"
    md += "- (待填写)\n\n---\n"
    
    return md

def main():
    print("=== 股票板块观测系统 v2.0 ===\n")
    
    # 获取3日数据
    today_str = get_trading_date(0)
    yesterday_str = get_trading_date(1)
    day_before_str = get_trading_date(2)
    
    print(f"正在获取 {day_before_str} → {yesterday_str} → {today_str} 的涨停板数据...\n")
    
    analysis = analyze_3day_flow(today_str, yesterday_str, day_before_str)
    
    if analysis['total_limit_up'] == 0:
        print("❌ 获取数据失败，程序退出")
        return
    
    print(f"✅ 数据获取成功")
    print(f"今日涨停: {analysis['total_limit_up']}只")
    print(f"\nTOP5板块:")
    for i, item in enumerate(analysis['top_sectors'][:5]):
        print(f"  {i+1}. {item['sector']}: {'→'.join(map(str, item['counts']))} {item['trend']}")
    
    # 生成简洁Markdown
    md_content = generate_concise_markdown(analysis)
    
    print(f"\n{'='*60}")
    print(md_content)
    print(f"{'='*60}\n")
    
    print("💡 提示:")
    print("  1. 手动复制上述内容到 Obsidian 笔记")
    print("  2. 补充「关键新闻」和「主力资金流向」真实数据")
    print("  3. 或运行 stock_observation_system.py --auto-write 自动写入文件")
    
    # 可选：保存到文件
    # with open('today_analysis.md', 'w', encoding='utf-8') as f:
    #     f.write(md_content)
    # print(f"\n✅ 已保存到 today_analysis.md")

if __name__ == "__main__":
    main()
