import os, time, requests, json, datetime
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
import akshare as ak
import pandas as pd

print("="*60)
print("v2.4 明日(5/18) 买入信号扫描")
print("="*60)

# 1. Get latest limit-up pool
print("\n1. 获取涨停池...")
zt_dates = ["20260506","20260507","20260508","20260511","20260512","20260513","20260514","20260515"]
all_zt = []
for d in zt_dates:
    try:
        df = ak.stock_zt_pool_em(date=d)
        time.sleep(0.15)
        df["date"] = d
        all_zt.append(df)
    except:
        time.sleep(0.2)

zt_all = pd.concat(all_zt, ignore_index=True) if all_zt else pd.DataFrame()
code_col = [c for c in zt_all.columns if "代" in c or "code" in c.lower()][0]
codes = list(zt_all[code_col].unique())[:50]
print(f"  涨停池: {len(codes)}支")

# 2. Score with v2.4
print("\n2. v2.4评分...")
def is_main_board(code):
    """仅保留沪/深主板(60,00开头), 排除注册制(688,300,301,8)"""
    c = str(code).strip().zfill(6)
    return not c.startswith(("688","300","301","8"))

stock_scores = {}
for code in codes:
    code_s = str(code).strip().zfill(6)
    if not is_main_board(code_s): continue
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

print(f"  合格(评分≥2): {len(stock_scores)}支")

# 3. Get K-line data and real-time quotes
print("\n3. 获取K线和实时行情...")

today_str = datetime.date.today().strftime("%Y-%m-%d")
results = []

for code_s, info in stock_scores.items():
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    
    # Get K-line
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=80"
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        kdata = json.loads(r.text)
    except:
        time.sleep(0.1)
        continue
    if len(kdata) < 30: continue
    
    closes = [float(d["close"]) for d in kdata]
    vols = [int(d["volume"]) for d in kdata]
    highs = [float(d["high"]) for d in kdata]
    
    current = closes[-1]
    ma20 = sum(closes[-20:])/20
    dev = (current - ma20)/ma20*100
    
    # Volume breakout (last 15 days vs previous 15 days)
    recent_vol = sum(vols[-15:])/15 if len(vols) >= 15 else sum(vols)/len(vols)
    prev_vol = sum(vols[-30:-15])/15 if len(vols) >= 30 else sum(vols[:len(vols)//2])/max(1,len(vols)//2)
    vol_ratio = recent_vol/prev_vol if prev_vol > 0 else 0
    
    # Volume spike detection (within last 10 days, >2x of 15-day average)
    avg_vol = sum(vols[-20:])/20
    max_spike = max(vols[-10:])/avg_vol if avg_vol > 0 else 0
    has_spike = max_spike >= 2.0
    
    # 3-month change
    chg = (closes[-1]-closes[0])/closes[0]*100 if len(closes) >= 60 else (closes[-1]-closes[-min(60,len(closes))])/closes[-min(60,len(closes))]*100
    
    # Price trend: MA5 > MA20 > MA60 (uptrend)
    ma5 = sum(closes[-5:])/5 if len(closes) >= 5 else closes[-1]
    ma60 = sum(closes[-60:])/60 if len(closes) >= 60 else closes[0]
    uptrend = ma5 > ma20 and ma20 > ma60
    
    # Max daily close in last 20 days
    max_20 = max(closes[-20:])
    near_high = current / max_20 > 0.95  # Near 20-day high
    
    # Get real-time name & price from Tencent
    name = code_s
    real_price = current
    pe = "N/A"
    try:
        r2 = requests.get(f"http://qt.gtimg.cn/q={pre}{code_s}", timeout=5)
        parts = r2.text.split("~")
        name = parts[1] if len(parts) > 1 else code_s
        real_price = float(parts[3]) if parts[3] else current
        pe = parts[39] if len(parts) > 39 else "N/A"
    except:
        pass
    
    is_buy = has_spike and (-5 <= dev <= 3) and current <= 100
    
    results.append({
        "code": code_s, "name": name, "score": info["score"],
        "rev": info["rev"], "profit": info["profit"],
        "price": real_price, "ma20": round(ma20,2), "dev": round(dev,1),
        "vol_ratio": round(vol_ratio,1), "spike": round(max_spike,1),
        "ma5": round(ma5,2), "ma60": round(ma60,2),
        "uptrend": uptrend, "near_high": near_high,
        "chg3m": round(chg,1), "pe": pe,
        "buy_signal": is_buy
    })

# 4. Analyze and prioritize
buy_now = [r for r in results if r["buy_signal"]]
wait = [r for r in results if not r["buy_signal"] and r["dev"] > 3 and r["dev"] < 20]

print("\n" + "="*60)
print(f"扫描结果: 合格池{len(stock_scores)}支, 当前买入信号{len(buy_now)}支")
print("="*60)

if buy_now:
    print(f"\n🟢 当前有买入信号的标的 ({len(buy_now)}支):")
    buy_now.sort(key=lambda x: (x["score"], -x["dev"]), reverse=True)
    
    print(f"\n{'代码':<8} {'名称':<10} {'评分':<4} {'现价':<8} {'MA20':<8} {'偏离':<6} {'放量比':<6} {'走势':<6} {'3月涨幅':<8}")
    print("-"*75)
    for r in buy_now:
        trend_icon = "🔼" if r["uptrend"] else "➡"
        print(f"{r['code']:<8} {r['name']:<10} {r['score']}分   ¥{r['price']:<6.2f} ¥{r['ma20']:<6.2f} {r['dev']:+.1f}%  {r['spike']:.1f}x  {trend_icon:<4} {r['chg3m']:+.1f}%")
    
    # Top 3 picks
    print(f"\n{'='*60}")
    print("🌟 明日(5/18) TOP 3 推荐 (按评分+偏离排序):")
    print(f"{'='*60}")
    
    top3 = buy_now[:3]
    for i, r in enumerate(top3, 1):
        buy_zone = f"¥{r['ma20']*0.97:.2f} ~ ¥{r['ma20']*1.02:.2f}"
        stop_loss = f"¥{r['ma20']*0.95:.2f}"
        target = f"¥{r['price']*1.07:.2f}"
        pct_to_ma20 = (r['price'] - r['ma20']) / r['ma20'] * 100
        print(f"\n  #{i} {r['name']}({r['code']})  评分 {r['score']}分")
        print(f"    现价: ¥{r['price']:.2f}  |  MA20: ¥{r['ma20']}  |  偏离: {r['dev']:+.1f}%")
        print(f"    买入区间: {buy_zone}  |  止损: {stop_loss}  |  目标: {target}")
        print(f"    营收: +{r['rev']:.1f}%  |  净利: +{r['profit']:.1f}%  |  PE: {r['pe']}")
        print(f"    放量比: {r['spike']:.1f}x  |  趋势: {'上升' if r['uptrend'] else '震荡'}")
        print(f"    近高: {'是' if r['near_high'] else '否'}  |  3月涨幅: {r['chg3m']:+.1f}%")

else:
    print("\n🟡 当前没有符合条件的买入信号")

# Wait list
wait.sort(key=lambda x: x["score"], reverse=True)
if wait:
    print(f"\n🟡 等待回调标的 (已放量但偏离MA20>+3%, {len(wait)}支):")
    for r in wait[:5]:
        need_drop = (r["ma20"] - r["price"]) / r["price"] * 100
        print(f"  {r['name']}({r['code']}) 评分{r['score']}分  ¥{r['price']:.2f}  MA20¥{r['ma20']}  偏离{r['dev']:+.1f}% → 再跌{need_drop:.0f}%进区间")

print(f"\n{'='*60}")
print("盘前/开盘30分钟必看清单:")
print(f"{'='*60}")
print("""
📍 盘前(9:00-9:25):
  1. 看这3支的分时竞价——竞价量>昨日10%且价格在MA20附近可重点跟进
  2. 看大盘(上证)是否在MA20以上(>3350) 
  3. 看板块涨幅榜——候选股所在板块是否在涨幅前5

📍 开盘30分钟(9:30-10:00):
  1. 走势确认——开盘15分钟稳住MA20以上可考虑入场
  2. 放量确认——前30分钟成交量>昨日同期1.5倍
  3. 大盘环境——上证不破昨日收盘验证多方格局
  4. 盘中若有急跌到-4%~-3%(MA20附近)且回拉，是较好的入场点
""")
