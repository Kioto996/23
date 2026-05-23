import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import json

# 获取过去3个交易日的涨停板数据
dates = ['20260512', '20260513', '20260514']

print("=== 过去3个交易日主力资金板块进驻分析 ===\n")

sector_data = {}

for date in dates:
    try:
        print(f"\n正在获取 {date} 涨停板数据...")
        df = ak.stock_zt_pool_em(date=date)
        
        # 按板块统计
        if '所属行业' in df.columns:
            sector_col = '所属行业'
        elif '板块' in df.columns:
            sector_col = '板块'
        elif '行业' in df.columns:
            sector_col = '行业'
        else:
            # 尝试找到行业相关列
            sector_col = None
            for col in df.columns:
                if '行' in col or '板' in col or '概' in col:
                    sector_col = col
                    break
        
        if sector_col and sector_col in df.columns:
            sector_counts = df[sector_col].value_counts()
            sector_data[date] = sector_counts.to_dict()
            
            print(f"\n{date} 涨停板块分布 (前10):")
            for sector, count in sector_counts.head(10).items():
                print(f"  {sector}: {count}只")
        else:
            print(f"  {date}: 未找到板块列，可用列: {df.columns.tolist()}")
            sector_data[date] = {}
            
    except Exception as e:
        print(f"获取 {date} 数据失败: {e}")
        sector_data[date] = {}

# 分析趋势
print("\n\n=== 板块资金进驻趋势分析 ===")
print("连续3日都有涨停的板块：")

all_sectors = set()
for date in sector_data:
    all_sectors.update(sector_data[date].keys())

trend_data = []
for sector in all_sectors:
    counts = []
    for date in dates:
        count = sector_data.get(date, {}).get(sector, 0)
        counts.append(count)
    
    if sum(counts) > 0:  # 至少有1天出现
        trend_data.append({
            'sector': sector,
            '5/12': counts[0],
            '5/13': counts[1],
            '5/14': counts[2],
            'total': sum(counts),
            'trend': '↑' if counts[2] > counts[0] else ('↓' if counts[2] < counts[0] else '→')
        })

# 按总涨停数排序
trend_data.sort(key=lambda x: x['total'], reverse=True)

print("\n板块\t5/12\t5/13\t5/14\t总计\t趋势")
print("-" * 60)
for item in trend_data[:20]:  # 显示前20个
    print(f"{item['sector'][:10]}\t{item['5/12']}\t{item['5/13']}\t{item['5/14']}\t{item['total']}\t{item['trend']}")

# 识别主力资金进驻板块
print("\n\n=== 主力资金进驻板块判断 ===")
print("标准：连续3日有涨停 + 涨停数量稳定或增长")

main_sectors = []
for item in trend_data:
    if item['5/12'] >= 2 and item['5/13'] >= 2:  # 至少2天有2+涨停
        main_sectors.append(item)
        print(f"✓ {item['sector']}: {item['5/12']}→{item['5/13']}→{item['5/14']} {item['trend']}")

print(f"\n结论：主力资金主要进驻 {len(main_sectors)} 个板块")
