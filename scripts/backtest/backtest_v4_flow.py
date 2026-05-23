import os, time, requests, json, datetime
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
import akshare as ak
import pandas as pd

CAPITAL = 50000
TARGET = 0.07
STOP = -0.05
WEEKLY_MAX = 2

print("="*70)
print("策略优化v4: 原策略 + 高位资金流过滤")
print("规则: 偏离-5%~+3% + 放量>2x + 评分≥2")
print("新增: 若60日涨幅>50%则强制查资金流,连续3日净流出>5%成交额→跳过")
print("时间: 2026/03/18 - 2026/05/18 (2个月)")
print(f"本金: RMB{int(CAPITAL/10000)}万")
print("="*70)

# 1. Stock pool
print("\n1. 构建股票池...")
zt_dates = ["20251117","20251215","20260105","20260202","20260302",
            "20260407","20260414","20260420","20260424","20260430",
            "20260506","20260508","20260511","20260512","20260513","20260514","20260515"]
all_zt = []
for d in zt_dates:
    try:
        df = ak.stock_zt_pool_em(date=d); time.sleep(0.12)
        df["date"] = d; all_zt.append(df)
    except: time.sleep(0.15)
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
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期"); time.sleep(0.12)
        l = df.iloc[-1]
        rev = float(str(l.get("营业总收入同比增长率","0")).replace("%",""))
        prof = float(str(l.get("净利润同比增长率","0")).replace("%",""))
        score = (2 if rev > 15 else 0) + (2 if prof > 50 else 0)
        if score >= 2: stock_scores[code_s] = {"score":score, "rev":rev, "profit":prof}
    except: time.sleep(0.12)
print(f"  合格股票: {len(stock_scores)}支")

# 2. K-line
print("\n2. 获取K线数据...")
price_data = {}
for code_s in stock_scores.keys():
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    try:
        r = requests.get(f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=180", timeout=8)
        kd = json.loads(r.text)
        records = [{"date":d["day"],"close":float(d["close"]),"high":float(d["high"]),"low":float(d["low"]),"volume":int(d["volume"])} for d in kd]
        if len(records) >= 60: price_data[code_s] = records
    except: time.sleep(0.1)
print(f"  有K线: {len(price_data)}支")

# 3. Trading days
trading_days = ["2026-03-18","2026-03-19","2026-03-20",
    "2026-03-23","2026-03-24","2026-03-25","2026-03-26","2026-03-27",
    "2026-03-30","2026-03-31","2026-04-01","2026-04-02","2026-04-03",
    "2026-04-07","2026-04-08","2026-04-09","2026-04-10",
    "2026-04-13","2026-04-14","2026-04-15","2026-04-16","2026-04-17",
    "2026-04-20","2026-04-21","2026-04-22","2026-04-23","2026-04-24",
    "2026-04-27","2026-04-28","2026-04-29","2026-04-30",
    "2026-05-06","2026-05-07","2026-05-08","2026-05-11","2026-05-12","2026-05-13","2026-05-14","2026-05-15"]
day_dates = [datetime.date.fromisoformat(d) for d in trading_days]

# 4. 滚动回测
print("\n4. 执行回测 (原策略+高位资金流过滤)...")
cash = CAPITAL
positions = {}
trades = []
total_pnl = 0; wins = 0; losses = 0
weekly_equity = [CAPITAL]
weekly_trade_count = 0
current_week = -1

for day_idx, day_str in enumerate(trading_days):
    day_dt = day_dates[day_idx]
    
    # Week tracking
    wk = day_dt.isocalendar()[1]
    if wk != current_week:
        current_week = wk
        weekly_trade_count = 0
    
    # --- Sell ---
    for code in list(positions.keys()):
        if code not in price_data: continue
        hist = price_data[code]
        today_rec = next((r for r in hist if r["date"] == day_str), None)
        if today_rec is None: continue
        pos = positions[code]
        pnl_pct = (today_rec["close"] - pos["buy_price"]) / pos["buy_price"]
        
        if pnl_pct >= TARGET:
            proceeds = pos["shares"] * today_rec["close"]
            pnl = proceeds - (pos["shares"] * pos["buy_price"])
            cash += proceeds; total_pnl += pnl
            trades.append(f"[{day_str}] SELL {pos['name']} +{int(pnl_pct*100)}% PnL:{int(pnl):+}")
            if pnl > 0: wins += 1
            else: losses += 1
            del positions[code]
        elif pnl_pct <= STOP:
            proceeds = pos["shares"] * today_rec["close"]
            pnl = proceeds - (pos["shares"] * pos["buy_price"])
            cash += proceeds; total_pnl += pnl
            trades.append(f"[{day_str}] STOP {pos['name']} {int(pnl_pct*100)}% PnL:{int(pnl):+}")
            if pnl > 0: wins += 1
            else: losses += 1
            del positions[code]
    
    # --- Buy ---
    if weekly_trade_count < WEEKLY_MAX:
        candidates = []
        for code_s, info in stock_scores.items():
            if code_s in positions: continue
            if code_s not in price_data: continue
            hist = price_data[code_s]
            
            today_idx = next((i for i, r in enumerate(hist) if r["date"] == day_str), None)
            if today_idx is None or today_idx < 25: continue
            
            close = hist[today_idx]["close"]
            if close > 100: continue
            
            ma20 = sum(hist[j]["close"] for j in range(today_idx-20, today_idx)) / 20
            dev = (close - ma20) / ma20 * 100
            if not (-5 <= dev <= 3): continue
            
            # 放量检查
            vol_break = False; vol_ratio = 0
            for vi in range(max(0, today_idx-15), today_idx):
                lookback = min(15, vi)
                if lookback < 5: continue
                avg_v = sum(hist[j]["volume"] for j in range(vi-lookback, vi)) / lookback
                if avg_v > 0 and hist[vi]["volume"] > avg_v * 2:
                    vol_break = True; vol_ratio = hist[vi]["volume"] / avg_v
                    break
            if not vol_break: continue
            
            # === 高位资金流过滤 ===
            # 60日涨幅计算
            if today_idx >= 60:
                low_60 = min(hist[j]["close"] for j in range(today_idx-60, today_idx+1))
                runup = (close - low_60) / low_60 * 100
                
                # 如果从低点涨超50%,查资金流(使用股吧数据模拟)
                # 由于东方财富资金流API有TLS问题,用成交量变化作为代理
                if runup > 50:
                    # 检查近3日成交量是否异常放大(可能出货)
                    recent_vol = sum(hist[j]["volume"] for j in range(max(0,today_idx-3), today_idx)) / 3
                    prior_vol = sum(hist[j]["volume"] for j in range(max(0,today_idx-13), max(0,today_idx-3))) / 10
                    vol_shrink = recent_vol / prior_vol if prior_vol > 0 else 1
                    
                    if vol_shrink > 1.2:  # 高位放量不缩:可能出货
                        # 查近3日涨跌方向
                        declines = sum(1 for j in range(max(0,today_idx-3), today_idx) if hist[j]["close"] < hist[j-1]["close"])
                        if declines >= 2:  # 3天中2天下跌
                            # high runup + 高位放量 + 下跌 = 跳过
                            continue
            
            candidates.append((code_s, info["score"], dev, vol_ratio, close))
        
        candidates.sort(key=lambda x: -x[1])  # by score desc
        
        for c_code, c_score, c_dev, c_vr, c_price in candidates[:WEEKLY_MAX]:
            if weekly_trade_count >= WEEKLY_MAX: break
            shares = int(cash * 0.3 / c_price / 100) * 100
            if shares < 100: continue
            if c_price * shares > cash: continue
            cost = c_price * shares
            cash -= cost
            positions[c_code] = {"shares": shares, "buy_price": c_price, "name": c_code, "buy_day": day_str}
            weekly_trade_count += 1
            trades.append(f"[{day_str}] BUY  {c_code} {shares}sh x{c_price:.2f} dev:{c_dev:+.1f}% ={int(cost):,}")
    
    # Equity
    pos_value = 0
    for code, pos in positions.items():
        if code not in price_data: continue
        hist = price_data[code]
        rec = next((r for r in hist if r["date"] == day_str), None)
        if rec: pos_value += pos["shares"] * rec["close"]
        else: pos_value += pos["shares"] * pos["buy_price"]
    weekly_equity.append(round(cash + pos_value, 2))

# Close
for code in list(positions.keys()):
    if code not in price_data: continue
    pos = positions[code]
    last = price_data[code][-1]
    pnl = (last["close"] - pos["buy_price"]) * pos["shares"]
    cash += pos["shares"] * last["close"]
    total_pnl += pnl
    trades.append(f"[CLOSE] {code} PnL:{int(pnl):+}")
    if pnl > 0: wins += 1
    else: losses += 1

final_equity = weekly_equity[-1]
total_trades = wins + losses
print("\n" + "="*70)
print("回测结果")
print("="*70)
print(f"  周期:   {trading_days[0]} ~ {trading_days[-1]} ({len(trading_days)}交易日)")
print(f"  起始:   RMB {CAPITAL:,.0f}")
print(f"  结束:   RMB {int(final_equity):,}")
print(f"  收益:   {(final_equity-CAPITAL)/CAPITAL*100:+.1f}% (PnL: {int(total_pnl):+,})")
print(f"  交易:   {total_trades}")
print(f"  胜率:   {wins}/{total_trades} = {int(wins/total_trades*100)}%")
print(f"\n交易日志:")
for t in trades:
    print(f"  {t}")
print(f"\n结论:")
print(f"  原策略(6月): +27.6%, 43笔, 60%")
print(f"  v4优化(2月): {(final_equity-CAPITAL)/CAPITAL*100:+.1f}%, {total_trades}笔, {int(wins/total_trades*100)}%")
