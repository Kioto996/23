"""
策略参数优化
对不同参数组合进行系统化测试，找最优组合
"""
import os, time, requests, json, datetime, math
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
import akshare as ak
import pandas as pd

CAPITAL = 50000
WEEKLY_MAX = 2

# ====== 1. 固定数据（一次获取，多次复用） ======
print("1. 构建固定数据池...")
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
        if score >= 2: stock_scores[code_s] = {"score":score}
    except: time.sleep(0.1)
print(f"  股票池: {len(stock_scores)}支")

# 价格数据
price_data = {}
for code_s in stock_scores.keys():
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    try:
        r = requests.get(f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=180", timeout=8)
        kd = r.json()
        records = [{"date":d["day"],"close":float(d["close"]),"volume":int(d["volume"])} for d in kd]
        if len(records) >= 60: price_data[code_s] = records
    except: time.sleep(0.1)
print(f"  价格数据: {len(price_data)}支")

# 交易日
trading_days = ["2026-03-18","2026-03-19","2026-03-20",
    "2026-03-23","2026-03-24","2026-03-25","2026-03-26","2026-03-27",
    "2026-03-30","2026-03-31","2026-04-01","2026-04-02","2026-04-03",
    "2026-04-07","2026-04-08","2026-04-09","2026-04-10",
    "2026-04-13","2026-04-14","2026-04-15","2026-04-16","2026-04-17",
    "2026-04-20","2026-04-21","2026-04-22","2026-04-23","2026-04-24",
    "2026-04-27","2026-04-28","2026-04-29","2026-04-30",
    "2026-05-06","2026-05-07","2026-05-08","2026-05-11","2026-05-12","2026-05-13","2026-05-14","2026-05-15"]

# ====== 2. 参数扫描函数 ======
def run_backtest(vol_min, dev_low, dev_high, target_pct, stop_pct):
    """运行一次完整回测，返回结果"""
    cash = CAPITAL
    positions = {}
    trades = []
    total_pnl = 0; wins = 0; losses = 0
    
    for day_idx, day_str in enumerate(trading_days[:-1]):
        # Sell
        for code in list(positions.keys()):
            if code not in price_data: continue
            hist = price_data[code]
            rec = next((r for r in hist if r["date"] == day_str), None)
            if rec is None: continue
            pos = positions[code]
            pnl_pct = (rec["close"] - pos["buy_price"]) / pos["buy_price"]
            
            if pnl_pct >= target_pct:
                cash += pos["shares"] * rec["close"]
                total_pnl += (rec["close"] - pos["buy_price"]) * pos["shares"]
                if (rec["close"] - pos["buy_price"]) * pos["shares"] > 0: wins += 1
                else: losses += 1
                del positions[code]
            elif pnl_pct <= stop_pct:
                cash += pos["shares"] * rec["close"]
                total_pnl += (rec["close"] - pos["buy_price"]) * pos["shares"]
                if (rec["close"] - pos["buy_price"]) * pos["shares"] > 0: wins += 1
                else: losses += 1
                del positions[code]
        
        # Buy
        if len(positions) < WEEKLY_MAX:
            candidates = []
            for code_s, info in stock_scores.items():
                if code_s in positions or code_s not in price_data: continue
                hist = price_data[code_s]
                idx = next((i for i,r in enumerate(hist) if r["date"] == day_str), None)
                if idx is None or idx < 25: continue
                close = hist[idx]["close"]
                if close > 100: continue
                
                ma20 = sum(hist[j]["close"] for j in range(idx-20, idx))/20
                dev = (close-ma20)/ma20*100
                if not (dev_low <= dev <= dev_high): continue
                
                vol_break = False
                for vi in range(max(0, idx-15), idx):
                    lb = min(15, vi)
                    if lb < 5: continue
                    avg_v = sum(hist[j]["volume"] for j in range(vi-lb, vi))/lb
                    if avg_v > 0 and hist[vi]["volume"] > avg_v * vol_min:
                        vol_break = True; break
                if not vol_break: continue
                
                candidates.append((code_s, info["score"], dev, close))
            
            for c_code, _, _, c_price in sorted(candidates, key=lambda x: -x[1])[:WEEKLY_MAX]:
                if len(positions) >= WEEKLY_MAX: break
                shares = int(cash * 0.3 / c_price / 100) * 100
                if shares < 100: continue
                cash -= c_price * shares
                positions[c_code] = {"shares": shares, "buy_price": c_price}
    
    # Close
    for code in list(positions.keys()):
        if code not in price_data: continue
        pos = positions[code]
        last = price_data[code][-1]
        pnl = (last["close"] - pos["buy_price"]) * pos["shares"]
        cash += pos["shares"] * last["close"]
        total_pnl += pnl
        if pnl > 0: wins += 1
        else: losses += 1
    
    total = wins + losses
    ret = (cash - CAPITAL) / CAPITAL * 100
    wr = wins/total*100 if total > 0 else 0
    return {"trades": total, "wins": wins, "return_pct": round(ret,1), "win_rate": round(wr,1)}

# ====== 3. 参数扫描 ======
print("\n2. 参数扫描...")
print(f"{'放量阈值':<8} {'偏离范围':<12} {'止盈':<6} {'止损':<6} {'交易数':<6} {'胜率':<6} {'收益率':<8}")
print("-"*55)

params_to_test = []
for vol_min in [1.5, 2.0, 2.5]:
    for dev_lo, dev_hi in [(-5,3), (-5,1), (-3,1)]:
        for tgt in [0.05, 0.07, 0.10]:
            for stp in [0.03, 0.05, 0.07]:
                params_to_test.append((vol_min, dev_lo, dev_hi, tgt, stp))

# 只用一半参数（随机抽样加速）
import random
random.seed(42)
test_params = random.sample(params_to_test, min(40, len(params_to_test)))
# 加入当前默认参数确保有基准
default = (2.0, -5, 3, 0.07, 0.05)
if default not in test_params:
    test_params.insert(0, default)

results = []
for vol_min, dev_lo, dev_hi, tgt, stp in test_params:
    r = run_backtest(vol_min, dev_lo, dev_hi, tgt, stp)
    dev_range = f"{dev_lo}~{dev_hi}"
    print(f"{'≥'+str(vol_min)+'x':<8} {dev_range:<12} {'+'+str(int(tgt*100))+'%':<6} {'-'+str(int(stp*100))+'%':<6} {r['trades']:<6} {r['win_rate']:<5}% {r['return_pct']:<+6}%")
    results.append({"params":(vol_min, dev_lo, dev_hi, tgt, stp), **r})

# ====== 4. 排序 ======
print("\n\n3. 按收益率排序 Top 10:")
print(f"{'排名':<4} {'放量':<6} {'偏离':<10} {'止盈':<6} {'止损':<6} {'交易数':<5} {'胜率':<6} {'收益率':<8}")
print("-"*55)
results.sort(key=lambda x: -x["return_pct"])
for i, r in enumerate(results[:10]):
    p = r["params"]
    dev = f"{p[1]}~{p[2]}"
    print(f"#{i+1:<2}  {'≥'+str(p[0])+'x':<6} {dev:<10} {'+'+str(int(p[3]*100))+'%':<6} {'-'+str(int(p[4]*100))+'%':<6} {r['trades']:<5} {r['win_rate']:<5}% {r['return_pct']:<+6}%")

print(f"\n基准参数(2.0x,-5~3,+7%,-5%): ", end="")
base = [r for r in results if r["params"] == default]
if base:
    b = base[0]
    print(f"{b['trades']}笔, {b['win_rate']}%胜率, {b['return_pct']:+.1f}%收益")
