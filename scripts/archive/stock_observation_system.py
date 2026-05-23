#!/usr/bin/env python3
"""
股票板块观测系统 - 自动数据更新脚本
用于每日自动获取涨停板数据并更新Obsidian笔记
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os

# Obsidian笔记路径
OBSIDIAN_PATH = r"V:\psy\psy\stock"
MONTH_FILE = os.path.join(OBSIDIAN_PATH, "5月.md")
TEMPLATE_FILE = os.path.join(OBSIDIAN_PATH, "每日观察模板.md")

def get_trading_date(offset=0):
    """获取交易日期字符串 (YYYYMMDD格式)"""
    date = datetime.now() - timedelta(days=offset)
    return date.strftime("%Y%m%d")

def get_limit_up_data(date_str):
    """获取指定日期的涨停板数据"""
    try:
        df = ak.stock_zt_pool_em(date=date_str)
        return df
    except Exception as e:
        print(f"获取 {date_str} 数据失败: {e}")
        return None

def analyze_sector_flow(df_today, df_yesterday=None, df_day_before=None):
    """分析板块资金流向"""
    if df_today is None or '所属行业' not in df_today.columns:
        return None
    
    # 今日板块统计
    today_sectors = df_today['所属行业'].value_counts().to_dict()
    
    result = {
        'date': df_today['所属行业'].index[0] if len(df_today) > 0 else '',
        'total_limit_up': len(df_today),
        'sector_counts': today_sectors,
        'top_sectors': []
    }
    
    # TOP10板块
    for sector, count in sorted(today_sectors.items(), key=lambda x: x[1], reverse=True)[:10]:
        result['top_sectors'].append({'sector': sector, 'count': count})
    
    return result

def generate_daily_markdown(date_str, analysis):
    """生成每日观察的Markdown内容"""
    date_obj = datetime.strptime(date_str, "%Y%m%d")
    date_display = date_obj.strftime("%Y-%m-%d")
    weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date_obj.weekday()]
    
    md = f"\n\n### {date_display} ({weekday})\n"
    md += f"**市场概况**: 涨停{analysis['total_limit_up']}只，情绪[待评估]\n"
    md += f"**关键事件**: (待填写)\n\n"
    md += "---\n\n"
    md += "#### 板块资金流向 (3日对比)\n"
    md += "| 板块 | D-2 | D-1 | 今日 | 趋势 | 综合得分 | 判断 |\n"
    md += "|------|-----|-----|------|------|---------|------|\n"
    md += "| (待数据) |  |  |  |  |  |  |\n\n"
    md += "**新崛起板块** (需观察2-3天)\n"
    md += "- (待填写)\n\n"
    md += "**衰退板块**\n"
    md += "- (待填写)\n\n"
    md += "---\n\n"
    md += "#### 连板梯队\n"
    md += "- (待填写)\n\n"
    md += "---\n\n"
    md += "#### 个股观察\n\n"
    md += "**符合选股标准 (≤100元+国企+MA20偏离率低)**\n"
    md += "1. (待填写)\n\n"
    md += "**观察但不符合标准**\n"
    md += "- (待填写)\n\n"
    md += "---\n\n"
    md += "#### 操作记录\n"
    md += "- [ ] 观察: (待填写)\n\n"
    md += "---\n\n"
    md += "#### 预测 (用于验证观察系统有效性)\n"
    md += "- 预测明日: (待填写)\n"
    md += "- 验证前日预测: (待验证)\n\n"
    
    return md

def main():
    print("=== 股票板块观测系统 ===\n")
    
    # 获取今日数据
    today_str = get_trading_date(0)
    print(f"正在获取 {today_str} 的涨停板数据...")
    df_today = get_limit_up_data(today_str)
    
    if df_today is None:
        print("获取数据失败，程序退出")
        return
    
    # 分析数据
    analysis = analyze_sector_flow(df_today)
    
    if analysis:
        print(f"\n今日涨停: {analysis['total_limit_up']}只")
        print(f"\nTOP5板块:")
        for i, item in enumerate(analysis['top_sectors'][:5]):
            print(f"  {i+1}. {item['sector']}: {item['count']}只")
        
        # 生成Markdown
        md_content = generate_daily_markdown(today_str, analysis)
        
        print(f"\n生成的Markdown内容已准备好，可以手动复制到 {MONTH_FILE}")
        print("\n" + "="*60)
        print(md_content)
        print("="*60)
        
        # 可选：自动写入文件（需要解析现有文件结构）
        # with open(MONTH_FILE, 'a', encoding='utf-8') as f:
        #     f.write(md_content)
        # print(f"\n✅ 已追加到 {MONTH_FILE}")
        
        print("\n💡 提示: 由于Obsidian文件格式复杂，建议手动复制上述内容到笔记中")
        print("   或运行带有 --auto-write 参数的版本（需先手动指定插入位置）")

if __name__ == "__main__":
    main()
