"""
N字战法回测 — 对比原策略 vs 加入新规则
"""
import os, time, requests, json, datetime
import akshare as ak
import pandas as pd
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

CAPITAL = 50000
WEEKLY_MAX = 2
TARGET_PCT = 0.07
STOP_PCT = 0.05

print("="*60)
print("N字战法 v5.0 回测")
print("新增: ①4天不赚清仓 ②移动止盈(MA5) ③止损=当日最低价")
print("="*60)

# 1. 数据池
zt_dates = ["20251117","20251215","20260105","20260202","20260302",
            "20260407","20260414","20260420","20260424","20260430",
            "20260506","20260508","20260511","20260512","20260513","20260514","20260515"]
all_zt = []
for d in zt_dates:
    try: df = ak.stock_zt_pool_em(date=d); time.sleep(0.1); df["date"]=d; all_zt.append(df)
    except: time.sleep(0.12)

zt_all = pd.concat(all_zt, ignore_index=True) if all_zt else pd.DataFrame()
code_col = [c for c in zt_all.columns if "代" in c or "code" in c.lower()][0]
codes = list(zt_all[code_col].unique())[:80]

def is_main(c):
    c = str(c).strip().zfill(6)
    return not c.startswith(("688","300","301","8"))

score4 = {}
for code in codes:
    code_s = str(code).strip().zfill(6)
    if not is_main(code_s): continue
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期"); time.sleep(0.08)
        l = df.iloc[-1]
        rev = float(str(l.get("营业总收入同比增长率","0")).replace("%",""))
        prof = float(str(l.get("净利润同比增长率","0")).replace("%",""))
        if rev > 15 and prof > 50: score4[code_s] = True
    except: time.sleep(0.1)
print(f"4分股票: {len(score4)}支")

price_data = {}
for code_s in score4.keys():
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    try:
        r = requests.get(f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=180", timeout=8)
        kd = r.json()
        records = []
        for d in kd:
            records.append({
                "date":d["day"], "close":float(d["close"]), 
                "high":float(d["high"]), "low":float(d["low"]),
                "open":float(d["open"]), "volume":int(d["volume"])
            })
        if len(records) >= 60: price_data[code_s] = records
    except: time.sleep(0.1)
print(f"价格数据: {len(price_data)}支")

trading_days = ["2026-04-07","2026-04-08","2026-04-09","2026-04-10",
    "2026-04-13","2026-04-14","2026-04-15","2026-04-16","2026-04-17",
    "2026-04-20","2026-04-21","2026-04-22","2026-04-23","2026-04-24",
    "2026-04-27","2026-04-28","2026-04-29","2026-04-30",
    "2026-05-06","2026-05-07","2026-05-08","2026-05-11","2026-05-12",
    "2026-05-13","2026-05-14","2026-05-15"]

def run_backtest(use_n_rules=False):
    cash = CAPITAL; pos = {}; trades = []; wins = 0; losses = 0
    
    for day_str in trading_days:
        # SELL
        for code in list(pos.keys()):
            if code not in price_data: continue
            hist = price_data[code]
            rec = next((r for r in hist if r["date"] == day_str), None)
            if rec is None: continue
            
            p = pos[code]
            pnl = (rec["close"] - p["buy"]) / p["buy"]
            days = p.get("days_held", 0) + 1
            p["days_held"] = days
            
            sell_reason = None
            
            # 原策略: +7%止盈/-5%止损
            if pnl >= TARGET_PCT:
                sell_reason = f"止盈+{int(pnl*100)}%"
            elif pnl <= STOP_PCT:
                sell_reason = f"止损{int(pnl*100)}%"
            
            # N字新规则 (如果启用)
            if use_n_rules:
                # 规则1: 4天不赚就卖
                if days >= 4 and pnl < 0.07:
                    sell_reason = f"弱·4天仅{int(pnl*100)}%"
                
                # 规则2: 移动止盈 — 涨>7%后跌破MA5
                if pnl > 0.07 and rec["close"] < p.get("ma5", rec["close"]):
                    sell_reason = f"破MA5·已赚{int(pnl*100)}%"
                
                # 规则3: 止损=买入当天最低价(代替固定-5%)
                day_low_stop = p.get("day_low_stop", p["buy"] * 0.95)
                if rec["close"] <= day_low_stop:
                    sell_reason = f"破当日最低{int((day_low_stop-p['buy'])/p['buy']*100)}%"
            
            if sell_reason:
                cash += p["shares"] * rec["close"]
                pnl_abs = (rec["close"] - p["buy"]) * p["shares"]
                trades.append(sell_reason)
                if pnl_abs > 0: wins += 1
                else: losses += 1
                del pos[code]
                continue
            
            # 更新MA5用于规则2
            idx = next((i for i,r in enumerate(hist) if r["date"] == day_str), None)
            if idx and idx >= 4:
                new_ma5 = sum(hist[j]["close"] for j in range(idx-4, idx+1))/5
                p["ma5"] = new_ma5
        
        # BUY
        if len(pos) < WEEKLY_MAX:
            cand = []
            for code_s in score4.keys():
                if code_s in pos or code_s not in price_data: continue
                hist = price_data[code_s]
                idx = next((i for i,r in enumerate(hist) if r["date"] == day_str), None)
                if idx is None or idx < 30: continue
                c = hist[idx]["close"]
                if c > 100: continue
                ma20 = sum(hist[j]["close"] for j in range(idx-20, idx))/20
                dev = (c-ma20)/ma20*100
                if not (-5 <= dev <= 3): continue
                
                vol_ok = False
                for vi in range(max(0,idx-15), idx):
                    lb = min(15, vi)
                    if lb < 5: continue
                    avg_v = sum(hist[j]["volume"] for j in range(vi-lb, vi))/lb
                    if avg_v > 0 and hist[vi]["volume"] > avg_v * 2: vol_ok = True; break
                if not vol_ok: continue
                cand.append((code_s, -dev))
            
            for cd, _ in sorted(cand)[:WEEKLY_MAX]:
                if len(pos) >= WEEKLY_MAX: break
                hist = price_data[cd]
                idx = next((i for i,r in enumerate(hist) if r["date"] == day_str), None)
                c = hist[idx]["close"]
                shares = int(cash * 0.3 / c / 100) * 100
                if shares < 100: continue
                cash -= c * shares
                
                # 初始化MA5和止损
                ma5_init = sum(hist[j]["close"] for j in range(idx-4, idx+1))/5 if idx>=4 else c
                day_low = hist[idx]["low"]
                day_low_stop = min(day_low * 0.98, c * 0.95)
                
                pos[cd] = {
                    "shares":shares, "buy":c, "days_held":0,
                    "ma5":ma5_init, "day_low_stop":day_low_stop
                }
    
    # Close all
    for code in list(pos.keys()):
        if code not in price_data: continue
        last = price_data[code][-1]
        pnl = (last["close"] - pos[code]["buy"]) * pos[code]["shares"]
        cash += pos[code]["shares"] * last["close"]
        if pnl > 0: wins += 1
        else: losses += 1
    
    total = wins + losses
    ret = (cash - CAPITAL) / CAPITAL * 100
    wr = wins / total * 100 if total > 0 else 0
    return ret, wins, losses, wr, trades

# 运行对比
print("\n运行回测...")
r_old, w_old, l_old, wr_old, tr_old = run_backtest(use_n_rules=False)
r_new, w_new, l_new, wr_new, tr_new = run_backtest(use_n_rules=True)

print("\n" + "="*60)
print("回测对比结果")
print("="*60)
print(f"{'策略':<20} {'收益':<8} {'胜率':<8} {'交易数':<8} {'盈亏比':<6}")
print("-"*50)
print(f"{'原策略(v4)':<20} {r_old:<+5.1f}%  {wr_old:.0f}%     {w_old+l_old}      —")
print(f"{'N字战法(v5)':<20} {r_new:<+5.1f}%  {wr_new:.0f}%     {w_new+l_new}      —")

# 交易明细对比
print(f"\nN字战法交易记录:")
for t in tr_new:
    print(f"  {t}")

print(f"\n结论:")
if r_new > r_old:
    print(f"  ✅ N字战法提升 {r_new-r_old:+.1f}%")
else:
    print(f"  ⚠️ N字战法变化 {r_new-r_old:+.1f}%")
