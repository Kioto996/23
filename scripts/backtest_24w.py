import os, time, requests, json, datetime
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import akshare as ak
import pandas as pd

CAPITAL = 50000
TARGET_PCT = 0.07
STOP_PCT = -0.05
WEEKLY_MAX = 2

print("="*60)
print("v2.4 v4版 6个月回测 (24周)")
print("规则: 偏离-5%~+3% + 放量>2x + 评分≥2 + 高位(>50%涨幅)资金流过滤")
print("时间: 2025/11/17 - 2026/05/15")
print(f"本金: RMB{int(CAPITAL/10000)}万, 止盈+7%, 止损-5%, 每周≤{WEEKLY_MAX}次, v4高位过滤")
print("="*60)

# ====== 1. 获取涨停股票池 (覆盖6个月) ======
zt_dates = [
    # Nov 2025
    "20251117","20251118","20251119","20251120","20251121",
    "20251124","20251125","20251126","20251127","20251128",
    # Dec 2025
    "20251201","20251202","20251203","20251204","20251205",
    "20251208","20251209","20251210","20251211","20251212",
    "20251215","20251216","20251217","20251218","20251219",
    "20251222","20251223","20251224","20251225","20251226",
    "20251229","20251230","20251231",
    # Jan 2026
    "20260105","20260106","20260107","20260108","20260109",
    "20260112","20260113","20260114","20260115","20260116",
    "20260119","20260120","20260121","20260122","20260123",
    "20260126","20260127","20260128","20260129","20260130",
    # Feb 2026
    "20260202","20260203","20260204","20260205","20260206",
    "20260209","20260210","20260211","20260212","20260213",
    "20260216","20260217","20260218","20260219","20260220",
    "20260223","20260224","20260225","20260226","20260227",
    # Mar 2026
    "20260302","20260303","20260304","20260305","20260306",
    "20260309","20260310","20260311","20260312","20260313",
    "20260316","20260317","20260318","20260319","20260320",
    "20260323","20260324","20260325","20260326","20260327",
    "20260330","20260331",
    # Apr 2026
    "20260401","20260402","20260403",
    "20260407","20260408","20260409","20260410",
    "20260413","20260414","20260415","20260416","20260417",
    "20260420","20260421","20260422","20260423","20260424",
    "20260427","20260428","20260429","20260430",
    # May 2026
    "20260506","20260507","20260508",
    "20260511","20260512","20260513","20260514","20260515",
]
print(f"Collecting limit-up data from {len(zt_dates)} trading days...")
all_zt = []
for i, d in enumerate(zt_dates):
    try:
        df = ak.stock_zt_pool_em(date=d)
        time.sleep(0.15)
        df["date"] = d
        all_zt.append(df)
        if (i+1) % 20 == 0:
            print(f"  Progress: {i+1}/{len(zt_dates)} days done")
    except:
        time.sleep(0.2)
        continue

zt_all = pd.concat(all_zt, ignore_index=True) if all_zt else pd.DataFrame()
print(f"Total limit-up records: {len(zt_all)}")

code_col = [c for c in zt_all.columns if "代" in c or "code" in c.lower()][0]
codes_list = list(zt_all[code_col].unique())[:80]  # Top 80 most active
print(f"Unique stocks from limit-up: {len(codes_list)}")

# ====== 2. 基本面评分 (v2.4) ======
print("\nScoring stocks with v2.4...")
stock_scores = {}
for i, code in enumerate(codes_list):
    code_s = str(code).strip().zfill(6)
    if code_s.startswith(("688","300","301","8")): continue  # 排除注册制(科创板+创业板+北交所)
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期")
        time.sleep(0.15)
        l = df.iloc[-1]
        rev = 0.0; prof = 0.0
        try:
            rev = float(str(l.get("营业总收入同比增长率","0")).replace("%",""))
            prof = float(str(l.get("净利润同比增长率","0")).replace("%",""))
        except: pass
        score = (2 if rev > 15 else 0) + (2 if prof > 50 else 0)
        if score >= 2:
            stock_scores[code_s] = {"score":score, "rev":rev, "profit":prof}
    except:
        time.sleep(0.15)
    if (i+1) % 20 == 0:
        print(f"  Scoring: {i+1}/{len(codes_list)}")

print(f"v2.4合格股票: {len(stock_scores)}")

# ====== 3. 获取6个月K线 ======
print("\nFetching 6-month price data (160 trading days)...")
price_history = {}

for i, code_s in enumerate(stock_scores.keys()):
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=160"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        data = json.loads(r.text)
        records = []
        for d in data:
            records.append({
                "date": d["day"], "close": float(d["close"]),
                "high": float(d["high"]), "low": float(d["low"]),
                "volume": int(d["volume"])
            })
        if len(records) >= 60:
            price_history[code_s] = records
    except:
        time.sleep(0.1)
    if (i+1) % 10 == 0:
        print(f"  Price data: {i+1}/{len(stock_scores)}")

print(f"Stocks with full price data: {len(price_history)}")

# ====== 4. 生成24周时间表 ======
# Nov 17, 2025 (Monday) to May 15, 2026 (Friday) = ~24 weeks
weeks = []
start = datetime.date(2025, 11, 17)
for w in range(24):
    mon = start + datetime.timedelta(weeks=w)
    fri = mon + datetime.timedelta(days=4)
    weeks.append((mon.strftime("%Y-%m-%d"), fri.strftime("%Y-%m-%d")))
print(f"\nTrading weeks: {len(weeks)} ({weeks[0][0]} ~ {weeks[-1][1]})")

# ====== 5. 模拟交易 ======
cash = CAPITAL
positions = {}
trades = []
total_pnl = 0
wins = 0
losses = 0
weekly_equity = [CAPITAL]  # W0 starting capital

for week_num, (mon_date, fri_date) in enumerate(weeks):
    weekly_trades = 0
    
    # Check existing positions (sell check on Friday)
    for code in list(positions.keys()):
        if code not in price_history: continue
        hist = price_history[code]
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
                trades.append(f"[W{week_num+1}] SELL {pos['name']} +{int(pnl_pct*100)}% PnL:{int(pnl):+}")
                if pnl > 0: wins += 1; pos["result"] = "win"
                else: losses += 1; pos["result"] = "loss"
                del positions[code]
            elif pnl_pct <= STOP_PCT:
                proceeds = pos["shares"] * price
                pnl = proceeds - (pos["shares"] * pos["buy_price"])
                cash += proceeds
                total_pnl += pnl
                trades.append(f"[W{week_num+1}] STOP {pos['name']} {int(pnl_pct*100)}% PnL:{int(pnl):+}")
                if pnl > 0: wins += 1; pos["result"] = "win"
                else: losses += 1; pos["result"] = "loss"
                del positions[code]
    
    # Find buy opportunities (on Monday)
    candidates = []
    for code_s, info in stock_scores.items():
        if code_s in positions: continue
        if code_s not in price_history: continue
        
        hist = price_history[code_s]
        mon_record = None
        for r in hist:
            if r["date"] >= mon_date:
                mon_record = r
                break
        if mon_record is None: continue
        
        if code_s.startswith(("688","300","301","8")): continue  # 排除注册制(科创板+创业板+北交所)
        
        price = mon_record["close"]
        if price > 100: continue
        if price * 100 > cash * 0.5: continue
        
        idx = hist.index(mon_record)
        if idx < 25: continue
        
        # Calculate MA20
        ma20_closes = [hist[i]["close"] for i in range(idx-20, idx)]
        ma20 = sum(ma20_closes)/20
        dev = (price - ma20)/ma20*100
        
        # v4: 高位资金流过滤 (60日涨幅>50%时检查)
        if idx >= 60:
            low_60 = min(hist[j]["close"] for j in range(idx-60, idx+1))
            runup = (price - low_60) / low_60 * 100
            if runup > 50:
                # 近3日成交量 vs 前10日
                recent_v = sum(hist[j]["volume"] for j in range(idx-3, idx)) / 3
                prior_v = sum(hist[j]["volume"] for j in range(idx-13, idx-3)) / 10
                if prior_v > 0 and recent_v > prior_v * 1.2:  # 高位放量
                    declines = sum(1 for j in range(idx-3, idx) if hist[j]["close"] < hist[j-1]["close"])
                    if declines >= 2:  # 高位放量+下跌=出货
                        continue
        
        # Volume breakout check (within last 15 trading days)
        vol_break = False
        for vi in range(max(0, idx-15), idx):
            lookback = min(15, vi)
            if lookback < 5: continue
            avg_vol_before = sum(h["volume"] for h in hist[vi-lookback:vi])/lookback
            if avg_vol_before > 0 and hist[vi]["volume"] > avg_vol_before * 2:
                vol_break = True
                break
        
        if vol_break and -5 <= dev <= 3:
            candidates.append((code_s, info, price, dev, mon_record["date"]))
    
    candidates.sort(key=lambda x: x[1]["score"], reverse=True)
    for code_s, info, price, dev, buy_date in candidates[:WEEKLY_MAX]:
        if weekly_trades >= WEEKLY_MAX: break
        
        shares = int(cash * 0.3 / price / 100) * 100
        if shares < 100: continue
        cost = price * shares
        cash -= cost
        positions[code_s] = {"shares": shares, "buy_price": price, "name": code_s, "week": week_num+1}
        weekly_trades += 1
        trades.append(f"[W{week_num+1}] BUY  {code_s} {shares}sh x{price:.2f} dev:{dev:+.1f}% ={int(cost):,}")
    
    # Record weekly equity (liquidate positions at Friday prices for NAV calc)
    pos_value = 0
    for code, pos in positions.items():
        if code not in price_history: continue
        hist = price_history[code]
        fri_rec = None
        for r in hist:
            if r["date"] <= fri_date:
                fri_rec = r
        if fri_rec:
            pos_value += pos["shares"] * fri_rec["close"]
        else:
            pos_value += pos["shares"] * pos["buy_price"]
    nav = cash + pos_value
    weekly_equity.append(round(nav, 2))

# Close remaining positions
for code in list(positions.keys()):
    if code not in price_history: continue
    pos = positions[code]
    last = price_history[code][-1]
    price = last["close"]
    proceeds = pos["shares"] * price
    pnl = proceeds - (pos["shares"] * pos["buy_price"])
    cash += proceeds
    total_pnl += pnl
    trades.append(f"[CLOSE] {code} PnL:{int(pnl):+}")
    if pnl > 0: wins += 1
    else: losses += 1

final_equity = weekly_equity[-1]
total_trades = wins + losses

# ====== 完整回测指标 ======
import math

# 周收益率序列 (从周净值计算)
weekly_returns = []
for w in range(1, len(weekly_equity)):
    r = (weekly_equity[w] - weekly_equity[w-1]) / weekly_equity[w-1]
    weekly_returns.append(r)

# 1. 年化收益率
total_weeks = len(weekly_returns)
annual_return = (final_equity / CAPITAL) ** (52.0 / total_weeks) - 1 if total_weeks > 0 else 0

# 2. 夏普比率 (无风险利率按2%年化, 约0.0385%/周)
risk_free = 0.02 / 52
avg_return = sum(weekly_returns) / len(weekly_returns) if weekly_returns else 0
var_return = sum((r - avg_return)**2 for r in weekly_returns) / len(weekly_returns) if weekly_returns else 0
std_return = math.sqrt(var_return)
sharpe = (avg_return - risk_free) / std_return * math.sqrt(52) if std_return > 0 else 0

# 3. 最大回撤 (已算)
dd = min_nav = min(weekly_equity)
peak_before = max(weekly_equity[:weekly_equity.index(min_nav)+1]) if min_nav != weekly_equity[0] else CAPITAL
max_dd_pct = (min_nav - peak_before) / peak_before * 100

# 4. 卡玛比率
calmar = annual_return / (abs(max_dd_pct)/100) if max_dd_pct < 0 else 0

# 5. 盈亏比
win_pnls = []
loss_pnls = []
for t in trades:
    import re
    m = re.search(r'PnL:([+-]?\d+)', t)
    if m:
        p = int(m.group(1))
        if p > 0: win_pnls.append(p)
        elif p < 0: loss_pnls.append(p)
avg_win = sum(win_pnls)/len(win_pnls) if win_pnls else 0
avg_loss = abs(sum(loss_pnls)/len(loss_pnls)) if loss_pnls else 0
profit_loss_ratio = avg_win/avg_loss if avg_loss > 0 else 0

# 6. 最大连续亏损
consecutive_losses = 0
max_consec_loss = 0
for t in trades:
    m = re.search(r'PnL:([+-]?\d+)', t)
    if m:
        p = int(m.group(1))
        if p < 0:
            consecutive_losses += 1
            max_consec_loss = max(max_consec_loss, consecutive_losses)
        else:
            consecutive_losses = 0
win_rate = int(wins/total_trades*100) if total_trades > 0 else 0
total_return = (final_equity - CAPITAL) / CAPITAL * 100

print("\n" + "="*60)
print("24-WEEK (6 MONTH) BACKTEST RESULTS")
print("="*60)
print(f"  Period:    {weeks[0][0]} ~ {weeks[-1][1]}")
print(f"  Starting:  RMB {CAPITAL:,.0f}")
print(f"  Ending:    RMB {int(final_equity):,}")
print(f"  Return:    {total_return:+.1f}% (PnL: {int(total_pnl):+,})")
print(f"  Trades:    {total_trades}")
print(f"  Win Rate:  {wins}/{total_trades} = {win_rate}%")
print(f"  —— 量化指标 ——")
print(f"  年化收益:  {annual_return*100:.1f}%")
print(f"  夏普比率:  {sharpe:.2f}")
print(f"  卡玛比率:  {calmar:.2f}")
print(f"  最大回撤:  {max_dd_pct:.1f}%")
print(f"  盈亏比:    {profit_loss_ratio:.2f} (平均盈利{int(avg_win):,} / 平均亏损{int(avg_loss):,})")
print(f"  最大连亏:  {max_consec_loss}笔")

# 7. 月度胜率
from collections import defaultdict
monthly = defaultdict(lambda: {"w":0,"l":0})
for t in trades:
    m = re.search(r'\[(\d{4}-\d{2})-\d{2}\] (\w+) .*PnL:([+-]?\d+)', t)
    if m:
        month = m.group(1)
        pnl = int(m.group(3))
        if pnl > 0: monthly[month]["w"] += 1
        elif pnl < 0: monthly[month]["l"] += 1
print(f"\n  月度胜率:")
for m in sorted(monthly.keys()):
    mt = monthly[m]
    mr = mt["w"]/(mt["w"]+mt["l"])*100 if (mt["w"]+mt["l"]) > 0 else 0
    print(f"    {m}: {mt['w']}胜{mt['l']}负 ({mr:.0f}%)")
print(f"  Peak NAV:  RMB {int(max(weekly_equity)):,}")
min_nav = min(weekly_equity)
dd = (min_nav - max(weekly_equity[:weekly_equity.index(min_nav)+1])) / max(weekly_equity[:weekly_equity.index(min_nav)+1]) * 100 if len(weekly_equity) > 1 else 0
print(f"  Max DD:    {dd:.1f}%")
print(f"\nTrade Log ({len(trades)} entries):")
for t in trades:
    print(f"  {t}")

# ====== 6. 生成HTML报告 ======
weekly_labels = ["W0"] + [f"W{w+1}" for w in range(24)]

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>v2.4 6个月回测报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#0d1117;color:#e6edf3;padding:20px;line-height:1.6}
.container{max-width:1000px;margin:0 auto}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);border:1px solid #30363d;border-radius:12px;padding:28px 32px;margin-bottom:20px}
.header h1{font-size:24px}
.header .sub{color:#8b949e;font-size:13px}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px 24px;margin-bottom:16px}
.card h2{font-size:17px;margin-bottom:14px;color:#f0f6fc;border-bottom:1px solid #21262d;padding-bottom:10px}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.stat{background:#0d1117;border-radius:8px;padding:12px 16px;border:1px solid #21262d}
.stat .lbl{font-size:11px;color:#8b949e}
.stat .val{font-size:22px;font-weight:600;margin-top:4px}
.val.green{color:#3fb950}.val.red{color:#f85149}.val.yellow{color:#d29922}.val.gold{color:#d4a843}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
th,td{padding:5px 8px;text-align:left;border-bottom:1px solid #21262d;word-break:break-all}
th{color:#8b949e;font-weight:500;font-size:10px}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;margin:2px}
.tag.green{background:rgba(63,185,80,0.15);color:#3fb950}
.tag.red{background:rgba(248,81,73,0.15);color:#f85149}
.tag.yellow{background:rgba(210,153,34,0.15);color:#d29922}
.tag.blue{background:rgba(88,166,255,0.15);color:#58a6ff}
.chart-box{height:300px;position:relative;margin-top:10px}
.chart-sm{height:200px;margin-top:10px}
.footer{text-align:center;color:#484f58;font-size:12px;padding:20px;margin-top:20px;border-top:1px solid #21262d}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>v2.4 6个月回测报告</h1>
<div class="sub">2025/11/17 - 2026/05/15 · 24周 · 基本面评分v2.4 + MA20回踩买入</div>
<div class="grid-4" style="margin-top:16px">
<div class="stat"><div class="lbl">总收益</div><div class="val green">+""" + f"{total_return:.1f}%" + """</div></div>
<div class="stat"><div class="lbl">胜率</div><div class="val">""" + f"{wins}/{total_trades} ({win_rate}%)" + """</div></div>
<div class="stat"><div class="lbl">最大回撤</div><div class="val yellow">""" + f"{dd:.1f}%" + """</div></div>
<div class="stat"><div class="lbl">结束权益</div><div class="val gold">¥""" + f"{int(final_equity):,}" + """</div></div>
</div>
</div>

<div class="card">
<h2>24周收益曲线</h2>
<div class="chart-box"><canvas id="equityChart"></canvas></div>
</div>

<div class="card">
<h2>策略核心逻辑</h2>
<div class="grid-3">
<div class="stat"><div class="lbl">Step 1</div><div class="val" style="font-size:15px;color:#58a6ff">v2.4 评分≥2</div><div class="lbl">营收同比>15% + 净利同比>50%</div></div>
<div class="stat"><div class="lbl">Step 2</div><div class="val" style="font-size:15px;color:#58a6ff">放量突破</div><div class="lbl">成交量>2倍15日均量</div></div>
<div class="stat"><div class="lbl">Step 3</div><div class="val" style="font-size:15px;color:#3fb950">回踩MA20买入</div><div class="lbl">偏离-5%~+3%, 30%仓位, 每周≤2次</div></div>
</div>
</div>

<div class="card">
<h2>周度权益明细</h2>
<div style="max-height:300px;overflow-y:auto">
<table>"""

# Table: week, NAV, change
html += "<tr><th>周次</th><th>日期</th><th>净值(¥)</th><th>周变动</th><th>累计收益</th></tr>"
for w in range(len(weekly_equity)):
    eq = weekly_equity[w]
    chg = 0
    if w > 0:
        chg = (eq - weekly_equity[w-1]) / weekly_equity[w-1] * 100
    cum = (eq - CAPITAL) / CAPITAL * 100
    date_label = "开始" if w == 0 else f"W{w}"
    week_date = weeks[w-1][1] if w > 0 else weeks[0][0]
    chg_cls = "green" if chg >= 0 else "red"
    cum_cls = "green" if cum >= 0 else "red"
    html += f'<tr><td>{date_label}</td><td style="font-size:11px">{week_date}</td><td>¥{int(eq):,}</td><td class="{chg_cls}">{chg:+.1f}%</td><td class="{cum_cls}">{cum:+.1f}%</td></tr>'

html += """</table></div></div>

<div class="card">
<h2>交易明细（最近20笔）</h2>
<div style="max-height:300px;overflow-y:auto">
<table><tr><th>交易</th></tr>"""

# Show last 20 trades
for t in trades[-20:]:
    cls = "green" if "SELL" in t and "+" in t.split("PnL")[-1] else "red" if "STOP" in t else ""
    html += f'<tr><td class="{cls}" style="font-size:11px;font-family:monospace">{t}</td></tr>'

html += "</table></div></div>"

# Buy signals section (current market scan)
print("\n\nScanning current buy signals...")
now = datetime.date.today().isoformat()
buy_signals = []
analysis_list = []

for code_s, info in stock_scores.items():
    if code_s not in price_history: continue
    if code_s.startswith(("688","300","301","8")): continue  # 排除注册制(科创板+创业板+北交所)
    
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    hist = price_history[code_s]
    if len(hist) < 30: continue
    
    closes = [r["close"] for r in hist]
    ma20 = sum(closes[-20:])/20
    current = closes[-1]
    dev = (current - ma20)/ma20*100
    chg6m = (closes[-1]-closes[0])/closes[0]*100
    
    vols = [r["volume"] for r in hist]
    avg_vol = sum(vols[-25:-5])/20 if len(vols) > 25 else sum(vols[:-5])/(len(vols)-5)
    max_vol_r = max(vols[-15:])/avg_vol if avg_vol > 0 else 0
    
    is_buy = (dev >= -5 and dev <= 3) and max_vol_r >= 1.5 and current <= 100
    
    analysis_list.append({
        "code": code_s, "score": info["score"],
        "rev": info["rev"], "profit": info["profit"],
        "price": round(current, 2), "ma20": round(ma20, 2), "dev": round(dev, 1),
        "chg6m": round(chg6m, 1), "vol_ratio": round(max_vol_r, 1),
        "buy_signal": is_buy
    })

if analysis_list:
    buy_signals = [a for a in analysis_list if a["buy_signal"]]
    
    html += f'<div class="card"><h2>当前买入信号 (24周回测框架)</h2>'
    if buy_signals:
        html += f'<p style="color:#3fb950;font-size:13px;margin-bottom:8px">找到 {len(buy_signals)} 个买入信号</p>'
        html += '<table><tr><th>代码</th><th>评分</th><th>营收同比</th><th>净利同比</th><th>现价</th><th>MA20</th><th>偏离</th><th>放量比</th><th>6月涨幅</th><th>买点</th><th>止损</th></tr>'
        for s in sorted(buy_signals, key=lambda x: x["score"], reverse=True)[:10]:
            buy_level = round(s["ma20"] * 1.01, 2)
            stop_level = round(s["ma20"] * 0.95, 2)
            vol_tag = f'<span class="tag green">{s["vol_ratio"]}x</span>' if s["vol_ratio"] >= 2 else f'<span class="tag yellow">{s["vol_ratio"]}x</span>'
            html += f'<tr><td style="font-size:11px">{s["code"]}</td>'
            html += f'<td><span class="tag blue">{s["score"]}分</span></td><td>+{s["rev"]:.1f}%</td><td>+{s["profit"]:.1f}%</td>'
            html += f'<td>¥{s["price"]:.2f}</td><td>¥{s["ma20"]}</td>'
            html += f'<td style="color:#3fb950">{s["dev"]:+.1f}%</td><td>{vol_tag}</td>'
            html += f'<td>{s["chg6m"]:+.1f}%</td><td style="color:#3fb950">¥{buy_level}</td><td style="color:#f85149">¥{stop_level}</td></tr>'
        html += '</table>'
    else:
        html += '<p style="color:#8b949e">当前没有符合买入条件的标的</p>'
    html += '</div>'
    
    # Waiting for pullback section
    wait_list = [a for a in analysis_list if not a["buy_signal"] and -15 < a["dev"] < 15 and a["dev"] > 3]
    if wait_list:
        html += f'<div class="card"><h2>等待回调标的（已放量上涨，等MA20）</h2>'
        html += '<table><tr><th>代码</th><th>评分</th><th>营收同比</th><th>净利同比</th><th>现价</th><th>MA20</th><th>偏离</th><th>需跌到</th></tr>'
        for s in sorted(wait_list, key=lambda x: x["score"], reverse=True)[:8]:
            target = round(s["ma20"], 2)
            need_drop = round((s["ma20"] - s["price"]) / s["price"] * 100, 1)
            html += f'<tr><td style="font-size:11px">{s["code"]}</td>'
            html += f'<td><span class="tag blue">{s["score"]}分</span></td><td>+{s["rev"]:.1f}%</td><td>+{s["profit"]:.1f}%</td>'
            html += f'<td>¥{s["price"]:.2f}</td><td>¥{s["ma20"]}</td>'
            html += f'<td style="color:#d29922">{s["dev"]:+.1f}%</td><td>再跌{need_drop:.0f}%</td></tr>'
        html += '</table></div>'

html += """
<div class="card">
<h2>操作规则</h2>
<table>
<tr><th>规则</th><th>内容</th></tr>
<tr><td>选股</td><td>v2.4评分≥2分 (营收同比>15% + 净利同比>50%), 从涨停池扫描</td></tr>
<tr><td>买入</td><td>放量突破(>2倍15日均量)后回踩MA20(偏离-5%~+3%)</td></tr>
<tr><td>仓位</td><td>单票≤30%资金, 同时≤2只, 每周≤2次买入</td></tr>
<tr><td>止损</td><td>-5% (跌破MA20 95%无条件卖出)</td></tr>
<tr><td>止盈</td><td>+7%保底</td></tr>
<tr><td>不追</td><td>偏离>+5%不买, 等回调</td></tr>
</table>
</div>"""

import json
weekly_labels_json = json.dumps(weekly_labels)
weekly_equity_json = json.dumps(weekly_equity)

# Weekly PnL bar chart data
weekly_pnl = [0]
for w in range(1, len(weekly_equity)):
    weekly_pnl.append(round(weekly_equity[w] - weekly_equity[w-1], 2))

html += f"""
<div class="card">
<h2>周度收益柱状图</h2>
<div class="chart-sm"><canvas id="pnlChart"></canvas></div>
</div>
</div>

<script>
new Chart(document.getElementById("equityChart"), {{
  type: "line",
  data: {{
    labels: {weekly_labels_json},
    datasets: [{{
      label: "账户净值",
      data: {weekly_equity_json},
      borderColor: "#3fb950",
      backgroundColor: "rgba(63,185,80,0.1)",
      fill: true,
      tension: 0.3,
      pointBackgroundColor: "#3fb950",
      pointRadius: 3
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ color:"#8b949e", font:{{size:10}}, maxTicksLimit:12 }} }},
      y: {{ grid: {{ color:"rgba(139,148,158,0.1)" }}, ticks: {{ color:"#8b949e", font:{{size:11}}, callback: v => "¥"+v/10000+"万" }} }}
    }}
  }}
}});

new Chart(document.getElementById("pnlChart"), {{
  type: "bar",
  data: {{
    labels: {weekly_labels_json},
    datasets: [{{
      label: "周收益",
      data: {json.dumps(weekly_pnl)},
      backgroundColor: {json.dumps(["rgba(48,48,48,0.5)"] + ["rgba(63,185,80,0.7)" if weekly_pnl[i] >= 0 else "rgba(248,81,73,0.7)" for i in range(1, len(weekly_pnl))])},
      borderColor: {json.dumps(["transparent"] + ["#3fb950" if weekly_pnl[i] >= 0 else "#f85149" for i in range(1, len(weekly_pnl))])},
      borderWidth: 1
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ color:"#8b949e", font:{{size:9}}, maxTicksLimit:12 }} }},
      y: {{ grid: {{ color:"rgba(139,148,158,0.1)" }}, ticks: {{ color:"#8b949e", font:{{size:10}}, callback: v => "¥"+v }}}}
    }}
  }}
}});
</script>
<div class="footer">数据源: 同花顺THS + 新浪财经 | 回测: 24周 (2025/11/17-2026/05/15) | 本金5万 | ⚠️ 仅供参考不构成投资建议</div>
</body></html>"""

report_path = "D:/workbuddy's dates/2026-05-12-task-2/v24_6m回测报告.html"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n{'='*60}")
print(f"报告已生成: {report_path}")
print(f"6个月回测总收益: {total_return:+.1f}%")
print(f"胜率: {wins}/{total_trades} ({win_rate}%)")
print(f"当前买入信号: {len(buy_signals)} 个")
print(f"{'='*60}")
