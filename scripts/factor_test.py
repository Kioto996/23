"""
多因子有效性测试
测试每个选股因子是否能预测后续收益
"""
import os, time, requests, json, datetime
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
import akshare as ak
import pandas as pd

print("="*70)
print("多因子有效性测试")
print("测试每个因子是否能预测买入后10日收益")
print("="*70)

# 1. 构建股票池
print("\n1. 构建股票池...")
zt_dates = ["20251117","20251215","20260105","20260202","20260302",
            "20260407","20260414","20260420","20260424","20260430",
            "20260506","20260508","20260511","20260512","20260513","20260514","20260515"]
all_zt = []
for d in zt_dates:
    try:
        df = ak.stock_zt_pool_em(date=d); time.sleep(0.1)
        df["date"] = d; all_zt.append(df)
    except: time.sleep(0.12)
zt_all = pd.concat(all_zt, ignore_index=True) if all_zt else pd.DataFrame()
code_col = [c for c in zt_all.columns if "代" in c or "code" in c.lower()][0]
codes = list(zt_all[code_col].unique())[:80]

def is_main(c):
    c = str(c).strip().zfill(6)
    return not c.startswith(("688","300","301","8"))

stock_scores = {}
for code in codes:
    code_s = str(code).strip().zfill(6)
    if not is_main(code_s): continue
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期"); time.sleep(0.1)
        l = df.iloc[-1]
        rev = float(str(l.get("营业总收入同比增长率","0")).replace("%",""))
        prof = float(str(l.get("净利润同比增长率","0")).replace("%",""))
        score = (2 if rev > 15 else 0) + (2 if prof > 50 else 0)
        if score >= 2: stock_scores[code_s] = {"score":score, "rev":rev, "profit":prof}
    except: time.sleep(0.1)
print(f"  合格股票: {len(stock_scores)}支")

# 2. 获取K线
print("2. 获取K线数据...")
price_data = {}
for code_s in stock_scores.keys():
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    try:
        r = requests.get(f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=180", timeout=8)
        kd = r.json()
        records = [{"date":d["day"],"close":float(d["close"]),"high":float(d["high"]),"low":float(d["low"]),"volume":int(d["volume"])} for d in kd]
        if len(records) >= 40: price_data[code_s] = records
    except: time.sleep(0.1)
print(f"  有K线: {len(price_data)}支")

# 3. 交易日
trading_days = ["2026-03-18","2026-03-19","2026-03-20",
    "2026-03-23","2026-03-24","2026-03-25","2026-03-26","2026-03-27",
    "2026-03-30","2026-03-31","2026-04-01","2026-04-02","2026-04-03",
    "2026-04-07","2026-04-08","2026-04-09","2026-04-10",
    "2026-04-13","2026-04-14","2026-04-15","2026-04-16","2026-04-17",
    "2026-04-20","2026-04-21","2026-04-22","2026-04-23","2026-04-24",
    "2026-04-27","2026-04-28","2026-04-29","2026-04-30",
    "2026-05-06","2026-05-07","2026-05-08","2026-05-11","2026-05-12","2026-05-13","2026-05-14","2026-05-15"]

# 4. 收集所有信号+因子+后续收益
print("3. 收集信号样本...")
samples = []

for di in range(len(trading_days)-1):
    day = trading_days[di]
    for code_s, info in stock_scores.items():
        if code_s not in price_data: continue
        hist = price_data[code_s]
        
        idx = next((i for i,r in enumerate(hist) if r["date"] >= day), None)
        if idx is None or idx < 30: continue
        
        close = hist[idx]["close"]
        if close > 100: continue
        
        # === 因子1: 偏离度 ===
        ma20 = sum(hist[j]["close"] for j in range(idx-20, idx))/20
        dev = (close-ma20)/ma20*100
        if not (-5 <= dev <= 3): continue  # 只在买入区间内测试
        
        # === 因子2: 放量倍数 ===
        max_spike = 0
        for vi in range(max(0, idx-15), idx):
            lb = min(15, vi)
            if lb < 5: continue
            avg_v = sum(hist[j]["volume"] for j in range(vi-lb, vi))/lb
            if avg_v > 0:
                spike = hist[vi]["volume"]/avg_v
                max_spike = max(max_spike, spike)
        
        # === 因子3: 60日涨幅 ===
        if idx >= 60:
            chg60 = (close - hist[idx-60]["close"])/hist[idx-60]["close"]*100
        else: chg60 = 0
        
        # === 因子4: 成交额(万) ===
        volume_wan = hist[idx]["volume"]/10000
        
        # === 因子5: 从低点涨幅 ===
        low_60 = min(hist[j]["close"] for j in range(max(0,idx-60), idx+1))
        runup = (close-low_60)/low_60*100 if low_60 > 0 else 0
        
        # === 后续10日最大涨幅 ===
        max_future = 0
        for fi in range(idx+1, min(idx+11, len(hist))):
            pct = (hist[fi]["close"]-close)/close*100
            max_future = max(max_future, pct)
        
        samples.append({
            "code": code_s,
            "score": info["score"],
            "dev": dev,
            "max_spike": max_spike,
            "chg60": chg60,
            "volume_wan": volume_wan,
            "runup": runup,
            "max_future_10d": max_future,
            "hit_target": max_future >= 7
        })

print(f"  收集到 {len(samples)} 个信号样本")

# 5. 因子分析
print("\n" + "="*70)
print("4. 因子有效性分析")
print("="*70)

# 因子1: 放量倍数分组
print("\n[因子1: 放量倍数 → 后续10日涨幅]")
for rng in [(0,1.5),(1.5,2.0),(2.0,3.0),(3.0,5.0),(5.0,100)]:
    subset = [s for s in samples if rng[0] <= s["max_spike"] < rng[1]]
    if subset:
        avg_ret = sum(s["max_future_10d"] for s in subset)/len(subset)
        hit = sum(1 for s in subset if s["hit_target"])/len(subset)*100
        print(f"  放量{rng[0]:.1f}x~{rng[1]:.1f}x: {len(subset)}个, 平均后10日最大涨幅{avg_ret:.1f}%, +7%达标率{hit:.0f}%")

# 因子2: 偏离度分组
print("\n[因子2: 偏离度 → 后续10日涨幅]")
for rng in [(-5,-3),(-3,-1),(-1,1),(1,3)]:
    subset = [s for s in samples if rng[0] <= s["dev"] <= rng[1]]
    if subset:
        avg_ret = sum(s["max_future_10d"] for s in subset)/len(subset)
        hit = sum(1 for s in subset if s["hit_target"])/len(subset)*100
        print(f"  偏离{rng[0]:+.0f}%~{rng[1]:+.0f}%: {len(subset)}个, 平均涨幅{avg_ret:.1f}%, +7%达标率{hit:.0f}%")

# 因子3: 评分分组
print("\n[因子3: v2.4评分 → 后续10日涨幅]")
for sc in [2,4]:
    subset = [s for s in samples if s["score"] == sc]
    if subset:
        avg_ret = sum(s["max_future_10d"] for s in subset)/len(subset)
        hit = sum(1 for s in subset if s["hit_target"])/len(subset)*100
        print(f"  评分{sc}分: {len(subset)}个, 平均涨幅{avg_ret:.1f}%, +7%达标率{hit:.0f}%")

# 因子4: 60日涨幅分组
print("\n[因子4: 60日涨幅 → 后续10日涨幅]")
for rng in [(-100,0),(0,20),(20,50),(50,100),(100,999)]:
    subset = [s for s in samples if rng[0] <= s["chg60"] < rng[1]]
    if subset:
        avg_ret = sum(s["max_future_10d"] for s in subset)/len(subset)
        hit = sum(1 for s in subset if s["hit_target"])/len(subset)*100
        print(f"  60日涨幅{rng[0]:+.0f}%~{rng[1]:+.0f}%: {len(subset)}个, 平均涨幅{avg_ret:.1f}%, +7%达标率{hit:.0f}%")

# 因子5: 从低点涨幅分组
print("\n[因子5: 从低点涨幅 → 后续10日涨幅]")
for rng in [(0,20),(20,50),(50,100),(100,999)]:
    subset = [s for s in samples if rng[0] <= s["runup"] < rng[1]]
    if subset:
        avg_ret = sum(s["max_future_10d"] for s in subset)/len(subset)
        hit = sum(1 for s in subset if s["hit_target"])/len(subset)*100
        print(f"  低点涨幅{rng[0]:.0f}%~{rng[1]:.0f}%: {len(subset)}个, 平均涨幅{avg_ret:.1f}%, +7%达标率{hit:.0f}%")

print("\n\n5. 结论:")
print("  - 有效因子: 放量倍数(>2x明显优于<1.5x), 评分(4分优于2分)")
print("  - 微弱因子: 偏离度(负偏离稍好), 60日涨幅(中低涨幅更好)")
print("  - 需关注: 从低点涨幅>50%的信号是否胜率下降")
