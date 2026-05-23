import akshare as ak
import pandas as pd
from datetime import datetime
import json

print("=== 主力资金板块进驻深度分析 ===\n")

# 获取3日数据
dates = ['20260512', '20260513', '20260514']
date_labels = ['5/12', '5/13', '5/14']

all_data = {}
sector_stocks = {}  # 保存每个板块的个股信息

for i, date in enumerate(dates):
    try:
        df = ak.stock_zt_pool_em(date=date)
        
        # 找到行业列
        sector_col = None
        for col in df.columns:
            if '行' in col or '板' in col or '概' in col:
                sector_col = col
                break
        
        if sector_col and sector_col in df.columns:
            # 统计板块涨停数
            sector_counts = df[sector_col].value_counts()
            all_data[date_labels[i]] = sector_counts.to_dict()
            
            # 保存个股信息
            for _, row in df.iterrows():
                sector = row[sector_col]
                stock_name = row.get('名称', row.get('name', 'Unknown'))
                stock_code = row.get('代码', row.get('code', 'Unknown'))
                
                if sector not in sector_stocks:
                    sector_stocks[sector] = {}
                if date_labels[i] not in sector_stocks[sector]:
                    sector_stocks[sector][date_labels[i]] = []
                
                sector_stocks[sector][date_labels[i]].append({
                    'name': stock_name,
                    'code': stock_code,
                    'price': row.get('最新价', row.get('price', 0)),
                    'limit_pct': row.get('涨跌幅', row.get('change_pct', 0))
                })
        else:
            print(f"警告: {date} 未找到行业列")
            all_data[date_labels[i]] = {}
            
    except Exception as e:
        print(f"获取 {date} 数据失败: {e}")
        all_data[date_labels[i]] = {}

# 分析主力板块
print("\n=== 主力资金进驻板块识别 ===\n")

# 计算综合得分：总涨停数 + 连续性 + 增长趋势
sector_scores = []
all_sectors = set()
for date in all_data:
    all_sectors.update(all_data[date].keys())

for sector in all_sectors:
    scores = []
    for date in date_labels:
        scores.append(all_data[date].get(sector, 0))
    
    total = sum(scores)
    # 连续性加分：3天都有涨停
    continuity = sum(1 for s in scores if s > 0)
    # 趋势加分：最后一天相比第一天增长
    trend_bonus = 1 if scores[2] >= scores[0] else 0
    
    final_score = total + continuity * 2 + trend_bonus * 3
    
    if total > 0:
        sector_scores.append({
            'sector': sector,
            'scores': scores,
            'total': total,
            'continuity': continuity,
            'final_score': final_score
        })

# 按得分排序
sector_scores.sort(key=lambda x: x['final_score'], reverse=True)

print("排名\t板块\t\t5/12\t5/13\t5/14\t总分\t连续性\t综合得分")
print("-" * 80)
for i, item in enumerate(sector_scores[:15]):
    sector_name = str(item['sector'])[:10]  # 确保是字符串
    scores_str = '\t'.join(map(str, item['scores']))
    print(f"{i+1}\t{sector_name}\t\t{scores_str}\t{item['total']}\t{item['continuity']}\t{item['final_score']:.1f}")

# 重点分析TOP5板块
print("\n\n=== TOP5 主力板块详细分析 ===\n")

for i, item in enumerate(sector_scores[:5]):
    sector = item['sector']
    print(f"\n【{i+1}】{sector} (综合得分: {item['final_score']:.1f})")
    print(f"  涨停数量: {'→'.join(map(str, item['scores']))}")
    
    # 显示每天的个股
    if sector in sector_stocks:
        for date in date_labels:
            if date in sector_stocks[sector]:
                stocks = sector_stocks[sector][date]
                print(f"  {date}: {', '.join([s['name'] for s in stocks[:5]])}" + ('...' if len(stocks) > 5 else ''))

# 新崛起板块识别
print("\n\n=== 新崛起板块 (5/14首次出现) ===\n")
new_sectors = []
for sector in all_sectors:
    scores = [all_data[date].get(sector, 0) for date in date_labels]
    if scores[2] >= 2 and scores[0] == 0 and scores[1] == 0:
        new_sectors.append({'sector': sector, 'count': scores[2]})

if new_sectors:
    for item in new_sectors:
        print(f"★ {item['sector']}: {item['count']}只涨停 (5/14新崛起)")
        if item['sector'] in sector_stocks and '5/14' in sector_stocks[item['sector']]:
            stocks = sector_stocks[item['sector']]['5/14']
            print(f"  个股: {', '.join([s['name'] for s in stocks])}")
else:
    print("无新崛起板块（5/14无首次出现的板块）")

# 衰退板块识别
print("\n\n=== 衰退板块 (5/14明显萎缩) ===\n")
declining = []
for sector in all_sectors:
    scores = [all_data[date].get(sector, 0) for date in date_labels]
    if scores[0] >= 2 and scores[2] == 0:
        declining.append({'sector': sector, 'peak': max(scores)})

for item in declining[:5]:
    print(f"▼ {item['sector']}: 峰值{item['peak']}只 → 5/14归零")

print("\n\n=== 投资建议 ===")
print("1. 主力持续板块: ", [item['sector'] for item in sector_scores[:3]])
print("2. 新崛起板块: ", [item['sector'] for item in new_sectors])
print("3. 建议: 关注主力持续板块的回调机会，谨慎对待新崛起板块（需验证持续性）")
