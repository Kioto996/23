import os, time
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import akshare as ak

# 30只股票 代码+市场
stocks_30 = [
    ("长电科技","600584","sh"),("通富微电","002156","sz"),("晶方科技","603005","sh"),
    ("士兰微","600460","sh"),("三安光电","600703","sh"),("华天科技","002185","sz"),
    ("至纯科技","603690","sh"),("全志科技","300458","sz"),("韦尔股份","603501","sh"),
    ("兆易创新","603986","sh"),
    ("中科曙光","603019","sh"),("浪潮信息","000977","sz"),("紫光股份","000938","sz"),
    ("中兴通讯","000063","sz"),("烽火通信","600498","sh"),("中际旭创","300308","sz"),
    ("新易盛","300502","sz"),("天孚通信","300394","sz"),("光迅科技","002281","sz"),
    ("华工科技","000988","sz"),
    ("长江电力","600900","sh"),("华能国际","600011","sh"),("国电电力","600795","sh"),
    ("华电国际","600027","sh"),("三峡能源","600905","sh"),("京能电力","600578","sh"),
    ("华光环能","600475","sh"),("大唐发电","601991","sh"),("中国核电","601985","sh"),
    ("华能水电","600025","sh")
]

# 已有的评分（从之前结果手动录入）
scores = {
    "长电科技":0,"通富微电":3,"晶方科技":0,"士兰微":2,"三安光电":0,
    "华天科技":3,"至纯科技":0,"全志科技":4,"韦尔股份":0,"兆易创新":4,
    "中科曙光":2,"浪潮信息":0,"紫光股份":4,"中兴通讯":0,"烽火通信":0,
    "中际旭创":4,"新易盛":4,"天孚通信":2,"光迅科技":4,"华工科技":3,
    "长江电力":0,"华能国际":0,"国电电力":0,"华电国际":0,"三峡能源":0,
    "京能电力":0,"华光环能":0,"大唐发电":0,"中国核电":0,"华能水电":0
}

print("=" * 80)
print("v2.4修正版 3个月回测 (2026/02/15 - 2026/05/15)")
print("=" * 80)

results = []
for name, code, mkt in stocks_30:
    try:
        hist = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20260215", end_date="20260515", adjust="qfq")
        time.sleep(0.6)
        if len(hist) == 0:
            print(f"{name:<8} 无历史数据")
            continue
        
        p0 = float(hist.iloc[0]["收盘"])
        p1 = float(hist.iloc[-1]["收盘"])
        chg = (p1 - p0) / p0 * 100
        high_3m = float(hist["最高"].max())
        low_3m = float(hist["最低"].min())
        max_drawdown = (hist["最低"].min() - p0) / p0 * 100
        
        sc = scores.get(name, 0)
        results.append((sc, name, code, chg, max_drawdown, p0, p1))
        
    except Exception as e:
        print(f"{name:<8} ❌ {str(e)[:30]}")
        time.sleep(0.6)

print(f"\n成功获取: {len(results)}只")
print("=" * 80)
print(f"{'评分':>4}{'股票':<8}{'3月涨幅':>10}{'最大回撤':>10}{'起始价':>8}{'结束价':>8}")
print("-" * 60)

for r in sorted(results, key=lambda x: x[0], reverse=True):
    print(f"{r[0]:>3}分 {r[1]:<8} {r[3]:>+8.1f}% {r[4]:>+8.1f}% ¥{r[5]:>6.2f} ¥{r[6]:>6.2f}")

print()
print("=" * 80)
print("评分 vs 收益率 统计")
print("-" * 60)

for sc in [4, 3, 2, 0]:
    grp = [r for r in results if r[0] == sc]
    if grp:
        chgs = [r[3] for r in grp]
        print(f"{sc}分组({len(grp)}只): 平均{sum(chgs)/len(chgs):+.1f}%  最高{max(chgs):+.1f}%  最低{min(chgs):+.1f}%  正收益{sum(1 for c in chgs if c>0)}只")
