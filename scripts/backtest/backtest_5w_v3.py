import os, time, requests, json
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
import pandas as pd
import akshare as ak

CAPITAL = 50000
TARGET_PCT = 0.07
STOP_PCT = -0.05
WEEKLY_MAX = 2

print(f"Backtest: RMB{int(CAPITAL/10000)}万 · +7%止盈 · -5%止损 · <=2次/周")
print("="*60)

# Step 1: Get limit-up data
dates = ["20260424","20260430","20260506","20260507","20260508",
         "20260511","20260512","20260513","20260514","20260515"]
all_zt = []
for d in dates:
    df = ak.stock_zt_pool_em(date=d)
    time.sleep(0.2)
    df["date"] = d
    all_zt.append(df)
zt_all = pd.concat(all_zt, ignore_index=True)
print(f"Data: {len(zt_all)} records, {zt_all['code'].nunique() if 'code' in zt_all.columns else 'N/A'} stocks")

# Use whatever column name for code
code_col = [c for c in zt_all.columns if "代" in c or "code" in c.lower()][0]
name_col = [c for c in zt_all.columns if "名" in c or "name" in c.lower()][0]
price_col = [c for c in zt_all.columns if "价" in c or "price" in c.lower() or "最新" in c][0]

codes_list = list(zt_all[code_col].unique())[:50]
print(f"Getting fundamentals for {len(codes_list)} stocks...")

stock_scores = {}
for code in codes_list:
    code_s = str(code).strip().zfill(6)
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期")
        time.sleep(0.25)
        l = df.iloc[-1]
        
        rev_raw = l.get("营业总收入同比增长率","0")
        prof_raw = l.get("净利润同比增长率","0")
        
        rev = 0.0
        prof = 0.0
        try:
            rev = float(str(rev_raw).replace("%",""))
            prof = float(str(prof_raw).replace("%",""))
        except:
            pass
        
        score = 0
        if rev > 15: score += 2
        if prof > 50: score += 2
        
        if score >= 2:
            stock_scores[code_s] = {"score":score, "rev":rev, "profit":prof}
    except:
        time.sleep(0.25)

print(f"Passed v2.4: {len(stock_scores)} stocks")

# Step 3: Simulate trading
print("\nSimulating trades...")
cash = CAPITAL
positions = {}
trades = []
weekly_trades = 0
current_week = ""
total_pnl = 0
wins = 0
losses = 0

unique_dates = sorted(zt_all["date"].unique())

for d in unique_dates:
    week_key = d[:6]
    day_zt = zt_all[zt_all["date"]==d]
    
    if week_key != current_week:
        current_week = week_key
        weekly_trades = 0
    
    # Check sell conditions
    for code in list(positions.keys()):
        mkt = "sh" if str(code).startswith(("6","9")) else "sz"
        try:
            r = requests.get(f"http://qt.gtimg.cn/q={mkt}{code}", timeout=5)
            price = float(r.text.split("~")[3])
            pos = positions[code]
            pnl_pct = (price - pos["buy_price"]) / pos["buy_price"]
            if pnl_pct >= TARGET_PCT or pnl_pct <= STOP_PCT:
                proceeds = pos["shares"] * price
                pnl = proceeds - (pos["shares"] * pos["buy_price"])
                cash += proceeds
                total_pnl += pnl
                reason = "止盈+7%" if pnl_pct >= TARGET_PCT else f"止损{int(pnl_pct*100)}%"
                trades.append(f"[SELL] {d} {pos['name']}({code}) {pos['buy_price']:.2f}->{price:.2f} PnL:{pnl:+.0f} {reason}")
                if pnl > 0: wins += 1
                else: losses += 1
                del positions[code]
        except:
            pass
    
    # Look for buy opportunities
    for _, stock in day_zt.iterrows():
        if weekly_trades >= WEEKLY_MAX:
            break
        code_s = str(stock[code_col]).strip().zfill(6)
        if code_s not in stock_scores or code_s in positions:
            continue
        
        price = float(stock[price_col])
        if price > 100 or price * 100 > cash * 0.5:
            continue
        
        mkt = "sh" if code_s.startswith(("6","9")) else "sz"
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={mkt}{code_s}&scale=240&ma=no&datalen=40"
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
            kdata = json.loads(r.text)
            closes = [float(x["close"]) for x in kdata[-20:]]
            if len(closes) < 10: continue
            ma20 = sum(closes)/len(closes)
            dev = (price - ma20)/ma20*100
            if -3 <= dev <= 3:
                shares = int(cash * 0.3 / price / 100) * 100
                if shares >= 100:
                    cost = price * shares
                    cash -= cost
                    stock_name = str(stock[name_col])
                    positions[code_s] = {"shares":shares, "buy_price":price, "name":stock_name}
                    weekly_trades += 1
                    trades.append(f"[BUY]  {d} {stock_name}({code_s}) {shares}shares x {price:.2f} = {cost:.0f}")
        except:
            continue

# Final close
for code in list(positions.keys()):
    pos = positions[code]
    mkt = "sh" if str(code).startswith(("6","9")) else "sz"
    try:
        r = requests.get(f"http://qt.gtimg.cn/q={mkt}{code}", timeout=5)
        price = float(r.text.split("~")[3])
    except:
        price = pos["buy_price"]
    proceeds = pos["shares"] * price
    pnl = proceeds - (pos["shares"] * pos["buy_price"])
    cash += proceeds
    total_pnl += pnl
    trades.append(f"[CLOSE] {pos['name']}({code}) PnL:{pnl:+}")
    if pnl > 0: wins += 1
    else: losses += 1

print(f"\n{'='*60}")
print("FINAL RESULTS")
print(f"{'='*60}")
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
