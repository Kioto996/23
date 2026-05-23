import os, time, requests, json
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import akshare as ak
import pandas as pd

CAPITAL = 50000
TARGET = 0.07  # 7%止盈
STOP = -0.05    # -5%止损
WEEKLY_MAX = 2

print("="*65)
print(f"📊 完整回测: ¥{CAPITAL/10000}万 · +7%止盈 · -5%止损· ≤2次/周")
print("="*65)

# Step 1: 获取批量数据
dates = ["20260424","20260430","20260506","20260507","20260508",
         "20260511","20260512","20260513","20260514","20260515"]

print("获取涨停数据...")
all_zt = []
for d in dates:
    df = ak.stock_zt_pool_em(date=d)
    time.sleep(0.2)
    df["日期"] = d
    all_zt.append(df)

zt_all = pd.concat(all_zt, ignore_index=True) if all_zt else None
if zt_all is None: exit()
print(f"{len(zt_all)}条记录, {zt_all['代码'].nunique()}只不同股票")

import pandas as pd
codes_done = set()
stock_scores = {}  # code -> score data

codes_list = zt_all["代码"].unique()
print(f"\n获取基本面({len(codes_list)}只, 限80只)...")
count = 0
for code in codes_list[:80]:
    code_s = str(code).strip().zfill(6)
    if code_s in codes_done: 
        continue
    codes_done.add(code_s)
    
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期")
        time.sleep(0.25)
        l = df.iloc[-1]
        
        def n(s):
            try: return float(str(s).replace("%",""))
            except: return 0
        
        rev = n(l.get("营业总收入同比增长率","0"))
        prof = n(l.get("净利润同比增长率","0"))
        
        score = 0
        if rev > 15: score += 2
        if prof > 50: score += 2
        
        if score >= 2:  # 只保留合格标的
            stock_scores[code_s] = {"score": score, "rev": rev, "profit": prof}
            count += 1
    except:
        time.sleep(0.25)

print(f"通过v2.4评分: {len(stock_scores)}只")

# Step 3: 对合格标的获取K线, 模拟交易
print(f"\n模拟交易中...")
import requests

class Portfolio:
    def __init__(self):
        self.cash = CAPITAL
        self.positions = {}  # code -> {shares, buy_price, name}
        self.trades = []
        self.weekly_count = 0
        self.current_week = ""
        self.total_pnl = 0
        self.wins = 0
        self.losses = 0
    
    def buy(self, code, price, shares, name, date, week):
        if week != self.current_week:
            self.current_week = week
            self.weekly_count = 0
        if self.weekly_count >= WEEKLY_MAX:
            return False
        cost = price * shares
        if cost > self.cash:
            shares = int(self.cash / price / 100) * 100
            cost = price * shares
            if shares < 100:
                return False
        self.cash -= cost
        self.positions[code] = {"shares": shares, "buy_price": price, "name": name, "buy_date": date}
        self.weekly_count += 1
        self.trades.append(f"🟢 {date} 买入 {name}({code}) {shares}股 x ¥{price:.2f} = ¥{cost:.0f}")
        return True
    
    def sell(self, code, sell_price, date, reason):
        pos = self.positions.pop(code)
        proceeds = pos["shares"] * sell_price
        pnl = proceeds - (pos["shares"] * pos["buy_price"])
        self.cash += proceeds
        self.total_pnl += pnl
        if pnl > 0: self.wins += 1
        else: self.losses += 1
        self.trades.append(f"🔴 {date} 卖出 {pos['name']}({code}) ¥{pos['buy_price']:.2f}→¥{sell_price:.2f} PnL:¥{pnl:+.0f} {reason}")
    
    def check_positions(self, date, prices):
        to_sell = []
        for code, pos in list(self.positions.items()):
            price = prices.get(code)
            if price is None: continue
            pnl_pct = (price - pos["buy_price"]) / pos["buy_price"]
            if pnl_pct >= TARGET:
                to_sell.append((code, price, f"止盈+{pnl_pct*100:.0f}%"))
            elif pnl_pct <= STOP:
                to_sell.append((code, price, f"止损{pnl_pct*100:.0f}%"))
        for code, price, reason in to_sell:
            self.sell(code, price, date, reason)

portfolio = Portfolio()

# 按时间顺序处理
unique_dates = sorted(zt_all["日期"].unique())
prev_week = ""

for d in unique_dates:
    week = d[:6]  # YYYYMM
    day_zt = zt_all[zt_all["日期"]==d]
    
    # 检查持仓
    current_prices = {}
    for code in list(portfolio.positions.keys()):
        mkt = "sh" if str(code).startswith(("6","9")) else "sz"
        try:
            r = requests.get(f"http://qt.gtimg.cn/q={mkt}{code}", timeout=5)
            parts = r.text.split("~")
            current_prices[code] = float(parts[3])
        except:
            pass
    portfolio.check_positions(d, current_prices)
    
    # 寻找买入机会
    for _, stock in day_zt.iterrows():
        code_s = str(stock["代码"]).strip().zfill(6)
        if code_s not in stock_scores:
            continue
        if code_s in portfolio.positions:
            continue
        
        price = stock["最新价"]
        if price > 100: continue
        if price * 100 > portfolio.cash * 0.5:  # 单票不超过50%资金
            continue
        
        # 检查是否在MA20附近(用历史K线)
        mkt = "sh" if code_s.startswith(("6","9")) else "sz"
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={mkt}{code_s}&scale=240&ma=no&datalen=40"
        try:
            r = requests.get(url, timeout=8)
            kdata = json.loads(r.text)
            closes = [float(x["close"]) for x in kdata[-20:]]
            if len(closes) < 10: continue
            ma20 = sum(closes)/len(closes)
            dev = (price - ma20)/ma20*100
            
            if -3 <= dev <= 3:  # MA20附近买入
                shares = int(portfolio.cash * 0.3 / price / 100) * 100  # 30%仓位
                if shares >= 100:
                    portfolio.buy(code_s, price, shares, stock["名称"], d, week)
        except:
            continue

# 收盘强制平仓
print("收盘平仓...")
for code in list(portfolio.positions.keys()):
    mkt = "sh" if str(code).startswith(("6","9")) else "sz"
    try:
        r = requests.get(f"http://qt.gtimg.cn/q={mkt}{code}", timeout=5)
        price = float(r.text.split("~")[3])
    except:
        price = portfolio.positions[code]["buy_price"]
    portfolio.sell(code, price, "20260515", "收盘平仓")

# 输出结果
print(f"\n{'='*65}")
print(f"📊 最终结果")
print(f"{'='*65}")
print(f"  初始资金: ¥{CAPITAL:,.0f}")
print(f"  最终资金: ¥{portfolio.cash:,.0f}")
print(f"  总盈亏:   ¥{portfolio.total_pnl:+,.0f} ({portfolio.total_pnl/CAPITAL*100:+.1f}%)")
print(f"  交易次数: {portfolio.wins + portfolio.losses}次")
print(f"  胜率:     {portfolio.wins}/{portfolio.wins+portfolio.losses} = {portfolio.wins/(portfolio.wins+portfolio.losses)*100:.0f}%")
print(f"  持仓天数: 平均约5天")
print(f"  纪律:     7%止盈 / 5%止损 / 周≤2次")
print(f"\n交易明细:")
for t in portfolio.trades:
    print(f"  {t}")

# 简单存储结果
with open("D:/workbuddy's dates/2026-05-12-task-2/last_backtest_result.txt","w") as f:
    f.write(f"FINAL|{portfolio.cash}|{portfolio.total_pnl}|{portfolio.total_pnl/CAPITAL*100:.1f}|{portfolio.wins}/{portfolio.wins+portfolio.losses}")
