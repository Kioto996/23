import akshare as ak
import pandas as pd

print("=== 过去3个交易日主力资金板块进驻分析 ===\n")

# 获取3日数据
dates = ['20260512', '20260513', '20260514']
date_labels = ['5/12', '5/13', '5/14']

all_data = {}
sector_stocks = {}  # 保存每个板块的个股信息

for i, date in enumerate(dates):
    try:
        print(f"正在获取 {date} 涨停板数据...")
        df = ak.stock_zt_pool_em(date=date)
        
        # 使用正确的列名
        sector_col = '所属行业'
        
        if sector_col in df.columns:
            # 统计板块涨停数
            sector_counts = df[sector_col].value_counts()
            all_data[date_labels[i]] = sector_counts.to_dict()
            
            print(f"\n{date_labels[i]} 涨停板块分布 (前10):")
            for sector, count in sector_counts.head(10).items():
                print(f"  {sector}: {count}只")
            
            # 保存个股信息
            for _, row in df.iterrows():
                sector = row[sector_col]
                stock_name = row['名称']
                stock_code = row['代码']
                
                if sector not in sector_stocks:
                    sector_stocks[sector] = {}
                if date_labels[i] not in sector_stocks[sector]:
                    sector_stocks[sector][date_labels[i]] = []
                
                sector_stocks[sector][date_labels[i]].append({
                    'name': stock_name,
                    'code': stock_code,
                    'price': row.get('最新价', 0),
                    'limit_pct': row.get('涨跌幅', 0),
                    'boards': row.get('连板数', 1)
                })
        else:
            print(f"警告: {date} 未找到'所属行业'列")
            print(f"可用列: {df.columns.tolist()}")
            all_data[date_labels[i]] = {}
            
    except Exception as e:
        print(f"获取 {date} 数据失败: {e}")
        import traceback
        traceback.print_exc()
        all_data[date_labels[i]] = {}

print("\n\n=== 板块资金进驻趋势分析 ===\n")

# 汇总所有板块
all_sectors = set()
for date in all_data:
    all_sectors.update(all_data[date].keys())

# 计算综合得分
sector_scores = []
for sector in all_sectors:
    scores = []
    for date in date_labels:
        count = all_data[date].get(sector, 0)
        scores.append(count)
    
    total = sum(scores)
    continuity = sum(1 for s in scores if s > 0)  # 连续性：几天有涨停
    trend = '↑' if scores[2] > scores[0] else ('↓' if scores[2] < scores[0] else '→')
    
    # 综合得分：总涨停数 + 连续性加分 + 趋势加分
    final_score = total + continuity * 3 + (3 if trend == '↑' else (0 if trend == '→' else -1))
    
    if total > 0:
        sector_scores.append({
            'sector': sector,
            'scores': scores,
            'total': total,
            'continuity': continuity,
            'trend': trend,
            'final_score': final_score
        })

# 按综合得分排序
sector_scores.sort(key=lambda x: x['final_score'], reverse=True)

print("排名\t板块\t\t5/12\t5/13\t5/14\t总计\t连续\t趋势\t得分")
print("-" * 90)
for i, item in enumerate(sector_scores[:20]):
    scores_str = '\t'.join(map(str, item['scores']))
    sector_name = item['sector'][:8]  # 截断过长名称
    print(f"{i+1}\t{sector_name}\t\t{scores_str}\t{item['total']}\t{item['continuity']}\t{item['trend']}\t{item['final_score']:.0f}")

# 主力板块识别
print("\n\n=== 主力资金进驻板块 (TOP10) ===\n")

for i, item in enumerate(sector_scores[:10]):
    sector = item['sector']
    print(f"\n【{i+1}】{sector} (综合得分: {item['final_score']:.0f})")
    print(f"  涨停数量: {'只 → '.join(map(str, item['scores']))}只")
    print(f"  趋势: {item['trend']} | 连续天数: {item['continuity']}/3")
    
    # 显示每天的个股（只显示前3只）
    if sector in sector_stocks:
        for date in date_labels:
            if date in sector_stocks[sector]:
                stocks = sector_stocks[sector][date]
                stock_names = [f"{s['name']}({s['boards']}板)" for s in stocks[:3]]
                more = f" 等{len(stocks)}只" if len(stocks) > 3 else ""
                print(f"  {date}: {', '.join(stock_names)}{more}")

# 新崛起板块
print("\n\n=== 新崛起板块 (5/14首次出现或明显加强) ===\n")
new_sectors = []
for item in sector_scores:
    scores = item['scores']
    # 5/14有涨停，且前两天都没有 或 5/14比前两天明显增多
    if scores[2] >= 2 and (scores[0] == 0 and scores[1] == 0):
        new_sectors.append(item)

if new_sectors:
    for item in new_sectors:
        print(f"★ {item['sector']}: {item['scores'][2]}只涨停 (5/14新崛起)")
else:
    print("无完全新崛起板块")
    print("（说明：资金仍在原有板块中轮动，未开启新主题）")

# 衰退板块
print("\n\n=== 衰退板块 (5/14涨停数归零或大幅减少) ===\n")
declining = []
for item in sector_scores:
    scores = item['scores']
    if scores[0] >= 2 and scores[2] == 0:  # 第一天有2+涨停，第三天归零
        declining.append(item)

if declining:
    for item in declining[:5]:
        print(f"▼ {item['sector']}: {scores[0]}只 → 0只 (衰退)")
else:
    print("无明确衰退板块（资金可能仍在板块内轮动）")

# 投资建议
print("\n\n=== 投资建议 ===\n")
print("1. 主力持续板块 (关注回调机会):")
for item in sector_scores[:3]:
    if item['continuity'] >= 2:
        print(f"   - {item['sector']}: {item['scores']} (综合得分{item['final_score']:.0f})")

print("\n2. 新崛起板块 (需验证持续性):")
if new_sectors:
    for item in new_sectors:
        print(f"   - {item['sector']}: {item['scores'][2]}只")
else:
    print("   - 无 (资金未开启新主题)")

print("\n3. 操作策略:")
print("   - 优先关注主力持续板块中MA20偏离率<15%的个股")
print("   - 等待回调而非追高")
print("   - 新崛起板块需观察2-3天确认持续性")
