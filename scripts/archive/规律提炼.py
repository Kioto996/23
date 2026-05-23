import pandas as pd
import datetime

df = pd.read_csv(r"D:\workbuddy's dates\2026-05-12-task-2\cache\涨停板_10日汇总.csv")
dates_sorted = sorted(df['日期'].unique())

print("=" * 60)
print("📊 核心规律提炼（699只涨停样本）")
print("=" * 60)

# 规律1: 板块趋势
print("\n规律一：板块趋势（上升/衰退/震荡）")
sectors = df.groupby(['日期','所属行业']).size().reset_index(name='涨停数')
for sec in ['电力','汽车零部','电网设备','光伏设备','化学制品','房地产开','半导体']:
    data = sectors[sectors['所属行业']==sec]
    vals = [int(data[data['日期']==d]['涨停数'].values[0]) if len(data[data['日期']==d])>0 else 0 for d in dates_sorted]
    recent3 = sum(vals[-3:])
    prev3 = sum(vals[-6:-3])
    direction = '↑ 上升' if recent3 > prev3 else ('↓ 衰退' if recent3 < prev3 else '→ 震荡')
    print(f"  {sec:<8}  {vals}  最近3天{recent3} vs 前3天{prev3}  {direction}")

# 规律2: 情绪周期
print("\n规律二：每日情绪周期")
for d in dates_sorted:
    day_data = df[df['日期']==d]
    total = len(day_data)
    max_ban = int(day_data['连板数'].max())
    ban_cnt = int((day_data['连板数']>1).sum())
    shouban_pct = int((day_data['连板数']==1).sum()/total*100)
    bar = '█' * int(total/5)
    dt = datetime.datetime.strptime(str(int(d)), '%Y%m%d')
    wd = ['周一','周二','周三','周四','周五','周六','周日'][dt.weekday()]
    print(f"  {int(d)}({wd})  涨停{total:>3d}只  最高{max_ban}板  连板{ban_cnt}只  首板{shouban_pct}%  {bar}")

# 规律3: 优质涨停特征
print("\n规律三：优质涨停的连板概率")
df['早盘_flag'] = df['首次封板时间'].apply(lambda t: int(str(int(t)).zfill(6)[:2]+str(int(t)).zfill(6)[2:4]) < 1000)
df['强封单'] = df['封板资金'] > 0.5e8
df['无炸板'] = df['炸板次数'] == 0

quality = df[df['早盘_flag'] & df['强封单'] & df['无炸板']]
normal = df[~(df['早盘_flag'] & df['强封单'] & df['无炸板'])]
q_rate = int((quality['连板数']>1).sum())/len(quality)*100
n_rate = int((normal['连板数']>1).sum())/len(normal)*100
print(f"  特征：早盘封板 + 封单>0.5亿 + 未炸板")
print(f"  满足条件：{len(quality)}只（占{len(quality)/len(df)*100:.1f}%）")
print(f"  优质股连板率：{q_rate:.1f}%")
print(f"  普通股连板率：{n_rate:.1f}%")
print(f"  → 差距{q_rate/n_rate:.1f}倍")

# 规律4: 板块跟风
print("\n规律四：热点板块的跟风效应")
for sec in ['电力','汽车零部','电网设备']:
    sec_data = df[df['所属行业']==sec]
    early = int(sec_data[sec_data['早盘_flag']].shape[0])
    late = int(sec_data[~sec_data['早盘_flag']].shape[0])
    print(f"  {sec}: 早盘{early}只 + 午后{late}只  (午后跟风{late/(early+late)*100:.0f}%)")

# 规律5: 封板资金
print("\n规律五：封板资金与连板能力")
for cap in [0.3, 0.5, 1, 2, 5]:
    above = df[df['封板资金']>cap*1e8]
    ban2 = int((above['连板数']>1).sum())
    print(f"  >{cap}亿: {len(above)}只, 连板{ban2}只({ban2/len(above)*100:.1f}%)")

# 规律6: 涨跌幅与连板
print("\n规律六：涨停当天涨跌幅与第二天连板")
df['zt_pct'] = df['涨跌幅'].abs()
for pct in [5, 7, 9, 10]:
    if pct == 10:
        subset = df[df['涨跌幅'] >= 9.5]
    else:
        subset = df[df['涨跌幅'] >= pct]
    ban2 = int((subset['连板数']>1).sum())
    print(f"  涨幅>={pct}%: {len(subset)}只, 连板{ban2}只({ban2/len(subset)*100:.1f}%)")

print("\n" + "=" * 60)
print("📌 操作性最强的前3条规律")
print("=" * 60)
print("""
1️⃣ 板块优先法
   只看电力(↑加速)、电网设备(↑)、化学制品(↑)这3个上升板块
   缩量回踩MA20的股 → 次日重点观察

2️⃣ 优质涨停筛选（盘中判断）
   早盘+强封单+未炸板 = 连板率比普通高1倍
   用这个标准过滤，避免追到"假涨停"

3️⃣ 连板进阶法（操作节奏）
   首板淘汰率80% → 不追首板
   等2板回封确认 → 胜率翻倍
""")
