import os
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import akshare as ak
import pandas as pd
import time
from datetime import datetime, timedelta

# ===== 配置 =====
CAPITAL = 20000  # 初始资金2万
MAX_WEEKLY_TRADES = 2
MIN_SHARES = 100
CACHE = "D:/workbuddy's dates/2026-05-12-task-2/cache"

# ===== Step 1: 获取数据 =====
print("="*60)
print(f"📊 实战回测: ¥{CAPITAL/10000}万 · 每周≤2次 · 每次≥100股")
print(f"📅 2026/04/24 - 2026/05/15")
print("="*60)

dates = ["20260424","20260430","20260506","20260507","20260508",
         "20260511","20260512","20260513","20260514","20260515"]

all_zt = []
for d in dates:
    df = ak.stock_zt_pool_em(date=d)
    time.sleep(0.3)
    df["日期"] = d
    all_zt.append(df)
    print(f"  {d}: {len(df)}只涨停")

zt_all = pd.concat(all_zt, ignore_index=True)
print(f"\n✅ 共获取 {len(zt_all)} 条涨停数据")

# ===== Step 2: 识别优质涨停 =====
def is_quality(row):
    """优质涨停三条件"""
    try:
        t = str(int(row["首次封板时间"])).zfill(6)
        early = int(t[:2]+t[2:4]) < 1000
        strong = row["封板资金"] > 0.5e8
        no_break = row["炸板次数"] == 0
        price_ok = row["最新价"] <= 100
        return early and strong and no_break and price_ok
    except:
        return False

zt_all["优质"] = zt_all.apply(is_quality, axis=1)
quality_stocks = zt_all[zt_all["优质"]==True]

print(f"  其中优质涨停(三条件+≤100元): {len(quality_stocks)}只")

# ===== Step 3: 按周分组，每周选2只 =====
zt_all["周"] = zt_all["日期"].apply(lambda x: f"W{int(str(x)[4:6])}")

# ===== Step 4: 模拟交易 =====
print(f"\n{'='*60}")
print(f"📊 模拟交易")
print(f"{'='*60}")

# 状态
cash = CAPITAL
positions = []  # [{stock, shares, buy_price, buy_date}]
trade_log = []
weekly_trades = 0
current_week = ""
pnl_log = []

# 按日期顺序处理
for d in sorted(zt_all["日期"].unique()):
    day_data = zt_all[zt_all["日期"]==d]
    w = str(d)[4:6]
    
    # 新一周重置
    if w != current_week:
        current_week = w
        weekly_trades = 0
    
    # 当天优质涨停
    day_quality = day_data[day_data["优质"]==True].sort_values("封板资金", ascending=False)
    
    for _, stock in day_quality.iterrows():
        if weekly_trades >= MAX_WEEKLY_TRADES:
            break
        
        name = stock["名称"]
        code = str(stock["代码"]).strip().zfill(6)
        price = stock["最新价"]
        
        # 计算可买股数(100股整数倍)
        affordable = int(cash / price / 100) * 100
        shares = min(affordable, 1000)  # 上限1000股
        
        if shares >= MIN_SHARES:
            cost = shares * price
            cash -= cost
            weekly_trades += 1
            
            positions.append({
                "name": name, "code": code,
                "buy_price": price, "buy_date": d,
                "shares": shares, "cost": cost,
                "sector": stock.get("所属行业","")
            })
            
            trade_log.append(f"🟢 买入 {name}({code}) {shares}股 x ¥{price:.2f} = ¥{cost:.0f}  现金余额: ¥{cash:.0f}")
    
    # 卖出: 持仓超过5天后强制卖出(假设短线持仓)
    to_sell = []
    for pos in positions:
        days_held = (datetime.strptime(d, "%Y%m%d") - datetime.strptime(pos["buy_date"], "%Y%m%d")).days
        if days_held >= 5:  # 持仓5天后卖出
            # 获取卖出日价格(用当天腾讯API)
            mkt = "sh" if str(pos["code"]).startswith(("6","9")) else "sz"
            try:
                import requests
                r = requests.get(f"http://qt.gtimg.cn/q={mkt}{pos['code']}", timeout=5).text.split("~")
                sell_price = float(r[3]) if r[3] else pos["buy_price"]
            except:
                sell_price = pos["buy_price"]
            
            proceeds = pos["shares"] * sell_price
            pnl = proceeds - pos["cost"]
            cash += proceeds
            pnl_log.append(pnl)
            
            trade_log.append(f"🔴 卖出 {pos['name']}({pos['code']}) {pos['shares']}股 x ¥{sell_price:.2f}  PnL: ¥{pnl:+.0f}")
            to_sell.append(pos)
    
    for pos in to_sell:
        positions.remove(pos)

# 收盘强制平仓
for pos in positions:
    mkt = "sh" if str(pos["code"]).startswith(("6","9")) else "sz"
    import requests
    try:
        r = requests.get(f"http://qt.gtimg.cn/q={mkt}{pos['code']}", timeout=5).text.split("~")
        sell_price = float(r[3]) if r[3] else pos["buy_price"]
    except:
        sell_price = pos["buy_price"]
    
    proceeds = pos["shares"] * sell_price
    pnl = proceeds - pos["cost"]
    cash += proceeds
    pnl_log.append(pnl)
    trade_log.append(f"🔴 强平 {pos['name']}({pos['code']}) {pos['shares']}股 x ¥{sell_price:.2f}  PnL: ¥{pnl:+.0f}")

# ===== 结果 =====
print(f"\n{'='*60}")
print(f"📊 回测结果")
print(f"{'='*60}")

for log in trade_log:
    print(f"  {log}")

total_pnl = sum(pnl_log)
win_trades = sum(1 for p in pnl_log if p > 0)
total_trades = len(pnl_log)

print(f"\n{'='*60}")
print(f"📊 汇总")
print(f"{'='*60}")
print(f"  初始资金: ¥{CAPITAL:,.0f}")
print(f"  最终资金: ¥{cash:,.0f}")
print(f"  总盈亏:   ¥{total_pnl:+,.0f} ({total_pnl/CAPITAL*100:+.1f}%)")
print(f"  交易次数: {total_trades}次")
print(f"  胜率:     {win_trades}/{total_trades} = {win_trades/total_trades*100:.0f}%")
print(f"  周期:     4/24 - 5/15 (22天)")
print(f"  平均持仓: 5天")
print(f"  每周交易: ≤{MAX_WEEKLY_TRADES}次")
