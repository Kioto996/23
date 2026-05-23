import os, time, requests, json, datetime
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
import akshare as ak
import pandas as pd

print("="*70)
print("滚动回测：前一交易日信号→后一交易日验证")
print("周期：过去22个交易日 (2026/04/20 - 2026/05/18)")
print("="*70)

# 1. 构建股票池 (从6个月的涨停数据+ v2.4评分)
print("\n1. 构建股票池...")
zt_dates = ["20251117","20251215","20260105","20260202","20260302",
            "20260407","20260414","20260420","20260424","20260430",
            "20260506","20260508","20260511","20260512","20260513","20260514","20260515"]
all_zt = []
for d in zt_dates:
    try:
        df = ak.stock_zt_pool_em(date=d)
        time.sleep(0.12)
        df["date"] = d
        all_zt.append(df)
    except:
        time.sleep(0.15)

zt_all = pd.concat(all_zt, ignore_index=True) if all_zt else pd.DataFrame()
code_col = [c for c in zt_all.columns if "代" in c or "code" in c.lower()][0]
codes = list(zt_all[code_col].unique())[:80]

def is_main(c):
    c = str(c).strip().zfill(6)
    return not c.startswith(("688","300","301","8"))

# v2.4评分
stock_scores = {}
for code in codes:
    code_s = str(code).strip().zfill(6)
    if not is_main(code_s): continue
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期")
        time.sleep(0.12)
        l = df.iloc[-1]
        rev = float(str(l.get("营业总收入同比增长率","0")).replace("%",""))
        prof = float(str(l.get("净利润同比增长率","0")).replace("%",""))
        score = (2 if rev > 15 else 0) + (2 if prof > 50 else 0)
        if score >= 2:
            stock_scores[code_s] = {"score":score, "rev":rev, "profit":prof}
    except:
        time.sleep(0.12)

print(f"  合格股票: {len(stock_scores)}支")

# 2. 获取K线
print("\n2. 获取K线数据 (180日)...")
price_data = {}
for code_s in stock_scores.keys():
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=180"
    try:
        r = requests.get(url, timeout=8)
        kd = json.loads(r.text)
        records = []
        for d in kd:
            records.append({
                "date": d["day"], "close": float(d["close"]),
                "high": float(d["high"]), "low": float(d["low"]),
                "volume": int(d["volume"])
            })
        if len(records) >= 40:
            price_data[code_s] = records
    except:
        time.sleep(0.1)

print(f"  有K线数据: {len(price_data)}支")

# 3. 定义交易日序列 (过去22个交易日)
trading_days = [
    "2026-04-20","2026-04-21","2026-04-22","2026-04-23","2026-04-24",
    "2026-04-27","2026-04-28","2026-04-29","2026-04-30",
    "2026-05-06","2026-05-07","2026-05-08",
    "2026-05-11","2026-05-12","2026-05-13","2026-05-14","2026-05-15",
    "2026-05-18"
]
print(f"\n3. 共 {len(trading_days)} 个交易日")

# 4. 滚动回测 - 前一天信号→后一天验证
print("\n4. 滚动回测: 逐日检查信号...")
print("="*70)

all_signals = []  # 所有信号的记录

for di in range(len(trading_days)-1):
    signal_day = trading_days[di]       # 信号出现日 (买入日)
    verify_day = trading_days[di+1]     # 验证日
    
    day_signals = []
    
    for code_s, info in stock_scores.items():
        if code_s not in price_data: continue
        hist = price_data[code_s]
        
        # 找到信号日对应的K线索引
        sig_idx = None
        for i, rec in enumerate(hist):
            if rec["date"] >= signal_day:
                sig_idx = i
                break
        if sig_idx is None or sig_idx < 25: continue
        
        # === 只使用信号日及之前的数据 ===
        price = hist[sig_idx]["close"]
        if price > 100: continue
        
        # MA20 (基于信号日前20日)
        ma20 = sum(hist[j]["close"] for j in range(sig_idx-20, sig_idx)) / 20
        dev = (price - ma20) / ma20 * 100
        
        if not (-5 <= dev <= 3): continue
        
        # 放量检查 (信号日前15日内)
        vol_break = False
        vol_ratio = 0
        for vi in range(max(0, sig_idx-15), sig_idx):
            lookback = min(15, vi)
            if lookback < 5: continue
            avg_v = sum(hist[j]["volume"] for j in range(vi-lookback, vi)) / lookback
            if avg_v > 0 and hist[vi]["volume"] > avg_v * 2:
                vol_break = True
                vol_ratio = hist[vi]["volume"] / avg_v
                break
        
        if not vol_break: continue
        
        # === 找到买入日和次日收盘 ===
        # 买入日收盘价
        buy_price = price
        
        # 次日收盘价 (验证日)
        verify_idx = None
        for i in range(sig_idx+1, min(sig_idx+11, len(hist))):
            if hist[i]["date"] >= verify_day:
                verify_idx = i
                break
        
        if verify_idx is None: continue
        verify_price = hist[verify_idx]["close"]
        
        # 检查10个交易日内是否达到+7%或-5%
        target = buy_price * 1.07
        stop = buy_price * 0.95
        hit_target = False
        hit_stop = False
        target_days = 0
        stop_days = 0
        max_chg = 0
        
        for li in range(sig_idx+1, min(sig_idx+11, len(hist))):
            pct = (hist[li]["close"] - buy_price) / buy_price * 100
            max_chg = max(max_chg, pct)
            if pct >= 7 and not hit_target:
                hit_target = True
                target_days = li - sig_idx
            if pct <= -5 and not hit_stop:
                hit_stop = True
                stop_days = li - sig_idx

        day_chg = (verify_price - buy_price) / buy_price * 100
        
        day_signals.append({
            "code": code_s, "score": info["score"],
            "signal_date": signal_day, "buy_price": buy_price,
            "ma20": round(ma20,2), "dev": round(dev,1),
            "vol_ratio": round(vol_ratio,1),
            "verify_date": verify_day, "verify_price": verify_price,
            "day1_chg": round(day_chg,1),
            "hit_target": hit_target, "target_days": target_days,
            "hit_stop": hit_stop, "stop_days": stop_days,
            "max_chg_10d": round(max_chg,1),
            "result": "win" if hit_target else ("loss" if hit_stop else "flat")
        })
    
    all_signals.extend(day_signals)
    
    # 当日信号统计
    wins = sum(1 for s in day_signals if s["result"] == "win")
    losses = sum(1 for s in day_signals if s["result"] == "loss")
    flats = sum(1 for s in day_signals if s["result"] == "flat")
    
    if day_signals:
        signal_codes = ", ".join(f'{s["code"]}({s["dev"]:+.0f}%)' for s in day_signals)
        print(f"  {signal_day}→{verify_day}: {len(day_signals)}个信号 | {wins}胜{losses}负{flats}平 | {signal_codes}")

# 5. 综合分析
print("\n" + "="*70)
print("5. 滚动回测统计")
print("="*70)

total = len(all_signals)
wins = sum(1 for s in all_signals if s["result"] == "win")
losses = sum(1 for s in all_signals if s["result"] == "loss")
flats = sum(1 for s in all_signals if s["result"] == "flat")

print(f"  总信号数: {total}")
print(f"  胜: {wins} ({wins/total*100:.0f}%)")
print(f"  负: {losses} ({losses/total*100:.0f}%)")
print(f"  平: {flats} ({flats/total*100:.0f}%)")

# 按条件分析
print("\n\n6. 条件交叉分析:")
print("-"*70)

# 偏离度分组
print("\n[按买入时偏离度分组]")
for dev_range in [(-5,-3), (-3,-1), (-1,1), (1,3)]:
    subset = [s for s in all_signals if dev_range[0] <= s["dev"] <= dev_range[1]]
    if subset:
        sw = sum(1 for s in subset if s["result"] == "win")
        sl = sum(1 for s in subset if s["result"] == "loss")
        print(f"  偏离{dev_range[0]:+d}%~{dev_range[1]:+d}%: {len(subset)}个信号, 胜{sw}/{len(subset)} ({sw/len(subset)*100:.0f}%)")

# 评分分组
print("\n[按评分分组]")
for sc in [2, 4]:
    subset = [s for s in all_signals if s["score"] == sc]
    if subset:
        sw = sum(1 for s in subset if s["result"] == "win")
        sl = sum(1 for s in subset if s["result"] == "loss")
        print(f"  评分{sc}分: {len(subset)}个信号, 胜{sw}/{len(subset)} ({sw/len(subset)*100:.0f}%)")

# 涨跌幅极值
print("\n[信号后10日最大涨幅分布]")
for rng in [(0,3),(3,7),(7,15),(15,100)]:
    subset = [s for s in all_signals if rng[0] <= s["max_chg_10d"] < rng[1]]
    if subset:
        print(f"  最大涨{rng[0]}%~{rng[1]}%: {len(subset)}个信号")

print(f"\n\n7. 各股票表现:")
print("-"*70)
by_code = {}
for s in all_signals:
    k = s["code"]
    if k not in by_code: by_code[k] = {"w":0,"l":0,"f":0}
    by_code[k][s["result"][0]] += 1

for code, stats in sorted(by_code.items(), key=lambda x: -(x[1]["w"])):
    total_c = stats["w"]+stats["l"]+stats["f"]
    wr = stats["w"]/total_c*100 if total_c > 0 else 0
    print(f"  {code}: {stats['w']}胜{stats['l']}负{stats['f']}平 ({wr:.0f}%)")

# 8. 失败信号特征分析
print(f"\n\n8. 失败信号特征分析")
print("-"*70)
loss_signals = [s for s in all_signals if s["result"] == "loss"]
win_signals = [s for s in all_signals if s["result"] == "win"]

if loss_signals:
    avg_dev_loss = sum(s["dev"] for s in loss_signals)/len(loss_signals)
    avg_dev_win = sum(s["dev"] for s in win_signals)/len(win_signals) if win_signals else 0
    print(f"  失败信号平均偏离: {avg_dev_loss:+.1f}%")
    print(f"  成功信号平均偏离: {avg_dev_win:+.1f}%")
    
    # 看有没有共同特征
    # 失败信号是否集中在某个偏离范围？
    loss_dev_high = sum(1 for s in loss_signals if s["dev"] > 1)
    loss_dev_low = sum(1 for s in loss_signals if s["dev"] <= 1)
    print(f"  失败中偏离>+1%: {loss_dev_high}个 | 偏离≤+1%: {loss_dev_low}个")
    
    # 次日涨跌方向与最终结果的关系
    wrong_dir = sum(1 for s in loss_signals if s["day1_chg"] < 0)
    print(f"  失败中买入次日即下跌: {wrong_dir}/{len(loss_signals)}")

print(f"\n\n9. 优化建议:")
print("-"*70)
# 根据分析给出具体建议
print("""
基于滚动回测数据, 建议策略优化方向:

1. 偏离度优化:
   - 检查买入时偏离度对胜率的影响
   - 如果偏离>+1%的失败率偏高 → 收紧买入区间到-3%~+1%

2. 次日验证:
   - 如果次日即下跌的信号失败率显著偏高
   - → 加一条"次日确认"规则: 信号日触发后, 等次日开盘确认

3. 评分权重:
   - 对比4分和2分信号的胜率差异
   - 如果4分明显高于2分 → 只做4分信号

4. 买入后跟踪:
   - 统计最大涨幅<3%的信号比例
   - 如果比例高 → 多数信号根本没有动能, 需提高放量阈值
""")
