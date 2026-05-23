import os, time, requests, json
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import akshare as ak
import pandas as pd

CAPITAL = 50000
TARGET_PCT = 0.07
STOP_PCT = -0.05
WEEKLY_MAX = 2

print("Backtest: 12 weeks (2026/02/17 - 2026/05/15)")
print(f"Capital: RMB{int(CAPITAL/10000)}万, +7% take profit, -5% stop loss")
print("="*60)

# Get qualified stocks from limit-up data
dates = ["20260424","20260430","20260506","20260507","20260508",
         "20260511","20260512","20260513","20260514","20260515"]
all_zt = []
for d in dates:
    df = ak.stock_zt_pool_em(date=d)
    time.sleep(0.2)
    df["date"] = d
    all_zt.append(df)
zt_all = pd.concat(all_zt, ignore_index=True)

code_col = [c for c in zt_all.columns if "代" in c or "code" in c.lower()][0]
name_col = [c for c in zt_all.columns if "名" in c or "name" in c.lower()][0]

codes_list = list(zt_all[code_col].unique())[:50]

stock_scores = {}
for code in codes_list:
    code_s = str(code).strip().zfill(6)
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期")
        time.sleep(0.2)
        l = df.iloc[-1]
        rev = 0.0
        prof = 0.0
        try:
            rev = float(str(l.get("营业总收入同比增长率","0")).replace("%",""))
            prof = float(str(l.get("净利润同比增长率","0")).replace("%",""))
        except: pass
        score = (2 if rev > 15 else 0) + (2 if prof > 50 else 0)
        if score >= 2:
            stock_scores[code_s] = {"score":score, "rev":rev, "profit":prof}
    except:
        time.sleep(0.2)

print(f"Qualified stocks: {len(stock_scores)}")

# For each qualified stock, get full 3-month K-line (60 trading days = 12 weeks)
print("Getting 12-week price data...")
price_history = {}  # code -> [{date, close}]

for code_s in stock_scores.keys():
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=80"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        data = json.loads(r.text)
        # Sina returns newest last, so dates[0] is oldest
        records = []
        for d in data:
            records.append({"date": d["day"], "close": float(d["close"]),
                           "high": float(d["high"]), "low": float(d["low"]),
                           "volume": int(d["volume"])})
        if len(records) >= 40:
            price_history[code_s] = records
    except:
        time.sleep(0.1)

# Build weekly schedule: 12 weeks from Feb to May
weeks = []
import datetime
start = datetime.date(2026, 2, 17)
for w in range(12):
    mon = start + datetime.timedelta(weeks=w)
    fri = mon + datetime.timedelta(days=4)
    weeks.append((mon.strftime("%Y-%m-%d"), fri.strftime("%Y-%m-%d")))

print(f"Trading weeks: {len(weeks)}")
print()

# Simulate trading
cash = CAPITAL
positions = {}
trades = []
total_pnl = 0
wins = 0
losses = 0

for week_num, (mon_date, fri_date) in enumerate(weeks):
    weekly_trades = 0
    
    # Check existing positions
    for code in list(positions.keys()):
        if code not in price_history: continue
        hist = price_history[code]
        # Find closest date to Friday
        fri_record = None
        for r in hist:
            if r["date"] <= fri_date:
                fri_record = r
        if fri_record:
            price = fri_record["close"]
            pos = positions[code]
            pnl_pct = (price - pos["buy_price"]) / pos["buy_price"]
            if pnl_pct >= TARGET_PCT:
                proceeds = pos["shares"] * price
                pnl = proceeds - (pos["shares"] * pos["buy_price"])
                cash += proceeds
                total_pnl += pnl
                trades.append(f"[W{week_num+1}] SELL {pos['name']} +{int(pnl_pct*100)}% PnL:{int(pnl)}")
                if pnl > 0: wins += 1
                else: losses += 1
                del positions[code]
            elif pnl_pct <= STOP_PCT:
                proceeds = pos["shares"] * price
                pnl = proceeds - (pos["shares"] * pos["buy_price"])
                cash += proceeds
                total_pnl += pnl
                trades.append(f"[W{week_num+1}] STOP {pos['name']} {int(pnl_pct*100)}% PnL:{int(pnl)}")
                if pnl > 0: wins += 1
                else: losses += 1
                del positions[code]
    
    # Find buy opportunities - scan all qualified stocks
    candidates = []
    for code_s, info in stock_scores.items():
        if code_s in positions: continue
        if code_s not in price_history: continue
        
        hist = price_history[code_s]
        # Find Monday close
        mon_record = None
        for r in hist:
            if r["date"] >= mon_date:
                mon_record = r
                break
        
        if mon_record is None: continue
        
        price = mon_record["close"]
        if price > 100: continue
        if price * 100 > cash * 0.5: continue
        
        # Calculate MA20
        idx = hist.index(mon_record)
        if idx < 20: continue
        ma20_closes = [hist[i]["close"] for i in range(idx-20, idx)]
        ma20 = sum(ma20_closes)/20
        dev = (price - ma20)/ma20*100
        
        # Check for volume breakout in recent days
        vol_break = False
        for i in range(max(0, idx-10), idx):
            avg_vol_before = sum(h["volume"] for h in hist[max(0,i-10):i])/min(10,i)
            if avg_vol_before > 0 and hist[i]["volume"] > avg_vol_before * 2:
                vol_break = True
                break
        
        if vol_break and -5 <= dev <= 3:  # Broke out AND near MA20
            candidates.append((code_s, info, price, dev, mon_record["date"]))
    
    # Pick best candidates (high score first)
    candidates.sort(key=lambda x: x[1]["score"], reverse=True)
    for code_s, info, price, dev, buy_date in candidates[:WEEKLY_MAX]:
        if weekly_trades >= WEEKLY_MAX: break
        
        shares = int(cash * 0.3 / price / 100) * 100
        if shares < 100: continue
        cost = price * shares
        cash -= cost
        st_name = code_s  # Use code as name
        positions[code_s] = {"shares": shares, "buy_price": price, "name": st_name, "week": week_num+1}
        weekly_trades += 1
        trades.append(f"[W{week_num+1}] BUY  {code_s} {shares}sh x{price:.2f} dev:{dev:+.1f}% ={int(cost)}")

# Close remaining
for code in list(positions.keys()):
    if code not in price_history: continue
    pos = positions[code]
    last = price_history[code][-1]
    price = last["close"]
    proceeds = pos["shares"] * price
    pnl = proceeds - (pos["shares"] * pos["buy_price"])
    cash += proceeds
    total_pnl += pnl
    trades.append(f"[CLOSE] {code} PnL:{int(pnl)}")
    if pnl > 0: wins += 1
    else: losses += 1

print("="*60)
print("12-WEEK BACKTEST RESULTS")
print("="*60)
print(f"  Starting: RMB {CAPITAL:,.0f}")
print(f"  Ending:   RMB {int(cash):,}")
print(f"  PnL:      RMB {int(total_pnl):+,} ({total_pnl/CAPITAL*100:+.1f}%)")
total_trades = wins + losses
print(f"  Trades:   {total_trades}")
if total_trades > 0:
    print(f"  Win Rate: {wins}/{total_trades} = {int(wins/total_trades*100)}%")
print(f"\nTrade Log:")
for t in trades:
    print(f"  {t}")
