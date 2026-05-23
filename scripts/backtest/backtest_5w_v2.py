import os, time, requests, json
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
import pandas as pd
import akshare as ak

CAPITAL = 50000
TARGET_PCT = 0.07
STOP_PCT = -0.05
WEEKLY_MAX = 2

print("="*65)
print(f"\ud83d\udcca \u5b8c\u6574\u56de\u6d4b: \u00a5{int(CAPITAL/10000)}\u4e07 \u00b7 +7%\u6b62\u76c8 \u00b7 -5%\u6b62\u635f\u00b7 \u22642\u6b21/\u5468")
print("="*65)

# Step 1
dates = ["20260424","20260430","20260506","20260507","20260508",
         "20260511","20260512","20260513","20260514","20260515"]
all_zt = []
for d in dates:
    df = ak.stock_zt_pool_em(date=d)
    time.sleep(0.2)
    df["\u65e5\u671f"] = d
    all_zt.append(df)
zt_all = pd.concat(all_zt, ignore_index=True)

codes_list = list(zt_all["\u4ee3\u7801"].unique())[:60]
print(f"\n\u83b7\u53d6\u57fa\u672c\u9762({len(codes_list)}\u53ea)...")
stock_scores = {}
count = 0

for code in codes_list:
    code_s = str(code).strip().zfill(6)
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="\u6309\u62a5\u544a\u671f")
        time.sleep(0.25)
        l = df.iloc[-1]
        def n(s):
            try: return float(str(s).replace("%",""))
            except: return 0
        rev = n(l.get("\u8425\u4e1a\u603b\u6536\u5165\u540c\u6bd4\u589e\u957f\u7387","0"))
        prof = n(l.get("\u51c0\u5229\u6da6\u540c\u6bd4\u589e\u957f\u7387","0"))
        score = 0
        if rev > 15: score += 2
        if prof > 50: score += 2
        if score >= 2:
            stock_scores[code_s] = {"score":score, "rev":rev, "profit":prof}
            count += 1
    except:
        time.sleep(0.25)

print(f"\u901a\u8fc7v2.4\u8bc4\u5206: {len(stock_scores)}\u53ea")

# Simulate trading
print("\n\u6a21\u62df\u4ea4\u6613\u4e2d...")
cash = CAPITAL
positions = {}
trades = []
weekly_trades = 0
current_week = ""
total_pnl = 0
wins = 0
losses = 0

unique_dates = sorted(zt_all["\u65e5\u671f"].unique())

for d in unique_dates:
    week_key = d[:6]
    day_zt = zt_all[zt_all["\u65e5\u671f"]==d]
    
    if week_key != current_week:
        current_week = week_key
        weekly_trades = 0
    
    # Check positions for sell
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
                reason = "\u6b62\u76c8+7%" if pnl_pct >= TARGET_PCT else f"\u6b62\u635f{int(pnl_pct*100)}%"
                trades.append(f"\ud83d\udd34 {d} \u5356\u51fa {pos['name']}({code}) \u00a5{pos['buy_price']:.2f}\u2192\u00a5{price:.2f} PnL:\u00a5{pnl:+} {reason}")
                if pnl > 0: wins += 1
                else: losses += 1
                del positions[code]
        except:
            pass
    
    # Look for buys
    for _, stock in day_zt.iterrows():
        if weekly_trades >= WEEKLY_MAX:
            break
        code_s = str(stock["\u4ee3\u7801"]).strip().zfill(6)
        if code_s not in stock_scores or code_s in positions:
            continue
        
        price = float(stock["\u6700\u65b0\u4ef7"])
        if price > 100 or price * 100 > cash * 0.5:
            continue
        
        mkt = "sh" if code_s.startswith(("6","9")) else "sz"
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={mkt}{code_s}&scale=240&ma=no&datalen=40"
        try:
            r = requests.get(url, timeout=8)
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
                    positions[code_s] = {"shares":shares, "buy_price":price, "name":stock["\u540d\u79f0"], "buy_date":d}
                    weekly_trades += 1
                    trades.append(f"\ud83d\udfe2 {d} \u4e70\u5165 {stock['\u540d\u79f0']}({code_s}) {shares}\u80a1 x \u00a5{price:.2f} = \u00a5{cost:.0f}")
        except:
            continue

# Force close
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
    trades.append(f"\u26d4 {d} \u5f3a\u5e73 {pos['name']}({code}) PnL:\u00a5{pnl:+}")
    if pnl > 0: wins += 1
    else: losses += 1

print(f"\n{'='*65}")
print(f"\ud83d\udcca \u6700\u7ec8\u7ed3\u679c")
print(f"{'='*65}")
print(f"  \u521d\u59cb\u8d44\u91d1: \u00a5{CAPITAL:,}")
print(f"  \u6700\u7ec8\u8d44\u91d1: \u00a5{int(cash):,}")
print(f"  \u603b\u76c8\u4e8f:   \u00a5{int(total_pnl):+,} ({total_pnl/CAPITAL*100:+.1f}%)")
total_trades = wins + losses
print(f"  \u4ea4\u6613\u6b21\u6570: {total_trades}\u6b21")
if total_trades > 0:
    print(f"  \u80dc\u7387:     {wins}/{total_trades} = {int(wins/total_trades*100)}%")
print(f"\n\u4ea4\u6613\u660e\u7ec6:")
for t in trades:
    print(f"  {t}")
