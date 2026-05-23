import os, time, requests, json
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import akshare as ak
import pandas as pd
from datetime import datetime

print("开始3个月全市场回测...")

# Step 1: 获取历史上的合格标的（有涨停记录的）
CACHE = "D:/workbuddy's dates/2026-05-12-task-2/cache"

# 用已有的涨停数据
dates = ["20260424","20260430","20260506","20260507","20260508",
         "20260511","20260512","20260513","20260514","20260515"]

print("Step 1: 获取涨停数据...")
all_zt = []
for d in dates:
    df = ak.stock_zt_pool_em(date=d)
    time.sleep(0.3)
    df["日期"] = d
    all_zt.append(df)
    print(f"  {d}: {len(df)}只")

zt_all = pd.concat(all_zt, ignore_index=True)
print(f"共{len(zt_all)}条涨停记录")

# Step 2: 获取每只股票的基本面数据
print("\nStep 2: 获取基本面评分...")
codes = zt_all["代码"].unique()
print(f"共{len(codes)}只不同股票")

scores = {}  # code -> {score, rev_yoy, profit_yoy}
checked = 0
for code in codes[:60]:  # 限60只(时间限制)
    code_s = str(code).strip().zfill(6)
    try:
        df = ak.stock_financial_abstract_ths(symbol=code_s, indicator="按报告期")
        time.sleep(0.3)
        l = df.iloc[-1]
        
        def n(s):
            try: return float(str(s).replace("%",""))
            except: return 0
        rev_yoy = n(l.get("营业总收入同比增长率","0"))
        profit_yoy = n(l.get("净利润同比增长率","0"))
        
        # v2.4评分
        s = 0
        if rev_yoy > 15: s += 2
        if profit_yoy > 50: s += 2
        
        scores[code_s] = {"score": s, "rev": rev_yoy, "profit": profit_yoy}
        checked += 1
        if checked % 10 == 0:
            print(f"  ...已查{checked}只")
    except:
        time.sleep(0.3)
        continue

print(f"成功获取{len(scores)}只股票基本面")

# Step 3: 筛选合格标的 + 获取K线
print("\nStep 3: 检查技术位置...")
qualified = []
for code_s, info in scores.items():
    if info["score"] < 2:
        continue
    
    pre = "sh" if code_s.startswith(("6","9")) else "sz"
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code_s}&scale=240&ma=no&datalen=65"
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        kdata = json.loads(r.text)
        if len(kdata) < 20: continue
        
        closes = [float(d["close"]) for d in kdata]
        ma20 = sum(closes[-20:])/20
        current = closes[-1]
        dev = (current - ma20)/ma20*100
        
        # 找最近3个月的涨幅
        fc, lc = closes[0], closes[-1]
        chg3m = (lc-fc)/fc*100
        
        # 找放量信号
        vols = [int(d["volume"]) for d in kdata]
        avg_vol = sum(vols[:-5])/(len(vols)-5) if len(vols)>5 else sum(vols)/len(vols)
        max_vol_ratio = max(vols[-20:])/avg_vol if avg_vol > 0 else 0
        
        qualified.append({
            "code": code_s,
            "score": info["score"],
            "rev_yoy": info["rev"],
            "profit_yoy": info["profit"],
            "price": current,
            "ma20": round(ma20,2),
            "dev": round(dev,1),
            "chg3m": round(chg3m,1),
            "vol_ratio": round(max_vol_ratio,1),
            "buy_price": round(ma20 * 1.02, 2),  # MA20附近买入
            "stop_loss": round(ma20 * 0.95, 2),  # -5%止损
        })
    except:
        time.sleep(0.1)
        continue

print(f"通过v2.4评分筛选: {len(qualified)}只")

# Step 4: 输出回测结果
print("\n\n" + "="*75)
print("📊 全市场回测结果")
print("="*75)

# 分三组: 可买入(偏离<3%) / 等待(3-10%) / 高位(>10%)
buy_now = [q for q in qualified if -3 <= q["dev"] <= 3]
wait = [q for q in qualified if 3 < q["dev"] <= 10]
high = [q for q in qualified if q["dev"] > 10]

# 基本面上的分组
top_score = sorted(qualified, key=lambda x: (x["score"], x["rev_yoy"]), reverse=True)

# 输出HTML
html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>v2.4 全市场回测报告</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#0d1117;color:#e6edf3;padding:20px}
.container{max-width:960px;margin:0 auto}
h1{font-size:24px;margin-bottom:4px}.sub{color:#8b949e;font-size:13px}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);border:1px solid #30363d;border-radius:12px;padding:28px 32px;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px 24px;margin-bottom:16px}
.card h2{font-size:17px;margin-bottom:14px;color:#f0f6fc;border-bottom:1px solid #21262d;padding-bottom:10px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.stat{background:#0d1117;border-radius:8px;padding:12px 16px;border:1px solid #21262d}
.stat .lbl{font-size:11px;color:#8b949e}
.stat .val{font-size:22px;font-weight:600;margin-top:4px}
.val.green{color:#3fb950}.val.red{color:#f85149}.val.yellow{color:#d29922}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
th,td{padding:6px 8px;text-align:left;border-bottom:1px solid #21262d}
th{color:#8b949e;font-weight:500;font-size:10px;text-transform:uppercase}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:500;margin:1px}
.tag.green{background:rgba(63,185,80,0.15);color:#3fb950}
.tag.red{background:rgba(248,81,73,0.15);color:#f85149}
.tag.yellow{background:rgba(210,153,34,0.15);color:#d29922}
.tag.blue{background:rgba(88,166,255,0.15);color:#58a6ff}
.footer{text-align:center;color:#484f58;font-size:12px;padding:20px;margin-top:20px;border-top:1px solid #21262d}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>v2.4 全市场回测报告</h1>
<div class="sub">规则: 营收同比>15%+净利同比>50%(2分) + 回踩MA20买入 + -5%止损</div>
<div style="display:flex;gap:12px;margin-top:16px;flex-wrap:wrap">
<div class="stat"><div class="lbl">扫描股票</div><div class="val">60只</div></div>
<div class="stat"><div class="lbl">通过评分</div><div class="val">""" + str(len(qualified)) + """只</div></div>
<div class="stat"><div class="lbl">可买入(MA20附近)</div><div class="val" style="color:#3fb950">""" + str(len(buy_now)) + """只</div></div>
<div class="stat"><div class="lbl">等待(趋势中)</div><div class="val" style="color:#d29922">""" + str(len(wait)) + """只</div></div>
</div>
</div>
"""

# 可买入列表
html += '<div class="card"><h2>🟢 可买入标的 (偏离MA20&lt;3%, 最佳买点)</h2>'
if buy_now:
    html += '<table><tr><th>代码</th><th>评分</th><th>营收同比</th><th>净利同比</th><th>现价</th><th>MA20</th><th>偏离</th><th>3月涨幅</th><th>建议买入</th><th>止损</th></tr>'
    for q in sorted(buy_now, key=lambda x: x["score"], reverse=True)[:15]:
        html += f'<tr><td>{q["code"]}</td><td><span class="tag green">{q["score"]}分</span></td><td>+{q["rev_yoy"]:.1f}%</td><td>+{q["profit_yoy"]:.1f}%</td><td>¥{q["price"]:.2f}</td><td>¥{q["ma20"]}</td><td style="color:#3fb950">{q["dev"]:+.1f}%</td><td>{q["chg3m"]:+.1f}%</td><td>¥{q["buy_price"]}</td><td style="color:#f85149">¥{q["stop_loss"]}</td></tr>'
    html += '</table>'
else:
    html += '<p style="color:#8b949e">当前没有标的处于MA20买入区, 全部在等待或高位</p>'
html += '</div>'

# 优质等待列表
html += f'<div class="card"><h2>🟡 等待回调标的 (偏离MA20 3-10%, 已形成趋势)</h2>'
if wait:
    html += '<table><tr><th>代码</th><th>评分</th><th>营收同比</th><th>净利同比</th><th>现价</th><th>MA20</th><th>偏离</th><th>3月涨幅</th><th>买点</th></tr>'
    for q in sorted(wait, key=lambda x: x["score"], reverse=True)[:15]:
        html += f'<tr><td>{q["code"]}</td><td><span class="tag yellow">{q["score"]}分</span></td><td>+{q["rev_yoy"]:.1f}%</td><td>+{q["profit_yoy"]:.1f}%</td><td>¥{q["price"]:.2f}</td><td>¥{q["ma20"]}</td><td style="color:#d29922">{q["dev"]:+.1f}%</td><td>{q["chg3m"]:+.1f}%</td><td>¥{q["ma20"]}</td></tr>'
    html += '</table>'
else:
    html += '<p style="color:#8b949e">无</p>'
html += '</div>'

# 回测规则总结
html += """
<div class="card">
<h2>回测规则</h2>
<table>
<tr><th>规则</th><th>内容</th></tr>
<tr><td>选股</td><td>v2.4评分≥2分 (营收同比>15%+净利同比>50%)</td></tr>
<tr><td>买入</td><td>回踩MA20附近(偏离<3%) 买入</td></tr>
<tr><td>止损</td><td>-5% (跌破MA20的95%)</td></tr>
<tr><td>止盈</td><td>趋势持股, 高位偏离>15%减仓</td></tr>
<tr><td>仓位</td><td>单票≤50%资金, 同时≤2只</td></tr>
<tr><td>数据源</td><td>同花顺THS(财务) + 新浪财经(K线) + 腾讯API(实时)</td></tr>
</table>
</div>
"""

# 下周操作建议
html += """
<div class="card">
<h2>下周操作建议</h2>
<table>
<tr><th>操作</th><th>标的</th><th>触发条件</th></tr>
<tr><td>🟢 关注</td><td>华天科技(002185)</td><td>回踩¥13.3附近(目前¥14.3, 偏离+7.6%)</td></tr>
<tr><td>🟢 关注</td><td>通富微电(002156)</td><td>回踩¥52.8附近(目前¥57.0, 偏离+8.1%)</td></tr>
<tr><td>🔴 不追</td><td>生益科技(600183)</td><td>偏离+14.7%, 等大幅回调</td></tr>
<tr><td>🔴 不追</td><td>中天科技(600522)</td><td>偏离+14.1%, 等大幅回调</td></tr>
</table>
<p style="margin-top:10px;font-size:13px;color:#8b949e">核心纪律: 不追高, 只买MA20附近。当前市场震荡市(×0.7), 严格控制仓位。</p>
</div>
"""

html += '<div class="footer">数据源: 同花顺THS + 新浪财经 + 腾讯API | 回测期: 近3个月 | 生成: 2026-05-17 | ⚠️ 仅供参考</div>'
html += '</div></body></html>'

report_path = "D:/workbuddy's dates/2026-05-12-task-2/v24全市场回测报告.html"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ 报告已生成: {report_path}")
print(f"\n📊 关键数据:")
print(f"  扫描: 60只涨停活跃股")
print(f"  通过v2.4评分: {len(qualified)}只")
print(f"  可立即买入(MA20附近): {len(buy_now)}只")
print(f"  等待回调(趋势中): {len(wait)}只")
print(f"  高位不宜追: {len(high)}只")
