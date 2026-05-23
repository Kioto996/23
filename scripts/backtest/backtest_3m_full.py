import os, time
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

import requests, json

# 30只股票
stocks = [
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

# 评分（从之前结果录入）
scores = {
    "长电科技":0,"通富微电":3,"晶方科技":0,"士兰微":2,"三安光电":0,
    "华天科技":3,"至纯科技":0,"全志科技":4,"韦尔股份":0,"兆易创新":4,
    "中科曙光":2,"浪潮信息":0,"紫光股份":4,"中兴通讯":0,"烽火通信":0,
    "中际旭创":4,"新易盛":4,"天孚通信":2,"光迅科技":4,"华工科技":3,
    "长江电力":0,"华能国际":0,"国电电力":0,"华电国际":0,"三峡能源":0,
    "京能电力":0,"华光环能":0,"大唐发电":0,"中国核电":0,"华能水电":0
}

# 板块
sectors = {
   "长电科技":"半导体","通富微电":"半导体","晶方科技":"半导体","士兰微":"半导体",
   "三安光电":"半导体","华天科技":"半导体","至纯科技":"半导体","全志科技":"半导体",
   "韦尔股份":"半导体","兆易创新":"半导体",
   "中科曙光":"算力","浪潮信息":"算力","紫光股份":"算力","中兴通讯":"算力",
   "烽火通信":"算力","中际旭创":"算力","新易盛":"算力","天孚通信":"算力",
   "光迅科技":"算力","华工科技":"算力",
   "长江电力":"电力","华能国际":"电力","国电电力":"电力","华电国际":"电力",
   "三峡能源":"电力","京能电力":"电力","华光环能":"电力","大唐发电":"电力",
   "中国核电":"电力","华能水电":"电力"
}

print("=" * 80)
print("v2.4修正版 3个月回测 (2026/02/15 - 2026/05/15)")
print("数据源: 新浪财经K线+同花顺THS")
print("=" * 80)

results = []
for name, code, pre in stocks:
    try:
        url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={pre}{code}&scale=240&ma=no&datalen=65"
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200 or len(r.text) < 50:
            print(f"{name:<8} {code} HTTP{r.status_code}")
            time.sleep(0.2)
            continue
        
        data = json.loads(r.text)
        first_c = float(data[0]["close"])
        last_c = float(data[-1]["close"])
        chg = (last_c - first_c) / first_c * 100
        
        highs = [float(d["high"]) for d in data]
        lows = [float(d["low"]) for d in data]
        max_dd = (min(lows) - first_c) / first_c * 100
        
        sc = scores.get(name, 0)
        sec = sectors.get(name, "")
        results.append((sc, name, code, sec, chg, max_dd, first_c, last_c))
        time.sleep(0.2)
    except Exception as e:
        print(f"{name:<8} {code} ❌ {str(e)[:40]}")
        time.sleep(0.2)

# 输出
print(f"\n✅ 成功获取: {len(results)}只")
print("=" * 80)
print(f"{'评分':>4}{'股票':<8}{'板块':<6}{'3月涨幅':>10}{'最大回撤':>10}{'起始价':>8}{'结束价':>8}")
print("-" * 65)

for r in sorted(results, key=lambda x: x[0], reverse=True):
    print(f"{r[0]:>3}分 {r[1]:<8}{r[3]:<6} {r[4]:>+8.1f}% {r[5]:>+8.1f}% ¥{r[6]:>6.2f} ¥{r[7]:>6.2f}")

# 分组统计
print()
print("评分分组统计")
print("-" * 65)
for sc in [4, 3, 2, 0]:
    grp = [r for r in results if r[0]==sc]
    if grp:
        chgs = [r[4] for r in grp]
        pos = sum(1 for c in chgs if c>0)
        print(f"{sc}分组({len(grp)}只):  平均{sum(chgs)/len(chgs):+.1f}%  "
              f"最高{max(chgs):+.1f}%  最低{min(chgs):+.1f}%  "
              f"正收益{pos}/{len(grp)}")

# 板块统计
print()
print("板块统计")
print("-" * 65)
for sec in ["半导体","算力","电力"]:
    grp = [r for r in results if r[3]==sec]
    if grp:
        chgs = [r[4] for r in grp]
        print(f"{sec:<8}({len(grp)}只): 平均{sum(chgs)/len(chgs):+.1f}%  "
              f"最高{max(chgs):+.1f}%  最低{min(chgs):+.1f}%  "
              f"正收益{sum(1 for c in chgs if c>0)}/{len(grp)}")
